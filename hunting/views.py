from django.shortcuts import render

import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)


def get_maptiler_key():
    """Return the MapTiler key from Django settings, falling back to the environment.

    A missing key is logged loudly but does not crash the page — the
    frontend shows a friendly message instead of a broken map.
    """
    api_key = getattr(settings, "MAPTILER_API_KEY", "") or os.environ.get("MAPTILER_API_KEY", "")

    if not api_key:
        logger.warning(
            "MAPTILER_API_KEY is not set or is empty; the GMU map will not load. "
            "Add it to your environment or .env file."
        )

    return api_key


def planner_view(request):
    """Serve the interactive hunt planner page."""
    return render(request, "hunting/planner.html", {
        "MAPTILER_API_KEY": get_maptiler_key(),
    })
