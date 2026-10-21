from django.urls import path

from . import views

urlpatterns = [
    path("plan/", views.planner_view, name="planner"),
]
