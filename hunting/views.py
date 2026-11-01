from django.shortcuts import render

import logging

from config.maptiler import get_maptiler_key

logger = logging.getLogger(__name__)


def planner_view(request):
    """Serve the interactive hunt planner page."""
    return render(request, "hunting/planner.html", {
        "MAPTILER_API_KEY": get_maptiler_key(),
    })
