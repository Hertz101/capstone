from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(MAPTILER_API_KEY="test-maptiler-key")
class PageViewTests(TestCase):
    """Tests for every page route in pages/urls.py."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth.models import User

        cls.user = User.objects.create_user("chatuser", password="pw12345!")

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

    def test_signup_with_profile_fields_creates_profile(self):
        from .models import Profile

        response = self.client.post(
            reverse("signup"),
            {
                "username": "hunter1",
                "password1": "s3cure-pass!",
                "password2": "s3cure-pass!",
                "email": "hunter1@example.com",
                "first_name": "Adam",
                "last_name": "H",
                "city": "Denver",
                "state": "co",
                "method": "archery",
            },
        )
        self.assertRedirects(response, reverse("group_chat"))
        profile = Profile.objects.get(user__username="hunter1")
        self.assertEqual(profile.first_name, "Adam")
        self.assertEqual(profile.city, "Denver")
        self.assertEqual(profile.state, "CO")  # normalized to upper case
        self.assertEqual(profile.method, "archery")
        self.assertEqual(profile.display_name, "Adam H")

    def test_group_chat_requires_login(self):
        # Anonymous users are redirected to the login page.
        response = self.client.get(reverse("group_chat"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_group_chat_url(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("group_chat"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/group_chat.html")

    def test_group_chat_post_creates_message(self):
        from .models import Message

        self.client.force_login(self.user)
        response = self.client.post(reverse("group_chat"), {"text": "Anyone hunting unit 201?"})
        self.assertRedirects(response, reverse("group_chat"))
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Message.objects.first().user, self.user)
        self.assertEqual(Message.objects.first().text, "Anyone hunting unit 201?")

    def test_group_chat_blank_post_is_ignored(self):
        from .models import Message

        self.client.force_login(self.user)
        self.client.post(reverse("group_chat"), {"text": "   "})
        self.assertEqual(Message.objects.count(), 0)

    def test_group_chat_shows_messages(self):
        from .models import Message

        Message.objects.create(user=self.user, text="Season opens Saturday!")
        self.client.force_login(self.user)
        response = self.client.get(reverse("group_chat"))
        self.assertContains(response, "chatuser")
        self.assertContains(response, "Season opens Saturday!")


class GroupTests(TestCase):
    """Create groups, add/remove members, and chat inside a group."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth.models import User

        cls.creator = User.objects.create_user("creator", password="pw12345!")
        cls.friend = User.objects.create_user("friend", password="pw12345!")
        cls.outsider = User.objects.create_user("outsider", password="pw12345!")

    def test_create_group_adds_creator_and_selected_members(self):
        from .models import ChatGroup

        self.client.force_login(self.creator)
        response = self.client.post(
            reverse("group_create"),
            {"name": "Camp Crew", "members": [self.friend.pk]},
        )
        group = ChatGroup.objects.get(name="Camp Crew")
        self.assertRedirects(response, reverse("group_chat_group", args=[group.pk]))
        self.assertEqual(set(group.members.all()), {self.creator, self.friend})
        self.assertEqual(group.created_by, self.creator)

    def test_create_group_form_lists_other_users(self):
        self.client.force_login(self.creator)
        response = self.client.get(reverse("group_create"))
        member_options = response.context["form"].fields["members"].queryset
        self.assertIn(self.friend, member_options)
        self.assertNotIn(self.creator, member_options)

    def test_non_member_cannot_read_group_chat(self):
        from .models import ChatGroup

        group = ChatGroup.objects.create(name="Secret Spot", created_by=self.creator)
        group.members.add(self.creator, self.friend)
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("group_chat_group", args=[group.pk]))
        self.assertRedirects(response, reverse("group_chat"))

    def test_member_can_post_to_group_chat(self):
        from .models import ChatGroup, Message

        group = ChatGroup.objects.create(name="Camp Crew", created_by=self.creator)
        group.members.add(self.creator, self.friend)
        self.client.force_login(self.friend)
        self.client.post(reverse("group_chat_group", args=[group.pk]), {"text": "Who's bringing the elk tag?"})
        msg = Message.objects.get(group=group)
        self.assertEqual(msg.user, self.friend)
        self.assertEqual(msg.text, "Who's bringing the elk tag?")

    def test_creator_can_add_and_remove_members(self):
        from .models import ChatGroup

        group = ChatGroup.objects.create(name="Camp Crew", created_by=self.creator)
        group.members.add(self.creator)
        self.client.force_login(self.creator)

        self.client.post(reverse("group_detail", args=[group.pk]), {"action": "add", "user_id": self.outsider.pk})
        self.assertIn(self.outsider, group.members.all())

        self.client.post(reverse("group_detail", args=[group.pk]), {"action": "remove", "user_id": self.outsider.pk})
        self.assertNotIn(self.outsider, group.members.all())

    def test_non_creator_cannot_add_members(self):
        from .models import ChatGroup

        group = ChatGroup.objects.create(name="Camp Crew", created_by=self.creator)
        group.members.add(self.creator, self.friend)
        self.client.force_login(self.friend)
        self.client.post(reverse("group_detail", args=[group.pk]), {"action": "add", "user_id": self.outsider.pk})
        self.assertNotIn(self.outsider, group.members.all())

    def test_group_join_view_adds_user(self):
        from .models import ChatGroup

        group = ChatGroup.objects.create(name="Open Crew", created_by=self.creator)
        self.client.force_login(self.outsider)
        response = self.client.post(reverse("group_join", args=[group.pk]))
        self.assertRedirects(response, reverse("group_chat_group", args=[group.pk]))
        self.assertIn(self.outsider, group.members.all())


class ProfileViewTests(TestCase):
    """The profile page: access control, auto-create, and editing."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth.models import User

        cls.user = User.objects.create_user("chatuser", password="pw12345!")

    def test_profile_requires_login(self):
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_profile_view_creates_missing_profile(self):
        # A user who somehow signed up before the Profile model existed
        # still gets a profile page without a 500.
        self.client.force_login(self.user)
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(hasattr(self.user, "profile"))

    def test_profile_edit_saves_changes(self):
        from .models import Profile

        Profile.objects.create(user=self.user, first_name="Old")
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("profile"),
            {
                "email": self.user.email or "edited@example.com",
                "first_name": "Adam",
                "last_name": "Hunter",
                "city": "Denver",
                "state": "co",
                "method": "rifle",
            },
        )
        self.assertRedirects(response, reverse("profile"))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.first_name, "Adam")
        self.assertEqual(self.user.profile.state, "CO")

    def test_account_delete_requires_correct_password(self):
        from django.contrib.auth.models import User

        self.client.force_login(self.user)
        response = self.client.post(reverse("account_delete"), {"password": "wrong-pw"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Incorrect password")
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_account_delete_removes_user_and_cascades(self):
        from django.contrib.auth.models import User

        from .models import ChatGroup, Message, Profile

        Profile.objects.create(user=self.user, first_name="Bye")
        Message.objects.create(user=self.user, text="farewell")
        group = ChatGroup.objects.create(name="Lonely Crew", created_by=self.user)
        group.members.add(self.user)

        self.client.force_login(self.user)
        response = self.client.post(reverse("account_delete"), {"password": "pw12345!"})

        self.assertRedirects(response, reverse("logged_out"))
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertEqual(Message.objects.count(), 0)          # messages cascade
        self.assertEqual(Profile.objects.count(), 0)          # profile cascades
        self.assertEqual(group.members.count(), 0)            # membership gone
        self.assertEqual(ChatGroup.objects.filter(name="Lonely Crew").count(), 1)  # group survives, creator nulled

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
class ResourceViewTests(TestCase):
    """Behavior of the resources page view itself."""

    def test_resource_view_resolves_and_renders(self):
        response = self.client.get(reverse("resource"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/resource.html")

    def test_resource_view_passes_all_cards(self):
        response = self.client.get(reverse("resource"))
        self.assertEqual(
            len(response.context["resources"]), len(RESOURCE_CARDS)
        )

    def test_resource_view_links_resolve_to_real_paths(self):
        response = self.client.get(reverse("resource"))
        for card in response.context["resources"]:
            for _, href in card.get("links", []):
                # Internal placeholders must be resolved to paths; external
                # URLs (http/https) pass through untouched.
                self.assertTrue(
                    href.startswith("/") or href.startswith("http"),
                    f"unresolved placeholder {href!r} in {card['id']}",
                )

    def test_resource_view_warns_on_missing_pdf(self, ):
        # A card pointing at a non-existent static PDF triggers the warning.
        from unittest.mock import patch

        with patch("pages.views.finders.find", return_value=None):
            with self.assertLogs("pages.views", level="WARNING") as logs:
                self.client.get(reverse("resource"))
        self.assertTrue(any("missing PDF" in line for line in logs.output))


@override_settings(MAPTILER_API_KEY="test-maptiler-key")
class PlannerViewTests(TestCase):
    """The old get_started redirect target and the planner route itself."""

    def test_planner_url_resolves_and_renders(self):
        response = self.client.get(reverse("planner"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "hunting/planner.html")

    def test_planner_receives_maptiler_key(self):
        # The key comes from the shared config.maptiler helper.
        response = self.client.get(reverse("planner"))
        self.assertIn("MAPTILER_API_KEY", response.context)
        self.assertEqual(response.context["MAPTILER_API_KEY"], "test-maptiler-key")
