
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


PRE_HUNT_CHECKLIST = [
    {
        "id": "hunting-gear",
        "icon": "🎒",
        "title": "Hunting gear",
        "items": [
            "Maps", "Compass or GPS", "Hunting pack",
            "Water bottle or hydration bladder",
            "Blaze orange tape for route marking",
            "Decoys and game calls", "Scent eliminators", "Scent attractors",
            "Ground blind or portable tree stand", "Binoculars / rangefinder",
            "Firearm / ammo", "Bow / arrows / release",
            "Game carrier (sled / cart / rope)", "Cooler",
            "Odorless insect repellent", "Sunscreen", "Knives for Harvesting", "Game Bags"
        ],
    },
    {
        "id": "hunting-clothing",
        "icon": "🧥",
        "title": "Hunting clothing",
        "items": [
            "Hunting jacket / convertible parka", "Hunting pants", "Hunting vest",
            "Hunting boots", "Performance base layer / long underwear",
            "Moisture-wicking socks", "Winter watch cap or beanie",
            "Hat (blaze orange, if required)",
            "Fingerless gloves / convertible mittens",
            "Camo balaclava / face mask", "Belt", "Boot gaiters", "Spare clothing",
        ],
    },
    {
        "id": "overnight-gear",
        "icon": "⛺",
        "title": "Overnight gear",
        "items": [
            "Tent", "Ground cloth or tent footprint", "Sleeping bag",
            "Foam ground pad or inflatable pad", "Flashlight / headlamp / lantern",
            "Camp chair / stool / seat pad", "Water purifier / filter", "Water jug",
            "Meals and snacks", "Camping stove",
            "Mess kit / utensils / cooking supplies", "Garbage bag",
            "Rope or nylon webbing", "Biodegradable camp soap",
            "Scrubbing sponge and washcloth", "Small shovel / trowel", "Toilet paper",
            "Bear bag with rope or cord", "Tent / tarp patch kit",
        ],
    },
    {
        "id": "emergency",
        "icon": "🩹",
        "title": "Emergency / survival gear",
        "items": [
            "First aid kit", "Emergency blanket", "Small flashlight",
            "Signal mirror", "Water purification tablets", "Windproof matches",
            "Firesteel / flint and steel", "Fire starting supplies",
            "Small sewing kit", "Safety pins", "Survival knife or multi-tool",
            "Portable saw", "Energy bar", "Aspirin / pain reliever", "Cell phone", "External battery for phones", "Cables"
        ],
    },
]


def your_trip_view(request):
    """Interactive pre-hunt checklist, grouped like the classic pre-hunt lists."""
    return render(request, "pages/your_trip.html", {
        "checklist": PRE_HUNT_CHECKLIST,
    })


def blog_view(request):
    return render(request, "pages/blog.html")


def group_chat_view(request):
    return render(request, "pages/group_chat.html")


def resource_view(request):
    """Resources page content. Add info by editing this data — the
    template loops over it, so structure never needs hand-editing."""
    resources = [
        {
            # What's New — refresh each year when CPW publishes the new
            # big-game brochure. Update the title year, bullets, and links.
            "id": "whats-new",
            "img": "img/elk.jpeg",
            "kicker": "Updated for 2026",
            "title": "What's New: 2026 Regulations",
            "sections": [
                {
                    "heading": "New for 2026",
                    "bullets": [
                        "Moose: certain hunt codes have limited 2026 draw quota reserved for 2025 license holders affected by the fires. Hunt codes shaded orange in the brochure tables (pages 59–61) have limited quota. Others are not eligible for a guaranteed 2026 license unless contacted by CPW.",
                        "CWD testing: mandatory chronic wasting disease submission (heads) for elk harvested during rifle seasons in select GMUs — no charge. Check cpw.state.co.us/cwd for how to submit and page 41 for the mandatory GMU list. No mandatory deer testing in 2026.",
                        "Moose lifetime bag limits: bull moose harvested with a Turn In Poachers (TIPs) license no longer count against your lifetime bag limit, so reporting poaching won't cost you future draw opportunity.",
                        "GMU boundary changes: updated descriptions for GMUs 97 and 99 (page 71).",
                        "GMU 74 closure: Forest Service closure on Hermosa Park Rd. (FS 578) Sept. 8–Oct. 13, 2026 blocks access to a major portion of the unit. Call the Columbine Ranger District at 970-501-5830.",
                        "Ranching for Wildlife: elk antler-point restrictions on RFW properties now follow the rules of the GMU the ranch sits in (page 36).",
                    ],
                },
                {
                    "heading": "New hunts and license changes",
                    "bullets": [
                        "First-season rifle deer buck hunts added for GMU groups 75/751 and 77/78/771 (pages 30–32).",
                        "Elk OTC and nonresident archery added in GMUs 59, 511, 581 & 591 (pages 38, 43).",
                        "GMUs 54, 55 & 551: second/third-season rifle bull elk licenses moved from unlimited OTC to limited draw (pages 48, 52).",
                        "Second-season rifle pronghorn doe hunt for GMUs 6, 16, 17, 161 & 171 (pages 56–57).",
                        "New resident moose bull and cow hunts for GMUs 55 & 551 (pages 59–61).",
                        "New private-land-only rifle bear hunts for units 3, 11, 211 & 301 (page 64).",
                        "Species-by-species changes: Deer p. 20, Elk p. 35, Pronghorn p. 53, Moose p. 58, Bear p. 62.",
                    ],
                },
                {
                    "heading": "Fees and reminders",
                    "bullets": [
                        "Backcountry Search & Rescue surcharge increased from $0.25 to $1.25 — its first change since 1987 (cpw.state.co.us/BSAR).",
                        "Reminder — nonresident archery elk: no more OTC archery elk licenses west of I-25 and GMU 140; those are now limited draw codes (page 43). OTC remains available east of I-25 via codes E-F-133-U1-A and E-E-087-U1-A.",
                        "Reminder — 2028 draw overhaul: the Draw Process Working Group policy changes take effect in 2028 (cpw.state.co.us/2028-draw).",
                        "Bison: free-ranging bison are now managed as a big-game species under SB25-053. No regular seasons proposed; special management licenses draw from the Bison Roster (cpw.state.co.us/bison-roster; the 2026 window closed Jan. 31).",
                    ],
                },
            ],
            "links": [
                ("Full 2026 Big Game Brochure →", "https://cpw.state.co.us/activities/hunting/big-game"),
            ],
        },
        {
            "img": "img/planning.jpg",
            "kicker": "Guide",
            "title": "Hunt Planning Basics",
            "sections": [
                {
                    "heading": "Getting started",
                    "bullets": [
                        "Pick a species and method first — they determine your license options and draw strategy.",
                        "Choose 2–3 backup GMUs in the same DAU so a failed draw doesn't end your season.",
                        "Verify season dates and regulations in the current CPW big-game brochure every year.",
                    ],
                },
                {
                    "heading": "Access & scouting",
                    "bullets": [
                        "Check CPW public-access maps and Walk-In properties for your target GMUs.",
                        "Look for road closures and fire restrictions before every trip.",
                        "Scout on foot or on the map well before opening day.",
                    ],
                },
            ],
            "links": [
                ("Open the Hunt Planner →", "{planner}"),
            ],
        },
        {
            "id": "licenses",
            "img": "img/tools.jpg",
            "kicker": "Reference",
            "title": "Licenses & the Draw",
            "sections": [
                {
                    "heading": "Draw timeline",
                    "bullets": [
                        "Colorado's primary draw applications are typically due in early April.",
                        "Draw results are posted in late spring; leftover licenses follow.",
                        "Leftover and OTC licenses go on sale after the draw results are posted.",
                    ],
                },
                {
                    "heading": "Points & costs",
                    "bullets": [
                        "Preference points only improve odds for the species you actually apply for.",
                        "Buy your habitat stamp once per year — it's required with every license.",
                        "Small-game licenses can be a cheap fallback if the big-game draw fails.",
                    ],
                },
            ],
            "links": [
                ("CPW 2026 Big Game Brochure →", "https://cpw.state.co.us/activities/hunting/big-game"),
            ],
        },
        {
            "id": "stats",
            "img": "img/elk.jpeg",
            "kicker": "Data",
            "title": "Harvest Statistics",
            "sections": [
                {
                    "heading": "Using the numbers",
                    "bullets": [
                        "Use the interactive map on our Hunt Map page to see harvest and success rates by GMU.",
                        "CPW publishes post-draw recaps and harvest estimates every spring for the prior season.",
                        "Success rates vary a lot by season — archery and muzzleloader differ from rifle hunts.",
                    ],
                },
                {
                    "heading": "Reading a report",
                    "bullets": [
                        "Hunter numbers matter as much as harvest — 20 animals from 200 hunters is a different unit than 20 from 30.",
                        "Check sex breakdowns: cow-heavy units hunt differently from bull-only draws.",
                    ],
                },
            ],
            "links": [
                ("Explore the Hunt Map →", "{maps}"),
            ],
        },
        {
            "id": "gear",
            "img": "img/powder.jpeg",
            "kicker": "Checklist",
            "title": "Gear & Field Prep",
            "sections": [
                {
                    "heading": "Legal requirements",
                    "bullets": [
                        "Blaze orange requirements apply during rifle seasons — check the current brochure.",
                    ],
                },
                {
                    "heading": "Before you leave",
                    "bullets": [
                        "Test everything before opening day: optics, boots, and any weapon.",
                        "Carry a paper map or offline GPS — cell coverage is unreliable in most GMUs.",
                        "Plan for weather swings: early seasons can run from snow to 80°F in one week.",
                    ],
                },
            ],
            "links": [
                ("Build your pre-hunt checklist →", "{your_trip}"),
                ("CPW Regulations →", "https://cpw.state.co.us"),
            ],
        },
        {
            # PDF link card — no "sections" needed; the hero opens the PDF.
            # Put the file in static/hunting/ (or anywhere under static/) and
            # reference it with the "pdf" key instead of "sections"/"links".
            "id": "ohv",
            "img": "img/tools.jpg",
            "kicker": "Regulations",
            "title": "OHV Regulations (Ch. P-5)",
            "pdf": "hunting/chapter-p5-ohv.pdf",
        },

        {

            "id": "biggame",
            "img": "img/elk.jpeg",
            "kicker": "Regulations",
            "title": "Big Game Regulations (Ch. W-2)",
            "pdf": "hunting/chapter-w2-big-game-regs.pdf",
        },
    ]

    # Resolve internal named-URL placeholders in link targets.
    from django.urls import reverse
    for card in resources:
        card["links"] = [
            (label, reverse(placeholder[1:-1]) if placeholder.startswith("{") else placeholder)
            for label, placeholder in card.get("links", [])
        ]

    return render(request, "pages/resource.html", {
        "resources": resources,
    })
