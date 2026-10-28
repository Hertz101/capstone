
import logging
import os

from django.conf import settings
from django.contrib.staticfiles import finders
from django.shortcuts import render
from django.urls import reverse

from .content import PRE_HUNT_CHECKLIST, RESOURCE_CARDS

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
    """Interactive pre-hunt checklist, grouped like the classic pre-hunt lists."""
    return render(request, "pages/your_trip.html", {
        "checklist": PRE_HUNT_CHECKLIST,
    })


def blog_view(request):
    return render(request, "pages/blog.html")


def group_chat_view(request):
    return render(request, "pages/group_chat.html")


def _resolve_links(card):
    """Turn "{name}" link targets into real paths via django.urls.reverse."""
    card["links"] = [
        (label, reverse(placeholder[1:-1]) if placeholder.startswith("{") else placeholder)
        for label, placeholder in card.get("links", [])
    ]


def resource_view(request):
    """Resources page. Content lives in pages/content.py — this view only
    wires up internal URLs and verifies PDF paths exist."""
    resources = [dict(card) for card in RESOURCE_CARDS]  # shallow copy per request
    for card in resources:
        _resolve_links(card)
        pdf = card.get("pdf")
        if pdf and not finders.find(pdf):
            logger.warning("resource_view: missing PDF %r for card %r", pdf, card["id"])

    return render(request, "pages/resource.html", {
        "resources": resources,
    })
