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
    path("activate/", estate_views.estate_activate, name="activate"),
    path(
        "activate/success/",
        estate_views.estate_activate_success,
        name="activate_success",
    ),
    path("activate/revoke/", estate_views.estate_revoke_access, name="revoke_access"),
    path("portal/", estate_views.portal_code_entry, name="portal_code_entry"),
    path("portal/dashboard/", estate_views.portal_dashboard, name="portal_dashboard"),
    path(
        "portal/items/<int:item_id>/",
        estate_views.portal_item_detail,
        name="executor_item_detail",
    ),
    path(
        "portal/items/<int:item_id>/photo/",
        estate_views.portal_item_photo,
        name="executor_item_photo",
    ),
    path(
        "portal/beneficiaries/<int:pk>/link/",
        estate_views.portal_link_issue,
        name="portal_link_issue",
    ),
    path(
        "portal/beneficiaries/<int:pk>/link/revoke/",
        estate_views.portal_link_revoke,
        name="portal_link_revoke",
    ),
    path(
        "portal/beneficiaries/<int:pk>/link/issued/",
        estate_views.portal_link_issued,
        name="portal_link_issued",
    ),
    path("beneficiary/", estate_views.beneficiary_portal, name="beneficiary_portal"),
    path(
        "beneficiary/items/<int:item_id>/",
        estate_views.beneficiary_item_detail,
        name="beneficiary_item_detail",
    ),
    path(
        "beneficiary/items/<int:item_id>/photo/",
        estate_views.beneficiary_item_photo,
        name="beneficiary_item_photo",
    ),
    path(
        "beneficiary/claim/<str:token>/",
        estate_views.beneficiary_claim,
        name="beneficiary_claim",
    ),
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
