from django.db.models import Q
from typing import Dict, Any, List

from my_garage.models import DynamicCollectionItem


def global_search(user, query: str) -> List[Dict[str, Any]]:
    """
    Performs a global search across DynamicCollectionItems.
    Returns a list of results with type, name, url, and icon.
    """
    if not query:
        return []

    items = DynamicCollectionItem.objects.filter(
        Q(owner=user) & (
            Q(name__icontains=query) |
            Q(collection_type__name__icontains=query) |
            Q(notes__icontains=query)
        )
    ).select_related("collection_type")[:10]

    results = []
    for item in items:
        results.append({
            "type": item.collection_type.name,
            "name": item.name,
            "subtext": item.collection_type.name,
            "url": f"/collections/{item.collection_type.slug}/items/{item.id}/",
            "icon": item.collection_type.icon or "fa-box",
            "category": item.collection_type.name,
        })
    return results
