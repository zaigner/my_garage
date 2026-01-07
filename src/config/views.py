from django.shortcuts import render
from django.http import HttpRequest, HttpResponse

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
        vehicles = request.user.vehicles.all()
        context["vehicles"] = vehicles
        context["total_garage_value"] = sum(v.current_market_value for v in vehicles)

    return render(request, "pages/home.html", context)
