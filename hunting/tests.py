import os
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(MAPTILER_API_KEY="test-maptiler-key")
class PlannerViewTests(TestCase):
    """Smoke tests for the hunt planner route."""

    def test_planner_url_resolves_and_renders(self):
        response = self.client.get(reverse("planner"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "hunting/planner.html")

    def test_planner_passes_maptiler_api_key(self):
        response = self.client.get(reverse("planner"))
        self.assertEqual(response.context["MAPTILER_API_KEY"], "test-maptiler-key")

    def test_planner_renders_with_empty_maptiler_key(self):
        # A missing map key must not crash the planner; the page renders
        # with an empty key and the frontend shows a friendly fallback.
        # Patch the environment too: the view falls back to MAPTILER_API_KEY
        # from os.environ, which python-dotenv populates from the local .env.
        with self.settings(MAPTILER_API_KEY=""), patch.dict(os.environ, {"MAPTILER_API_KEY": ""}):
            response = self.client.get(reverse("planner"))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["MAPTILER_API_KEY"], "")
