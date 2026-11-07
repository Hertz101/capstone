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
    path("group_chat/<int:group_id>/", views.group_chat_view, name="group_chat_group"),
    path("messages/<int:message_id>/like/", views.message_like_view, name="message_like"),
    path("messages/<int:message_id>/delete/", views.message_delete_view, name="message_delete"),
    path("messages/<int:message_id>/edit/", views.message_edit_view, name="message_edit"),
    path("groups/", views.group_list_view, name="group_list"),
    path("groups/new/", views.group_create_view, name="group_create"),
    path("groups/<int:group_id>/", views.group_detail_view, name="group_detail"),
    path("groups/<int:group_id>/join/", views.group_join_view, name="group_join"),
    path("search/", views.search_view, name="search"),
    path("resource/", views.resource_view, name="resource"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/delete/", views.account_delete_view, name="account_delete"),
]
