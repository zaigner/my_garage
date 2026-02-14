from django.urls import path
from . import views

app_name = "timepieces"

urlpatterns = [
    # Timepieces
    path("", views.timepiece_list, name="timepiece_list"),
    path("add/", views.timepiece_add, name="timepiece_add"),
    path("<int:timepiece_id>/", views.timepiece_detail, name="timepiece_detail"),
    path("<int:timepiece_id>/add-project/", views.timepiece_add_project, name="timepiece_add_project"),
]