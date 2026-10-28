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
from django.contrib.staticfiles import finders

from .content import PRE_HUNT_CHECKLIST, RESOURCE_CARDS


class ChecklistDataTests(TestCase):
    """Structural guarantees the Your Trip page and its JS rely on."""

    def test_every_group_has_id_icon_title_and_items(self):
        for group in PRE_HUNT_CHECKLIST:
            self.assertTrue(group["id"], f"group missing id: {group}")
            self.assertTrue(group["title"], f"group {group['id']} missing title")
            self.assertTrue(group["icon"], f"group {group['id']} missing icon")
            self.assertGreater(
                len(group["items"]), 0, f"group {group['id']} has no items"
            )

    def test_group_ids_are_unique(self):
        ids = [g["id"] for g in PRE_HUNT_CHECKLIST]
        self.assertEqual(len(ids), len(set(ids)), f"duplicate group ids: {ids}")

    def test_all_items_are_nonempty_strings(self):
        for group in PRE_HUNT_CHECKLIST:
            for item in group["items"]:
                self.assertIsInstance(item, str)
                self.assertTrue(item.strip(), f"blank item in {group['id']}")

    def test_checklist_renders_every_group(self):
        response = self.client.get(reverse("your_trip"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["checklist"]), PRE_HUNT_CHECKLIST
        )


class ResourceCardDataTests(TestCase):
    """Structural guarantees the Resources page template relies on."""

    def test_every_card_has_required_fields(self):
        for card in RESOURCE_CARDS:
            for field in ("id", "img", "kicker", "title"):
                self.assertTrue(
                    card.get(field), f"card {card.get('id')} missing {field}"
                )
            # A card is either expandable (sections) or a PDF link — not both, not neither.
            if "pdf" in card:
                self.assertNotIn("sections", card, f"card {card['id']} has both pdf and sections")
            else:
                self.assertIn("sections", card, f"card {card['id']} has neither pdf nor sections")

    def test_card_ids_are_unique(self):
        ids = [c["id"] for c in RESOURCE_CARDS]
        self.assertEqual(len(ids), len(set(ids)), f"duplicate card ids: {ids}")

    def test_sections_have_heading_and_bullets(self):
        for card in RESOURCE_CARDS:
            for section in card.get("sections", []):
                self.assertIn("heading", section, f"card {card['id']} section missing heading")
                self.assertTrue(
                    section.get("bullets"), f"card {card['id']} section '{section['heading']}' has no bullets"
                )

    def test_internal_link_placeholders_are_valid_url_names(self):
        from django.urls import NoReverseMatch, reverse

        for card in RESOURCE_CARDS:
            for _, target in card.get("links", []):
                if target.startswith("{"):
                    name = target[1:-1]
                    try:
                        reverse(name)
                    except NoReverseMatch:
                        self.fail(f"card {card['id']} links to unknown url name '{name}'")

    def test_pdf_paths_exist_in_static(self):
        for card in RESOURCE_CARDS:
            pdf = card.get("pdf")
            if pdf:
                self.assertIsNotNone(
                    finders.find(pdf), f"card {card['id']} references missing static PDF {pdf}"
                )

    def test_resource_view_resolves_placeholders(self):
        response = self.client.get(reverse("resource"))
        self.assertEqual(response.status_code, 200)
        cards = response.context["resources"]
        by_id = {c["id"]: c for c in cards}
        planner_card = by_id["planning"]
        href = dict(planner_card["links"])["Open the Hunt Planner →"]
        self.assertTrue(href.startswith("/"), "internal placeholder was not resolved to a path")
        self.assertFalse(href.startswith("{"))

    def test_resource_view_does_not_mutate_shared_content(self):
        # Views get shallow copies; the module-level dicts must keep raw placeholders.
        self.client.get(reverse("resource"))
        planning = next(c for c in RESOURCE_CARDS if c["id"] == "planning")
        self.assertEqual(planning["links"][0][1], "{planner}")
