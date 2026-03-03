import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.db import transaction
from django.template import Template, Context

# Import our custom Application Layer components
from my_garage.models import (
    Vehicle, ServiceRecord, ValuationHistory, Timepiece,
    CollectionType, DynamicCollectionItem, GenericServiceRecord, GenericUpgrade
)
from .forms import (
    VehicleForm, ServiceRecordForm, UpgradeForm, TimepieceForm,
    CollectionTypeForm, DynamicCollectionItemForm,
    GenericServiceRecordForm, GenericUpgradeForm
)
from .api.selectors import (
    vehicle_get_build_summary, 
    vehicle_list_wishlist_items, 
    vehicle_list_service_records, 
    vehicle_list_upgrades,
    global_search
)
from .api.services import service_record_create_from_ocr
from .tasks import task_update_market_valuation, task_enrich_vehicle_data, task_refresh_vehicle_photo
from .skills.theme_generator import CollectionThemeGenerator

logger = logging.getLogger(__name__)


@login_required
def garage_view(request: HttpRequest) -> HttpResponse:
    """
    The 'My Garage' view showing the vehicle carousel (garage.html).
    """
    vehicles = request.user.vehicles.all()
    return render(request, "my_garage/garage.html", {"vehicles": vehicles})


@login_required
def garage_dashboard(request: HttpRequest) -> HttpResponse:
    """
    Primary dashboard showing all vehicles in the user's garage.
    """
    vehicles = request.user.vehicles.all()
    timepieces = request.user.timepieces.all()

    # We could enhance this with a selector that summarizes the whole garage
    context = {
        "vehicles": vehicles,
        "timepieces": timepieces,
        "total_garage_value": sum(v.current_market_value for v in vehicles),
    }
    return render(request, "my_garage/dashboard.html", context)


@login_required
def vehicle_add(request: HttpRequest) -> HttpResponse:
    """
    View to add a new vehicle to the garage.
    """
    if request.method == 'POST':
        form = VehicleForm(request.POST, request.FILES)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.owner = request.user
            vehicle.save()
            
            # Trigger background tasks for enrichment and valuation
            if vehicle.vin:
                transaction.on_commit(lambda: task_enrich_vehicle_data.delay(vehicle.id))
            
            transaction.on_commit(lambda: task_update_market_valuation.delay(vehicle.id))
            
            messages.success(request, f"{vehicle.year} {vehicle.make} {vehicle.model} added to your garage! Data enrichment queued.")
            return redirect('my_garage:garage_view')
    else:
        form = VehicleForm()
    
    return render(request, 'my_garage/vehicle_form.html', {'form': form, 'title': 'Add New Vehicle'})


@login_required
def vehicle_detail(request: HttpRequest, vehicle_id: int) -> HttpResponse:
    """
    Detailed view for a single vehicle, allowing updates.
    """
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id, owner=request.user)

    if request.method == 'POST':
        # Capture old color to check for changes
        old_color = vehicle.exterior_color
        
        form = VehicleForm(request.POST, request.FILES, instance=vehicle)
        if form.is_valid():
            vehicle = form.save()
            
            # Check if color changed and user didn't upload a new photo manually
            new_color = vehicle.exterior_color
            photo_uploaded = 'photo' in request.FILES
            
            if new_color != old_color and new_color and not photo_uploaded:
                logger.info(f"Color changed for {vehicle} from '{old_color}' to '{new_color}'. Triggering photo refresh.")
                transaction.on_commit(lambda: task_refresh_vehicle_photo.delay(vehicle.id))
                messages.info(request, f"Updating photo to match {new_color}...")

            messages.success(request, f"{vehicle} updated successfully.")
            return redirect('my_garage:vehicle_detail', vehicle_id=vehicle.id)
    else:
        form = VehicleForm(instance=vehicle)

    # Use our selector to get a complete financial/condition summary
    summary = vehicle_get_build_summary(vehicle_id)

    financial_summary = {
        'purchase_price': vehicle.purchase_price,
        'total_investment': summary['total_investment'],
        'equity': summary['equity'],
    }

    # Prepare display-friendly dictionaries for the template
    display_specs = {key.replace('_', ' '): value for key, value in vehicle.specs.items()}
    display_features = {key.replace('_', ' '): value for key, value in vehicle.features.items()}
    
    # Get latest valuation history
    latest_valuation = vehicle.valuation_history.first()

    context = {
        'form': form,
        'vehicle': vehicle,
        'financial_summary': financial_summary,
        "wishlist": vehicle_list_wishlist_items(summary['vehicle']),
        "service_records": vehicle_list_service_records(summary['vehicle']),
        "upgrades": vehicle_list_upgrades(summary['vehicle']),
        'display_specs': display_specs,
        'display_features': display_features,
        'latest_valuation': latest_valuation,
    }
    return render(request, "my_garage/vehicle_detail.html", context)


@login_required
def trigger_valuation_refresh(request: HttpRequest, vehicle_id: int) -> HttpResponse:
    """
    Action view to manually trigger the Web MCP valuation task.
    """
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id, owner=request.user)

    # This is a GET request, so we can call the task directly.
    task_update_market_valuation.delay(vehicle.id)

    messages.success(request, f"Valuation update for {vehicle} has been queued.")
    return redirect("my_garage:vehicle_detail", vehicle_id=vehicle.id)


@login_required
def trigger_vin_enrichment(request: HttpRequest, vehicle_id: int) -> HttpResponse:
    """
    Action view to manually trigger the VIN enrichment task.
    """
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id, owner=request.user)
    logger.info(f"Triggering VIN enrichment for vehicle {vehicle.id}")

    if not vehicle.vin:
        messages.error(request, "This vehicle does not have a VIN to look up.")
        return redirect("my_garage:vehicle_detail", vehicle_id=vehicle.id)

    # This is a GET request, so we can call the task directly.
    task_enrich_vehicle_data.delay(vehicle.id)
    logger.info(f"Task for vehicle {vehicle.id} has been dispatched.")

    messages.success(request, f"VIN enrichment for {vehicle} has been queued. The data will be updated shortly.")
    return redirect("my_garage:vehicle_detail", vehicle_id=vehicle.id)


@login_required
def upload_service_receipt(request: HttpRequest, vehicle_id: int) -> HttpResponse:
    """
    Handles receipt upload and initiates AI OCR processing.
    """
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id, owner=request.user)

    if request.method == "POST" and request.FILES.get("receipt"):
        # Use the service layer to create the record and start the pipeline
        record = service_record_create_from_ocr(
            vehicle=vehicle,
            receipt_image=request.FILES["receipt"]
        )

        # The service_record_create_from_ocr would trigger the Celery task internally
        messages.info(request, "Receipt uploaded! AI is now extracting the details.")
        return redirect("my_garage:vehicle_detail", vehicle_id=vehicle.id)

    # If accessed via GET, redirect to the main Add Service page which now includes the upload form
    return redirect("my_garage:add_service_record", vehicle_id=vehicle.id)


@login_required
def add_service_record(request: HttpRequest, vehicle_id: int) -> HttpResponse:
    """
    View to add a new service record manually.
    """
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id, owner=request.user)

    if request.method == 'POST':
        form = ServiceRecordForm(request.POST, request.FILES)
        if form.is_valid():
            record = form.save(commit=False)
            record.vehicle = vehicle
            record.is_verified = True # Manually added records are verified by default
            record.save()
            
            messages.success(request, "Service record added successfully.")
            return redirect('my_garage:vehicle_detail', vehicle_id=vehicle.id)
    else:
        form = ServiceRecordForm()

    return render(request, 'my_garage/service_record_form.html', {'form': form, 'vehicle': vehicle, 'title': 'Add Service Record'})


@login_required
def edit_service_record(request: HttpRequest, record_id: int) -> HttpResponse:
    """
    View to edit an existing service record.
    """
    record = get_object_or_404(ServiceRecord, pk=record_id, vehicle__owner=request.user)
    vehicle = record.vehicle

    if request.method == 'POST':
        form = ServiceRecordForm(request.POST, request.FILES, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, "Service record updated.")
            return redirect('my_garage:vehicle_detail', vehicle_id=vehicle.id)
    else:
        form = ServiceRecordForm(instance=record)

    return render(request, 'my_garage/service_record_form.html', {
        'form': form, 
        'vehicle': vehicle, 
        'title': 'Edit Service Record',
        'is_edit': True,
        'record': record
    })


@login_required
def delete_service_record(request: HttpRequest, record_id: int) -> HttpResponse:
    """
    View to delete a service record.
    """
    record = get_object_or_404(ServiceRecord, pk=record_id, vehicle__owner=request.user)
    vehicle_id = record.vehicle.id
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, "Service record deleted.")
        return redirect('my_garage:vehicle_detail', vehicle_id=vehicle_id)
    
    # If GET, show confirmation page (or just redirect if you prefer no confirmation page)
    return render(request, 'my_garage/confirm_delete.html', {
        'object': record,
        'type': 'Service Record',
        'cancel_url': f"/garage/{vehicle_id}/"
    })


@login_required
def add_upgrade_project(request: HttpRequest, vehicle_id: int) -> HttpResponse:
    """
    View to add a new upgrade project.
    """
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id, owner=request.user)

    if request.method == 'POST':
        form = GenericUpgradeForm(request.POST)
        if form.is_valid():
            upgrade = form.save(commit=False)
            upgrade.content_object = vehicle
            upgrade.save()
            messages.success(request, "Upgrade project started!")
            return redirect('my_garage:vehicle_detail', vehicle_id=vehicle.id)
    else:
        form = GenericUpgradeForm()

    return render(request, 'my_garage/upgrade_form.html', {'form': form, 'vehicle': vehicle, 'title': 'Start New Project'})


@login_required
def vehicle_projects_kanban(request: HttpRequest, vehicle_id: int) -> HttpResponse:
    """
    Kanban board view for all upgrades/projects for a vehicle.
    """
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id, owner=request.user)

    # Get all generic upgrades for this vehicle
    upgrades = vehicle.projects.all().order_by('status', '-ordered_date', '-completion_date')

    # Group upgrades by status
    wishlist = upgrades.filter(status='WISHLIST')
    ordered = upgrades.filter(status='ORDERED')
    in_progress = upgrades.filter(status='IN_PROGRESS')
    completed = upgrades.filter(status='COMPLETED')
    cancelled = upgrades.filter(status='CANCELLED')

    return render(request, 'my_garage/vehicle_projects_kanban.html', {
        'vehicle': vehicle,
        'wishlist': wishlist,
        'ordered': ordered,
        'in_progress': in_progress,
        'completed': completed,
        'cancelled': cancelled,
    })


@login_required
def view_ocr_debug(request: HttpRequest, record_id: int) -> HttpResponse:
    """
    View to inspect the raw OCR data for a service record.
    """
    record = get_object_or_404(ServiceRecord, pk=record_id, vehicle__owner=request.user)
    
    # Extract raw text and other metadata
    raw_data = record.ocr_raw_data or {}
    raw_text = raw_data.get("raw_text", "No raw text available.")
    
    # Try to parse lines for display
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    
    context = {
        "record": record,
        "raw_text": raw_text,
        "lines": lines,
        "raw_data": raw_data,
    }
    return render(request, "my_garage/ocr_debug.html", context)


@login_required
def view_valuation_debug(request: HttpRequest, history_id: int) -> HttpResponse:
    """
    View to inspect the raw API response for a valuation update.
    """
    history = get_object_or_404(ValuationHistory, pk=history_id, vehicle__owner=request.user)
    
    context = {
        "history": history,
        "vehicle": history.vehicle,
        "raw_data": history.raw_data,
    }
    return render(request, "my_garage/valuation_debug.html", context)


@login_required
def timepiece_list(request: HttpRequest) -> HttpResponse:
    """
    The 'Horology Salon' gallery view.
    Renders an 8-slot winder box view.
    """
    timepieces = list(request.user.timepieces.all())
    
    # Create a list of 8 slots
    # Each slot is a dictionary: {'watch': TimepieceObject} or {'watch': None}
    slots = []
    for i in range(8):
        if i < len(timepieces):
            slots.append({'watch': timepieces[i]})
        else:
            slots.append({'watch': None})
            
    return render(request, "my_garage/timepiece_list_winder.html", {
        "timepieces": timepieces,
        "slots": slots
    })


@login_required
def timepiece_add(request: HttpRequest) -> HttpResponse:
    """
    View to add a new timepiece.
    """
    if request.method == 'POST':
        form = TimepieceForm(request.POST, request.FILES)
        if form.is_valid():
            timepiece = form.save(commit=False)
            timepiece.owner = request.user
            timepiece.save()
            messages.success(request, f"{timepiece.brand} {timepiece.model} added to your collection!")
            return redirect('timepieces:timepiece_list')
    else:
        form = TimepieceForm()
    
    return render(request, 'my_garage/timepiece_form.html', {'form': form, 'title': 'Add New Timepiece'})


@login_required
def timepiece_detail(request: HttpRequest, timepiece_id: int) -> HttpResponse:
    """
    Detailed view for a single timepiece.
    """
    timepiece = get_object_or_404(Timepiece, pk=timepiece_id, owner=request.user)

    if request.method == 'POST':
        # Handle photo update
        if 'photo' in request.FILES:
            timepiece.photo = request.FILES['photo']
            timepiece.save()
            messages.success(request, "Photo updated successfully.")
            return redirect('timepieces:timepiece_detail', timepiece_id=timepiece.id)

    return render(request, "my_garage/timepiece_detail.html", {"timepiece": timepiece})


@login_required
def timepiece_add_project(request: HttpRequest, timepiece_id: int) -> HttpResponse:
    """
    View to add a new project/upgrade to a timepiece.
    """
    timepiece = get_object_or_404(Timepiece, pk=timepiece_id, owner=request.user)

    if request.method == 'POST':
        form = GenericUpgradeForm(request.POST)
        if form.is_valid():
            upgrade = form.save(commit=False)
            upgrade.content_object = timepiece
            upgrade.save()
            messages.success(request, "Project started!")
            return redirect('timepieces:timepiece_detail', timepiece_id=timepiece.id)
    else:
        form = GenericUpgradeForm()

    return render(request, 'my_garage/upgrade_form.html', {
        'form': form, 
        'vehicle': timepiece, # Reusing template, might need adjustment
        'title': 'Start New Project',
        'is_timepiece': True # Flag to indicate this is a timepiece
    })


# ============================================================================
# DYNAMIC COLLECTION SYSTEM VIEWS
# ============================================================================

@login_required
def collection_type_list(request: HttpRequest) -> HttpResponse:
    """
    List all collection types for the user with summary stats.
    """
    collection_types = CollectionType.objects.filter(owner=request.user, is_active=True)

    # Get counts and values for each type
    type_data = []
    for ctype in collection_types:
        items = DynamicCollectionItem.objects.filter(
            collection_type=ctype,
            owner=request.user
        )

        count = items.count()
        total_value = sum(
            item.current_market_value or 0
            for item in items
        )

        type_data.append({
            'type': ctype,
            'count': count,
            'total_value': total_value
        })

    return render(request, 'my_garage/collection_types.html', {
        'type_data': type_data
    })


@login_required
def generate_collection_schema(request: HttpRequest) -> JsonResponse:
    """
    AJAX endpoint to generate a collection schema based on a topic string.
    Uses the Gemini-powered CollectionThemeGenerator skill.
    """
    topic = request.GET.get('topic', '').strip()
    description = request.GET.get('description', '').strip()
    
    logger.info(f"Generating schema for topic: '{topic}'")
    
    if not topic:
        logger.warning("No topic provided for schema generation")
        return JsonResponse({'error': 'No topic provided.'}, status=400)
        
    try:
        # Execute the skill
        generator = CollectionThemeGenerator()
        logger.info(f"CollectionThemeGenerator initialized. Enabled: {generator.enabled}")
        
        schema = generator.generate_schema(topic, description)
        logger.info(f"Schema generated successfully: {schema}")
        
        return JsonResponse({
            'success': True,
            'topic': topic,
            'schema': schema
        })
    except Exception as e:
        logger.error(f"Error generating theme for topic '{topic}': {e}", exc_info=True)
        return JsonResponse({'error': f'Failed to generate theme: {str(e)}'}, status=500)

@login_required
def generate_collection_ui(request: HttpRequest) -> JsonResponse:
    """
    AJAX endpoint to generate a UI component based on a topic string.
    Uses the Gemini-powered CollectionThemeGenerator skill.
    """
    topic = request.GET.get('topic', '').strip()
    description = request.GET.get('description', '').strip()
    
    logger.info(f"Generating UI for topic: '{topic}'")
    
    if not topic:
        return JsonResponse({'error': 'No topic provided.'}, status=400)
        
    try:
        generator = CollectionThemeGenerator()
        ui_html = generator.generate_ui_component(topic, description)
        
        return JsonResponse({
            'success': True,
            'topic': topic,
            'ui_html': ui_html
        })
    except Exception as e:
        logger.error(f"Error generating UI for topic '{topic}': {e}", exc_info=True)
        return JsonResponse({'error': f'Failed to generate UI: {str(e)}'}, status=500)


@login_required
def collection_type_create(request: HttpRequest) -> HttpResponse:
    """
    Create a new collection type with schema builder.
    """
    if request.method == 'POST':
        form = CollectionTypeForm(request.POST)

        # Get the schema JSON from the hidden field
        import json
        schema_json = request.POST.get('field_schema_json', '{}')
        list_display_fields = request.POST.get('list_display_fields_json', '[]')
        ui_theme_html = request.POST.get('ui_theme_html', '')

        if form.is_valid():
            collection_type = form.save(commit=False)
            collection_type.owner = request.user
            collection_type.ui_theme_html = ui_theme_html

            # Parse and save the schema
            try:
                collection_type.field_schema = json.loads(schema_json)
                collection_type.list_display_fields = json.loads(list_display_fields)
            except json.JSONDecodeError:
                messages.error(request, "Invalid schema format")
                return render(request, 'my_garage/collection_type_form.html', {'form': form})

            collection_type.save()
            messages.success(request, f"Collection type '{collection_type.name}' created successfully!")
            return redirect('collections:collection_type_list')
    else:
        form = CollectionTypeForm()

    return render(request, 'my_garage/collection_type_form.html', {'form': form})


@login_required
def collection_type_edit(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Edit an existing collection type.
    """
    collection_type = get_object_or_404(CollectionType, slug=slug, owner=request.user)

    if request.method == 'POST':
        form = CollectionTypeForm(request.POST, instance=collection_type)

        import json
        schema_json = request.POST.get('field_schema_json', '{}')
        list_display_fields = request.POST.get('list_display_fields_json', '[]')
        ui_theme_html = request.POST.get('ui_theme_html', '')

        if form.is_valid():
            collection_type = form.save(commit=False)
            collection_type.ui_theme_html = ui_theme_html

            try:
                # Handle potential empty strings or invalid JSON
                if not schema_json or schema_json == '""':
                    schema_json = '{}'
                if not list_display_fields or list_display_fields == '""':
                    list_display_fields = '[]'
                    
                collection_type.field_schema = json.loads(schema_json)
                collection_type.list_display_fields = json.loads(list_display_fields)
            except json.JSONDecodeError as e:
                logger.error(f"JSON Decode Error: {e}")
                messages.error(request, "Invalid schema format")
                return render(request, 'my_garage/collection_type_form.html', {
                    'form': form,
                    'collection_type': collection_type
                })

            collection_type.save()
            messages.success(request, f"Collection type '{collection_type.name}' updated successfully!")
            return redirect('collections:collection_type_list')
    else:
        form = CollectionTypeForm(instance=collection_type)

    return render(request, 'my_garage/collection_type_form.html', {
        'form': form,
        'collection_type': collection_type
    })


@login_required
def collection_list(request: HttpRequest, collection_slug: str) -> HttpResponse:
    """
    List items in a specific collection.
    """
    collection_type = get_object_or_404(
        CollectionType,
        slug=collection_slug,
        owner=request.user
    )

    items = DynamicCollectionItem.objects.filter(
        collection_type=collection_type,
        owner=request.user
    ).order_by('-created_at')

    rendered_ui = None

    # If a custom UI theme is defined, render it as a Django template
    if collection_type.ui_theme_html:
        try:
            # Create a template object from the stored HTML string
            template = Template(collection_type.ui_theme_html)
            
            # Prepare context for the template
            # We need to calculate some stats if the template uses them
            total_value = sum(item.current_market_value or 0 for item in items)
            avg_price = total_value / items.count() if items.count() > 0 else 0
            
            context = Context({
                'collection': {
                    'title': collection_type.name,
                    'description': collection_type.description,
                    'total_items': items.count(),
                    'total_value': total_value,
                    'average_price': avg_price,
                },
                'items': items,
                'recent_items': items[:5], # Just in case template uses 'recent_items'
                'collection_type': collection_type, # Pass the object itself too
                'request': request, # Pass request for URLs etc
                'user': request.user,
            })
            
            rendered_ui = template.render(context)
        except Exception as e:
            logger.error(f"Error rendering custom theme for {collection_type.name}: {e}")
            # Fallback to default view if rendering fails
            messages.error(request, "Error rendering custom theme. Falling back to default view.")

    return render(request, 'my_garage/collection_list.html', {
        'collection_type': collection_type,
        'items': items,
        'rendered_ui': rendered_ui
    })


@login_required
def collection_item_add(request: HttpRequest, collection_slug: str) -> HttpResponse:
    """
    Add a new item to a collection.
    """
    collection_type = get_object_or_404(
        CollectionType,
        slug=collection_slug,
        owner=request.user
    )

    if request.method == 'POST':
        form = DynamicCollectionItemForm(
            request.POST,
            request.FILES,
            collection_type=collection_type
        )
        if form.is_valid():
            item = form.save(commit=False)
            item.collection_type = collection_type
            item.owner = request.user
            item.save()
            messages.success(request, f"'{item.name}' added to {collection_type.name}!")
            return redirect('collections:collection_list', collection_slug=collection_slug)
    else:
        form = DynamicCollectionItemForm(collection_type=collection_type)

    return render(request, 'my_garage/collection_item_form.html', {
        'form': form,
        'collection_type': collection_type
    })


@login_required
def collection_item_detail(request: HttpRequest, collection_slug: str, item_id: int) -> HttpResponse:
    """
    View and edit a collection item.
    """
    collection_type = get_object_or_404(
        CollectionType,
        slug=collection_slug,
        owner=request.user
    )

    item = get_object_or_404(
        DynamicCollectionItem,
        id=item_id,
        collection_type=collection_type,
        owner=request.user
    )

    # Get related records
    service_records = item.service_records.all()
    upgrades = item.upgrades.all()
    attachments = item.attachments.all()

    # Get relationships
    relationships_from = item.relationships_from.all()
    relationships_to = item.relationships_to.all()

    if request.method == 'POST':
        form = DynamicCollectionItemForm(
            request.POST,
            request.FILES,
            instance=item,
            collection_type=collection_type
        )
        if form.is_valid():
            form.save()
            messages.success(request, f"'{item.name}' updated successfully!")
            return redirect('collections:collection_item_detail',
                          collection_slug=collection_slug,
                          item_id=item.id)
    else:
        form = DynamicCollectionItemForm(
            instance=item,
            collection_type=collection_type
        )

    return render(request, 'my_garage/collection_item_detail.html', {
        'collection_type': collection_type,
        'item': item,
        'form': form,
        'service_records': service_records,
        'upgrades': upgrades,
        'attachments': attachments,
        'relationships_from': relationships_from,
        'relationships_to': relationships_to,
    })


@login_required
def collection_item_delete(request: HttpRequest, collection_slug: str, item_id: int) -> HttpResponse:
    """
    Delete a collection item.
    """
    collection_type = get_object_or_404(
        CollectionType,
        slug=collection_slug,
        owner=request.user
    )

    item = get_object_or_404(
        DynamicCollectionItem,
        id=item_id,
        collection_type=collection_type,
        owner=request.user
    )

    if request.method == 'POST':
        item_name = item.name
        item.delete()
        messages.success(request, f"'{item_name}' deleted successfully!")
        return redirect('collections:collection_list', collection_slug=collection_slug)

    return render(request, 'my_garage/collection_item_confirm_delete.html', {
        'collection_type': collection_type,
        'item': item
    })


@login_required
def all_services_view(request: HttpRequest) -> HttpResponse:
    """
    View all service records across ALL collections.
    """
    # Get all service records for user's collection items
    service_records = GenericServiceRecord.objects.filter(
        item__owner=request.user
    ).select_related('item', 'item__collection_type').order_by('-date')

    return render(request, 'my_garage/all_services.html', {
        'service_records': service_records
    })


@login_required
def all_upgrades_view(request: HttpRequest) -> HttpResponse:
    """
    View all upgrades across ALL collections.
    """
    # Get all upgrades for user's collection items
    upgrades = GenericUpgrade.objects.filter(
        item__owner=request.user
    ).select_related('item', 'item__collection_type').order_by('-completion_date', '-ordered_date')

    return render(request, 'my_garage/all_upgrades.html', {
        'upgrades': upgrades
    })


@login_required
def collection_item_add_service(request: HttpRequest, collection_slug: str, item_id: int) -> HttpResponse:
    """
    Add a service record to a collection item.
    """
    collection_type = get_object_or_404(CollectionType, slug=collection_slug, owner=request.user)
    item = get_object_or_404(DynamicCollectionItem, id=item_id, collection_type=collection_type, owner=request.user)

    if request.method == 'POST':
        form = GenericServiceRecordForm(request.POST, request.FILES)
        if form.is_valid():
            record = form.save(commit=False)
            record.item = item
            record.is_verified = True  # Manually added records are verified by default
            record.save()

            messages.success(request, "Service record added successfully.")
            return redirect('collections:collection_item_detail', collection_slug=collection_slug, item_id=item.id)
    else:
        form = GenericServiceRecordForm()

    return render(request, 'my_garage/collection_service_record_form.html', {
        'form': form,
        'item': item,
        'collection_type': collection_type,
        'title': 'Add Service Record'
    })


@login_required
def collection_item_edit_service(request: HttpRequest, collection_slug: str, item_id: int, record_id: int) -> HttpResponse:
    """
    Edit a service record for a collection item.
    """
    collection_type = get_object_or_404(CollectionType, slug=collection_slug, owner=request.user)
    item = get_object_or_404(DynamicCollectionItem, id=item_id, collection_type=collection_type, owner=request.user)
    record = get_object_or_404(GenericServiceRecord, pk=record_id, item=item)

    if request.method == 'POST':
        form = GenericServiceRecordForm(request.POST, request.FILES, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, "Service record updated.")
            return redirect('collections:collection_item_detail', collection_slug=collection_slug, item_id=item.id)
    else:
        form = GenericServiceRecordForm(instance=record)

    return render(request, 'my_garage/collection_service_record_form.html', {
        'form': form,
        'item': item,
        'collection_type': collection_type,
        'title': 'Edit Service Record',
        'is_edit': True,
        'record': record
    })


@login_required
def collection_item_delete_service(request: HttpRequest, collection_slug: str, item_id: int, record_id: int) -> HttpResponse:
    """
    Delete a service record from a collection item.
    """
    collection_type = get_object_or_404(CollectionType, slug=collection_slug, owner=request.user)
    item = get_object_or_404(DynamicCollectionItem, id=item_id, collection_type=collection_type, owner=request.user)
    record = get_object_or_404(GenericServiceRecord, pk=record_id, item=item)

    if request.method == 'POST':
        record.delete()
        messages.success(request, "Service record deleted.")
        return redirect('collections:collection_item_detail', collection_slug=collection_slug, item_id=item.id)

    return render(request, 'my_garage/confirm_delete.html', {
        'object': record,
        'type': 'Service Record',
        'cancel_url': f"/garage/collections/{collection_slug}/items/{item_id}/"
    })


@login_required
def collection_item_add_upgrade(request: HttpRequest, collection_slug: str, item_id: int) -> HttpResponse:
    """
    Add an upgrade/modification project to a collection item.
    """
    collection_type = get_object_or_404(CollectionType, slug=collection_slug, owner=request.user)
    item = get_object_or_404(DynamicCollectionItem, id=item_id, collection_type=collection_type, owner=request.user)

    if request.method == 'POST':
        form = GenericUpgradeForm(request.POST)
        if form.is_valid():
            upgrade = form.save(commit=False)
            upgrade.item = item
            upgrade.save()

            messages.success(request, f"Project '{upgrade.name}' started!")
            return redirect('collections:collection_item_detail', collection_slug=collection_slug, item_id=item.id)
    else:
        form = GenericUpgradeForm()

    return render(request, 'my_garage/upgrade_form.html', {
        'form': form,
        'vehicle': item,
        'title': 'Start New Project',
        'is_collection': True,
        'collection_slug': collection_slug
    })


@login_required
def collection_item_edit_upgrade(request: HttpRequest, collection_slug: str, item_id: int, upgrade_id: int) -> HttpResponse:
    """
    Edit an upgrade/modification project.
    """
    collection_type = get_object_or_404(CollectionType, slug=collection_slug, owner=request.user)
    item = get_object_or_404(DynamicCollectionItem, id=item_id, collection_type=collection_type, owner=request.user)
    upgrade = get_object_or_404(GenericUpgrade, pk=upgrade_id, item=item)

    if request.method == 'POST':
        form = GenericUpgradeForm(request.POST, instance=upgrade)
        if form.is_valid():
            form.save()
            messages.success(request, f"Project '{upgrade.name}' updated.")
            return redirect('collections:collection_item_detail', collection_slug=collection_slug, item_id=item.id)
    else:
        form = GenericUpgradeForm(instance=upgrade)

    return render(request, 'my_garage/upgrade_form.html', {
        'form': form,
        'vehicle': item,
        'title': 'Edit Project',
        'is_edit': True,
        'upgrade': upgrade,
        'is_collection': True,
        'collection_slug': collection_slug
    })


@login_required
def collection_item_delete_upgrade(request: HttpRequest, collection_slug: str, item_id: int, upgrade_id: int) -> HttpResponse:
    """
    Delete an upgrade/modification project.
    """
    collection_type = get_object_or_404(CollectionType, slug=collection_slug, owner=request.user)
    item = get_object_or_404(DynamicCollectionItem, id=item_id, collection_type=collection_type, owner=request.user)
    upgrade = get_object_or_404(GenericUpgrade, pk=upgrade_id, item=item)

    if request.method == 'POST':
        upgrade.delete()
        messages.success(request, f"Project '{upgrade.name}' deleted.")
        return redirect('collections:collection_item_detail', collection_slug=collection_slug, item_id=item.id)

    return render(request, 'my_garage/confirm_delete.html', {
        'object': upgrade,
        'type': 'Upgrade Project',
        'cancel_url': f"/garage/collections/{collection_slug}/items/{item_id}/"
    })


@login_required
def collection_upgrades_kanban(request: HttpRequest, collection_slug: str) -> HttpResponse:
    """
    Kanban board view for all upgrades in a collection.
    """
    collection_type = get_object_or_404(CollectionType, slug=collection_slug, owner=request.user)

    # Get all upgrades for this collection, grouped by status
    items = DynamicCollectionItem.objects.filter(
        collection_type=collection_type,
        owner=request.user
    )

    upgrades = GenericUpgrade.objects.filter(
        item__in=items
    ).select_related('item').order_by('status', '-ordered_date', '-completion_date')

    # Group upgrades by status
    wishlist = upgrades.filter(status='WISHLIST')
    ordered = upgrades.filter(status='ORDERED')
    in_progress = upgrades.filter(status='IN_PROGRESS')
    completed = upgrades.filter(status='COMPLETED')
    cancelled = upgrades.filter(status='CANCELLED')

    return render(request, 'my_garage/collection_upgrades_kanban.html', {
        'collection_type': collection_type,
        'wishlist': wishlist,
        'ordered': ordered,
        'in_progress': in_progress,
        'completed': completed,
        'cancelled': cancelled,
    })


@login_required
def collection_upgrade_update_status(request: HttpRequest, upgrade_id: int) -> HttpResponse:
    """
    AJAX endpoint to update upgrade status (for kanban drag-and-drop).
    """
    import json
    from django.http import JsonResponse

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    upgrade = get_object_or_404(
        GenericUpgrade,
        pk=upgrade_id,
        item__owner=request.user
    )

    try:
        data = json.loads(request.body)
        new_status = data.get('status')

        if new_status not in dict(GenericUpgrade.STATUS_CHOICES):
            return JsonResponse({'error': 'Invalid status'}, status=400)

        upgrade.status = new_status

        # Update dates based on status
        if new_status == 'COMPLETED' and not upgrade.completion_date:
            from django.utils import timezone
            upgrade.completion_date = timezone.now().date()
        elif new_status == 'ORDERED' and not upgrade.ordered_date:
            from django.utils import timezone
            upgrade.ordered_date = timezone.now().date()

        upgrade.save()

        return JsonResponse({
            'success': True,
            'status': new_status,
            'status_display': upgrade.get_status_display()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def global_search_view(request: HttpRequest) -> JsonResponse:
    """
    AJAX endpoint for global search.
    """
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})
        
    results = global_search(request.user, query)
    return JsonResponse({'results': results})

def button_test_view(request: HttpRequest) -> HttpResponse:
    """
    Debug view to test button functionality (no login required for testing).
    """
    return render(request, 'my_garage/button_test.html', {})

# Force reload
