import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.db import transaction

# Import our custom Application Layer components
from my_garage.models import Vehicle, ServiceRecord, ValuationHistory, Timepiece
from .forms import VehicleForm, ServiceRecordForm, UpgradeForm
from .api.selectors import (
    vehicle_get_build_summary, 
    vehicle_list_wishlist_items, 
    vehicle_list_service_records, 
    vehicle_list_upgrades
)
from .api.services import service_record_create_from_ocr
from .tasks import task_update_market_valuation, task_enrich_vehicle_data, task_refresh_vehicle_photo

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
        form = UpgradeForm(request.POST)
        if form.is_valid():
            upgrade = form.save(commit=False)
            upgrade.vehicle = vehicle
            upgrade.save()
            messages.success(request, "Upgrade project started!")
            return redirect('my_garage:vehicle_detail', vehicle_id=vehicle.id)
    else:
        form = UpgradeForm()

    return render(request, 'my_garage/upgrade_form.html', {'form': form, 'vehicle': vehicle, 'title': 'Start New Project'})


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
    """
    timepieces = request.user.timepieces.all()
    return render(request, "my_garage/timepiece_list.html", {"timepieces": timepieces})


@login_required
def timepiece_detail(request: HttpRequest, timepiece_id: int) -> HttpResponse:
    """
    Detailed view for a single timepiece.
    """
    timepiece = get_object_or_404(Timepiece, pk=timepiece_id, owner=request.user)
    return render(request, "my_garage/timepiece_detail.html", {"timepiece": timepiece})
