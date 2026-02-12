from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from my_garage.models import DynamicCollectionItem

def home(request: HttpRequest) -> HttpResponse:
    """
    Home page view that mimics the dashboard structure but handles unauthenticated users.
    """
    context = {}
    if request.user.is_authenticated:
        # If user is logged in, we can try to get their garage stats
        # Note: Ideally we'd reuse the logic from my_garage.views.garage_dashboard
        # but we need to be careful about circular imports if we import views directly.
        # Instead, we can just query the models directly here or keep it simple.

        # For now, let's just pass the user object which is already in request.
        # The template handles the logic of showing data vs placeholders.

        # If we want to show actual data on the home page for logged in users:
        # We need to access the related managers on the user object.
        # Assuming the user model has related names 'vehicles' and 'timepieces'
        
        # Check if the user has the attributes before accessing them to avoid errors
        # if the custom user model or related names are different.
        vehicles = getattr(request.user, 'vehicles', None)
        timepieces = getattr(request.user, 'timepieces', None)
        
        if vehicles:
            vehicles = vehicles.all()
            context["vehicles"] = vehicles
            context["total_automobiles_value"] = sum(v.current_market_value for v in vehicles)
        else:
            context["vehicles"] = []
            context["total_automobiles_value"] = 0

        if timepieces:
            timepieces = timepieces.all()
            context["timepieces"] = timepieces
            context["total_timepieces_value"] = sum(t.current_market_value for t in timepieces)
        else:
            context["timepieces"] = []
            context["total_timepieces_value"] = 0
        
        # Calculate total value for dynamic collections
        collections = DynamicCollectionItem.objects.filter(owner=request.user)
        context["total_collections_value"] = sum(c.current_market_value for c in collections if c.current_market_value is not None)


    return render(request, "pages/home.html", context)
