"""Extract per-GMU big-game stats from CPW PDFs into static/hunting/elk_stats.json.

Sources (all published by CPW as PDFs):
- Harvest Estimates PDFs (elk, deer, bear, pronghorn) -> harvest/hunters/success by GMU
- Elk Post-Draw Recap Report PDF -> license quotas by hunt code (elk only)

Usage:
    ./venv/bin/python scripts/extract_elk_stats.py ELK.pdf DEER.pdf BEAR.pdf PRONGHORN.pdf [RECAP.pdf]

Download the PDFs from:
- https://cpw.state.co.us/activities/hunting/big-game/hunting-elk/elk-statistics
- https://cpw.state.co.us/activities/hunting/big-game/hunting-deer/deer-statistics
- https://cpw.state.co.us/activities/hunting/big-game/hunting-bear/bear-statistics
- https://cpw.state.co.us/activities/hunting/big-game/hunting-pronghorn/pronghorn-statistics
"""

import json
import re
import sys
from pathlib import Path

import pdfplumber

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT = BASE_DIR / "static" / "hunting" / "elk_stats.json"

BEAR_RE = re.compile(r"^(\d{3})\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)$")


def parse_eight_col(pdf_path: str) -> dict:
    """Parse 'for All Manners of Take' tables -> {gmu: {harvest, hunters, success_pct}}."""
    stats = {}
    row_re = re.compile(
        r"^(\d{3})\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+(\d+)\s+([\d,]+)$"
    )
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if "for All Manners of Take" not in text:
                continue
            for line in text.splitlines():
                m = row_re.match(line.strip())
                if m:
                    unit, _a, _b, _c, total, hunters, pct, _days = m.groups()
                    stats[unit] = {
                        "harvest": int(total.replace(",", "")),
                        "hunters": int(hunters.replace(",", "")),
                        "success_pct": int(pct),
                    }
    return stats


def parse_bear(pdf_path: str) -> dict:
    """Bear tables only publish unit boars sows harvest days (no hunters/success)."""
    stats = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if "for All Manners of Take" not in text:
                continue
            for line in text.splitlines():
                m = BEAR_RE.match(line.strip())
                if m:
                    stats[m.group(1)] = {
                        "harvest": int(m.group(4)),
                        "rec_days": int(m.group(5)),
                    }
    return stats


def parse_licenses(pdf_path: str) -> dict:
    """Parse draw recap -> {gmu: total_quota} summed across the unit's hunt codes."""
    quotas = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            code = re.search(r"\bE[A-Z](\d{3})[A-Z0-9]+\b", text)
            if not code:
                continue
            gmu = code.group(1)
            q = re.search(
                r"^(\d+)\s+LPP Restricted \(up to\).*?(\d+)\s+(\d+)\s+Determined",
                text,
                re.M,
            )
            if q:
                quotas[gmu] = quotas.get(gmu, 0) + int(q.group(2))
    return quotas


def main() -> None:
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(1)
    harvest_path, deer_path, bear_path, pronghorn_path = sys.argv[1:5]
    recap_path = sys.argv[5] if len(sys.argv) > 5 else None

    harvest = parse_eight_col(harvest_path)
    licenses = parse_licenses(recap_path)
    print(f"harvest units: {len(harvest)}, license units: {len(licenses)}")

    # --- Extra species: deer, bear, pronghorn (2023 harvest estimates) ---
    deer = parse_eight_col(deer_path) if deer_path else {}
    bear = parse_bear(bear_path) if bear_path else {}
    pronghorn = parse_eight_col(pronghorn_path) if pronghorn_path else {}
    print(
        f"deer units: {len(deer)}, bear units: {len(bear)}, "
        f"pronghorn units: {len(pronghorn)}"
    )

    data = {
        "harvest_year": 2023,
        "license_year": 2026,
        "source": (
            "CPW 2023 Statewide Elk Harvest Estimates; "
            "CPW 2026 Primary Elk Post-Draw Report"
        ),
        "units": {},
        "deer": {
            "year": 2023,
            "source": "CPW 2023 Statewide Deer Harvest Estimates",
            "units": deer,
        },
        "bear": {
            "year": 2023,
            "source": "CPW 2023 Statewide Bear Harvest Estimates "
            "(hunters/success not published by unit)",
            "units": bear,
        },
        "pronghorn": {
            "year": 2023,
            "source": "CPW 2023 Statewide Pronghorn Harvest Estimates",
            "units": pronghorn,
        },
    }
    for gmu, h in harvest.items():
        data["units"][gmu] = {**h, "licenses": licenses.get(gmu)}
    for gmu, q in licenses.items():
        data["units"].setdefault(gmu, {"licenses": q})

    OUTPUT.write_text(json.dumps(data))
    print(f"wrote {OUTPUT} ({len(data['units'])} units)")


if __name__ == "__main__":
    main()
