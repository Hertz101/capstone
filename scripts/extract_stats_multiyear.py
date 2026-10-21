"""Multi-year CPW harvest extractor -> static/hunting/elk_stats.json."""
import json
import re
from pathlib import Path

import pdfplumber

HARVEST_RE = re.compile(r"^(\d{1,3})\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+(\d+)\s+([\d,]+)$")
BEAR_RE = re.compile(r"^(\d{3})\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)$")

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


def parse_tables(pdf_path, tables, bear=False):
    out = {k: {} for k in tables}
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            for key, marker in tables.items():
                if marker not in t:
                    continue
                data = out[key]
                for line in t.splitlines():
                    line = line.strip()
                    if bear:
                        m = BEAR_RE.match(line)
                        if m and "Season" not in line:
                            data[m.group(1)] = {"harvest": int(m.group(4)), "rec_days": int(m.group(5)),
                                                "males": int(m.group(2)), "females": int(m.group(3))}
                    else:
                        m = HARVEST_RE.match(line)
                        if m:
                            data[m.group(1)] = {"harvest": int(m.group(5).replace(",", "")),
                                                "hunters": int(m.group(6).replace(",", "")),
                                                "success_pct": int(m.group(7)),
                                                "males": int(m.group(2).replace(",", "")),
                                                "females": int(m.group(3).replace(",", "")),
                                                "young": int(m.group(4).replace(",", ""))}
    return out


def licenses_by_sex(pdf_path, prefix):
    out = {}
    code_re = re.compile(rf"\b{prefix}([MEF])(\d{{3}})[A-Z0-9]+\b")
    quota_re = re.compile(r"^(\d+)\s+LPP Restricted \(up to\).*?(\d+)\s+(\d+)\s+Determined", re.M)
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            m = code_re.search(t)
            if not m:
                continue
            sex, gmu = m.group(1), m.group(2)
            q = quota_re.search(t)
            if not q:
                continue
            d = out.setdefault(gmu, {})
            d[sex] = d.get(sex, 0) + int(q.group(2))
    return out


def sexdict(d):
    return {g: {"bull": v.get("M", 0), "cow": v.get("F", 0), "either": v.get("E", 0)} for g, v in d.items()}


def main(years):
    seasons = {s: {} for s, _, _ in SPECS}
    for species, tables, bear in SPECS:
        for y in years:
            try:
                parsed = parse_tables(f"/tmp/{species}_{y}.pdf", tables, bear)
            except Exception as e:
                print(f"WARN {species} {y}: {e}")
                parsed = {k: {} for k in tables}
            for season in tables:
                seasons[species].setdefault(season, {})[str(y)] = parsed[season]

    elk_lic = licenses_by_sex("/tmp/elk_recap.pdf", "E")
    deer_lic = licenses_by_sex("/tmp/deer_recap.pdf", "D")
    prong_lic = licenses_by_sex("/tmp/prong_recap.pdf", "A")

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
    main([2023, 2022, 2021, 2020, 2019])
