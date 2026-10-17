
import os
from django.shortcuts import render


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
    "MAPTILER_API_KEY": os.environ.get("MAPTILER_API_KEY", ""),
})


def home_view(request):
    return render(request, "pages/home.html", {
        "MAPTILER_API_KEY": os.environ.get("MAPTILER_API_KEY", ""),
    })


def get_started_view(request):
    return render(request, "pages/get_started.html")


def tools_view(request):
    return render(request, "pages/tools.html")


def maps_view(request):
    return render(request, "pages/maps.html")


def your_trip_view(request):
    return render(request, "pages/your_trip.html")


def blog_view(request):
    return render(request, "pages/blog.html")
