from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.db import transaction

# Import our custom Application Layer components
from my_garage.models import Vehicle
from .forms import VehicleForm
from .api.selectors import vehicle_get_build_summary, vehicle_list_wishlist_items
from .api.services import service_record_create_from_ocr
from .tasks import task_update_market_valuation, task_enrich_vehicle_data


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

    # We could enhance this with a selector that summarizes the whole garage
    context = {
        "vehicles": vehicles,
        "total_garage_value": sum(v.current_market_value for v in vehicles),
    }
    return render(request, "my_garage/dashboard.html", context)


@login_required
def vehicle_add(request: HttpRequest) -> HttpResponse:
    """
    View to add a new vehicle to the garage.
    """
    if request.method == 'POST':
        form = VehicleForm(request.POST)
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
    Detailed view for a single vehicle using our selector for complex data.
    """
    # Use our selector to get a complete financial/condition summary
    summary = vehicle_get_build_summary(vehicle_id)

    # Check ownership
    if summary['vehicle'].owner != request.user:
        return HttpResponse("Unauthorized", status=401)

    context = {
        **summary,
        "wishlist": vehicle_list_wishlist_items(summary['vehicle']),
    }
    return render(request, "my_garage/vehicle_detail.html", context)


@login_required
def trigger_valuation_refresh(request: HttpRequest, vehicle_id: int) -> HttpResponse:
    """
    Action view to manually trigger the Web MCP valuation task.
    """
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id, owner=request.user)

    # Trigger the background Celery task
    task_update_market_valuation.delay(vehicle.id)

    messages.success(request, f"Valuation update for {vehicle} has been queued.")
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

    return render(request, "my_garage/upload_receipt.html", {"vehicle": vehicle})