from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from my_garage.models import DynamicCollectionItem, Vehicle, Timepiece, CollectionType
from itertools import chain
from operator import attrgetter
from datetime import datetime

def get_sort_date(item):
    """
    Helper function to get the appropriate date for sorting.
    Uses 'created_at' if available, otherwise falls back to 'purchase_date'.
    """
    if hasattr(item, 'created_at') and item.created_at:
        # Ensure created_at is a date object if it's a datetime
        if isinstance(item.created_at, datetime):
            return item.created_at.date()
        return item.created_at
    if hasattr(item, 'purchase_date') and item.purchase_date:
        return item.purchase_date
    # Fallback to a very old date if no date is available
    return datetime(1900, 1, 1).date()

def home(request: HttpRequest) -> HttpResponse:
    """
    Home page view that mimics the dashboard structure but handles unauthenticated users.
    """
    context = {}
    if request.user.is_authenticated:
        # If user is logged in, we can try to get their garage stats
        
        # Get querysets
        vehicles_manager = getattr(request.user, 'vehicles', None)
        timepieces_manager = getattr(request.user, 'timepieces', None)
        
        vehicles = vehicles_manager.all() if vehicles_manager else []
        timepieces = timepieces_manager.all() if timepieces_manager else []
        
        # Get all collection items for total valuation
        all_collection_items = DynamicCollectionItem.objects.filter(owner=request.user)

        # Get individual collection types with their items for the cards
        collection_types = CollectionType.objects.filter(owner=request.user, is_active=True)
        custom_collections = []
        
        for c_type in collection_types:
            items = all_collection_items.filter(collection_type=c_type)
            c_type.item_count = items.count()
            c_type.total_value = sum(item.current_market_value or 0 for item in items)
            custom_collections.append(c_type)

        # Calculate valuations
        context["total_automobiles_value"] = sum(v.current_market_value for v in vehicles if v.current_market_value)
        context["total_timepieces_value"] = sum(t.current_market_value for t in timepieces if t.current_market_value)
        context["total_collections_value"] = sum(c.current_market_value for c in all_collection_items if c.current_market_value)

        # Pass querysets for counts in template
        context["vehicles"] = vehicles
        context["timepieces"] = timepieces
        context["custom_collections"] = custom_collections
        
        # Combine all items for recent acquisitions feed
        all_items = sorted(
            chain(list(vehicles), list(timepieces), list(all_collection_items)),
            key=get_sort_date,
            reverse=True
        )
        context['recent_acquisitions'] = all_items[:3]

    return render(request, "pages/home.html", context)

def register(request: HttpRequest) -> HttpResponse:
    """
    Register a new user.
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful. Welcome to The Salon.")
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})
