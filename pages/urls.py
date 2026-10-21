from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    # The planner moved to the hunting app; keep the old URL working.
    path(
        "get_started/",
        RedirectView.as_view(pattern_name="planner", permanent=False),
        name="get_started",
    ),
    path("maps/", views.maps_view, name="maps"),
    path("tools/", views.tools_view, name="tools"),
    path("your_trip/", views.your_trip_view, name="your_trip"),
    path("blog/", views.blog_view, name="blog"),
    path("group_chat/", views.group_chat_view, name="group_chat"),
    path("resource/", views.resource_view, name="resource"),
]
