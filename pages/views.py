
import logging
import os

from django.conf import settings
from django.shortcuts import render

logger = logging.getLogger(__name__)


def get_maptiler_key():
    """Return the MapTiler key from Django settings, falling back to the environment."""
    return getattr(settings, "MAPTILER_API_KEY", "") or os.environ.get("MAPTILER_API_KEY", "")


def home_view(request):
    animal_cards = [
        ("Elk", "img/elk.jpeg", "Elk"),
        ("Deer", "img/mule.jpeg", "Mule Deer"),
        ("Deer", "img/whitetail.jpeg", "Whitetail Deer"),
        ("Bear", "img/bear.jpeg", "Bear"),
        ("Pronghorn", "img/pronghorn.jpeg", "Pronghorn"),
    ]

    return render(request, "pages/home.html", {
        "animal_cards": animal_cards,
    })


def tools_view(request):
    return render(request, "pages/tools.html")


def maps_view(request):
    return render(request, "pages/maps.html", {
        "maptiler_key": get_maptiler_key(),
    })


def your_trip_view(request):
    return render(request, "pages/your_trip.html")


def blog_view(request):
    return render(request, "pages/blog.html")


def group_chat_view(request):
    return render(request, "pages/group_chat.html")


def resource_view(request):
    return render(request, "pages/resource.html")
