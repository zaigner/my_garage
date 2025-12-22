urlpatterns = [
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    # ... other paths ...
    path("garage/", include("my_garage.urls", namespace="my_garage")),
    # FastAPI is served separately via Uvicorn, but we can mount the router here
    # if using a unified gateway or handle it via the api_router.
]