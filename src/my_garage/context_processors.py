from my_garage.models import CollectionType


def user_collections(request):
    """
    Injects quick_add_collections into every template context.
    Used by the global Quick Add nav dropdown.
    """
    if not request.user.is_authenticated:
        return {"quick_add_collections": []}

    collections = (
        CollectionType.objects.filter(owner=request.user, is_active=True)
        .only("name", "slug", "icon")
        .order_by("name")
    )
    return {"quick_add_collections": list(collections)}
