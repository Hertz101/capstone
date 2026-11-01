"""Multi-year CPW harvest extractor -> static/hunting/elk_stats.json."""
import argparse
import json
import sys
from pathlib import Path

from cpw_parse import BEAR_RE, HARVEST_RE, licenses_by_sex, parse_tables

ELK_TABLES = {"all": "for All Manners of Take","rifle_1": "for First Rifle Seasons","rifle_2": "for Second Rifle Seasons","rifle_3": "for Third Rifle Seasons","rifle_4": "for Fourth Rifle Seasons","archery": "for All Archery Seasons","muzzleloader": "for All Muzzleloader Seasons"}
DEER_TABLES = {"all": "for All Manners of Take","rifle_2": "for 2nd Rifle Seasons","rifle_3": "for 3rd Rifle Seasons","rifle_4": "for 4th Rifle Seasons","archery": "for All Archery Seasons","muzzleloader": "for All Muzzleloader Seasons"}
PRONG_TABLES = {"all": "for All Manners of Take","rifle": "for All Rifle Seasons","archery": "for All Archery Seasons","muzzleloader": "for All Muzzleloader Seasons"}
BEAR_TABLES = {"all": "for All Manners of Take","september": "for All September Seasons","archery": "for September Archery Seasons","muzzleloader": "for September Muzzleloader Seasons","rifle": "for September Regular Rifle Seasons"}

SPECS = [
    ("elk", ELK_TABLES, False),
    ("deer", DEER_TABLES, False),
    ("pronghorn", PRONG_TABLES, False),
    ("bear", BEAR_TABLES, True),
]

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "static" / "hunting" / "elk_stats.json"


def sexdict(d):
    return {g: {"bull": v.get("M", 0), "cow": v.get("F", 0), "either": v.get("E", 0)} for g, v in d.items()}


def main(years, input_dir):
    input_dir = Path(input_dir).expanduser().resolve()
    if not input_dir.is_dir():
        sys.exit(f"ERROR: input directory not found: {input_dir}")

    # Recap PDFs (draw licenses); fail loudly if any are missing up front.
    recap_names = {"elk": "elk_recap.pdf", "deer": "deer_recap.pdf", "pronghorn": "prong_recap.pdf"}
    recaps = {}
    for species, name in recap_names.items():
        path = input_dir / name
        if not path.is_file():
            sys.exit(f"ERROR: missing recap PDF for {species}: expected {path}")
        recaps[species] = str(path)

    seasons = {s: {} for s, _, _ in SPECS}
    for species, tables, bear in SPECS:
        for y in years:
            try:
                parsed = parse_tables(str(input_dir / f"{species}_{y}.pdf"), tables, bear)
            except Exception as e:
                print(f"WARN {species} {y}: {e}")
                parsed = {k: {} for k in tables}
            for season in tables:
                seasons[species].setdefault(season, {})[str(y)] = parsed[season]

    elk_lic = licenses_by_sex(recaps["elk"], "E")
    deer_lic = licenses_by_sex(recaps["deer"], "D")
    prong_lic = licenses_by_sex(recaps["pronghorn"], "A")

    latest = str(max(years))
    data = {
        "harvest_years": years,
        "license_year": 2026,
        "source": "CPW Statewide Harvest Estimates; CPW 2026 Post-Draw Reports (elk, deer, pronghorn)",
        "seasons": seasons,
        "licenses": {
            "elk": sexdict(elk_lic),
            "deer": sexdict(deer_lic),
            "pronghorn": sexdict(prong_lic),
            "bear": {},
        },
        "units": {
            g: {**row, **({"licenses_bull": elk_lic[g].get("M"), "licenses_cow": elk_lic[g].get("F"),
                           "licenses_either": elk_lic[g].get("E")} if g in elk_lic else {})}
            for g, row in seasons["elk"]["all"][latest].items()
        },
        "deer": {"year": max(years), "units": seasons["deer"]["all"][latest]},
        "bear": {"year": max(years), "units": seasons["bear"]["all"][latest]},
        "pronghorn": {"year": max(years), "units": seasons["pronghorn"]["all"][latest]},
    }
    OUT.write_text(json.dumps(data))
    print(f"wrote {OUT}")
    for s in seasons:
        print(" ", s, {y: len(seasons[s]["all"][str(y)]) for y in years})
    print("license units elk/deer/prong:",
          len(data["licenses"]["elk"]), len(data["licenses"]["deer"]), len(data["licenses"]["pronghorn"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", default="/tmp", help="Directory containing the CPW recap/harvest PDFs (e.g. elk_recap.pdf, elk_2023.pdf)")
    parser.add_argument("--years", nargs="+", type=int, default=[2023, 2022, 2021, 2020, 2019], help="Harvest years to extract")
    args = parser.parse_args()
    main(args.years, args.input_dir)
