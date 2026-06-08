"""URL patterns for Estate & Legacy."""

from django.urls import path

from . import estate_views

app_name = "estate"

urlpatterns = [
    path("", estate_views.estate_dashboard, name="estate_dashboard"),
    path("beneficiaries/", estate_views.beneficiary_list, name="beneficiary_list"),
    path(
        "beneficiaries/add/",
        estate_views.beneficiary_create,
        name="beneficiary_create",
    ),
    path(
        "beneficiaries/<int:pk>/delete/",
        estate_views.beneficiary_delete,
        name="beneficiary_delete",
    ),
    path("executor/", estate_views.executor_view, name="executor"),
    path("executor/remove/", estate_views.executor_remove, name="executor_remove"),
    path("assign/", estate_views.assign_overview, name="assign_overview"),
    path(
        "assign/<slug:collection_slug>/items/<int:item_id>/",
        estate_views.item_assign,
        name="item_assign",
    ),
    path(
        "assign/<slug:collection_slug>/items/<int:item_id>/remove/",
        estate_views.item_assign_remove,
        name="item_assign_remove",
    ),
]
