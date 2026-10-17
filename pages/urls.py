from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("get_started/", views.get_started_view, name="get_started"),
    path("maps/", views.maps_view, name="maps"),
    path("tools/", views.tools_view, name="tools"),
    path("your_trip/", views.your_trip_view, name="your_trip"),
    path("blog/", views.blog_view, name="blog"),
]
