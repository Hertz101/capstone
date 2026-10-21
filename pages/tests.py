from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(MAPTILER_API_KEY="test-maptiler-key")
class PageViewTests(TestCase):
    """Tests for every page route in pages/urls.py."""

    def test_home_url_resolves_and_renders(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/home.html")

    def test_get_started_url_redirects_to_planner(self):
        # The old /get_started/ path now redirects to the hunting planner.
        response = self.client.get(reverse("get_started"), follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("planner"))

    def test_maps_url(self):
        response = self.client.get(reverse("maps"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/maps.html")

    def test_resource_url(self):
        response = self.client.get(reverse("resource"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/resource.html")

    def test_group_chat_url(self):
        response = self.client.get(reverse("group_chat"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/group_chat.html")

    def test_blog_url(self):
        response = self.client.get(reverse("blog"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/blog.html")

    def test_home_passes_animal_cards_to_template(self):
        response = self.client.get(reverse("home"))
        animal_cards = response.context["animal_cards"]

        self.assertIsInstance(animal_cards, list)
        self.assertTrue(len(animal_cards) > 0)

        for card in animal_cards:
            self.assertEqual(len(card), 3)
            self.assertTrue(all(card))

        # Each unique species key should be present exactly once.
        species = [card[0] for card in animal_cards]
        self.assertIn("Elk", species)
        self.assertIn("Bear", species)
        self.assertIn("Pronghorn", species)
        self.assertEqual(species.count("Deer"), 2)

    def test_home_passes_no_maptiler_key(self):
        # The home page no longer renders the map, so it does not need the key.
        response = self.client.get(reverse("home"))
        self.assertNotIn("MAPTILER_API_KEY", response.context)
