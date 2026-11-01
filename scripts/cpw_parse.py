"""Shared parsing helpers for the CPW PDF extractors.

Both scripts/extract_elk_stats.py (single-year, CLI-arg driven) and
scripts/extract_stats_multiyear.py (multi-year, /tmp-driven) read the same
kinds of CPW PDFs, so the row regexes and page-scan loops live here once.
"""

import re

import pdfplumber

# Harvest tables: GMU  males females young  total  hunters  success%  days
HARVEST_RE = re.compile(
    r"^(\d{1,3})\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+(\d+)\s+([\d,]+)$"
)

# Bear tables: GMU  boars  sows  harvest  days
BEAR_RE = re.compile(r"^(\d{3})\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)$")

# License quota line inside a post-draw recap page.
QUOTA_RE = re.compile(
    r"^(\d+)\s+LPP Restricted \(up to\).*?(\d+)\s+(\d+)\s+Determined", re.M
)

ALL_MANNERS = "for All Manners of Take"


def iter_pdf_lines(pdf_path):
    """Yield the stripped lines of every page containing a table marker.

    When `marker` is given, only pages whose text contains it are scanned.
    """
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            yield from (line.strip() for line in text.splitlines())


def parse_eight_col(pdf_path: str) -> dict:
    """Parse 'for All Manners of Take' tables -> {gmu: {harvest, hunters, success_pct}}."""
    stats = {}
    for line in iter_pdf_lines(pdf_path):
        m = HARVEST_RE.match(line)
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
    for line in iter_pdf_lines(pdf_path):
        m = BEAR_RE.match(line)
        if m:
            stats[m.group(1)] = {
                "harvest": int(m.group(4)),
                "rec_days": int(m.group(5)),
            }
    return stats


def parse_licenses(pdf_path: str) -> dict:
    """Parse elk draw recap -> {gmu: total_quota} summed across the unit's hunt codes."""
    quotas = {}
    code_re = re.compile(r"\bE[A-Z](\d{3})[A-Z0-9]+\b")
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            code = code_re.search(text)
            if not code:
                continue
            gmu = code.group(1)
            q = QUOTA_RE.search(text)
            if q:
                quotas[gmu] = quotas.get(gmu, 0) + int(q.group(2))
    return quotas


def parse_tables(pdf_path, tables, bear=False):
    """Multi-year variant: map every season key in `tables` to its per-GMU rows."""
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
                            data[m.group(1)] = {
                                "harvest": int(m.group(4)),
                                "rec_days": int(m.group(5)),
                                "males": int(m.group(2)),
                                "females": int(m.group(3)),
                            }
                    else:
                        m = HARVEST_RE.match(line)
                        if m:
                            data[m.group(1)] = {
                                "harvest": int(m.group(5).replace(",", "")),
                                "hunters": int(m.group(6).replace(",", "")),
                                "success_pct": int(m.group(7)),
                                "males": int(m.group(2).replace(",", "")),
                                "females": int(m.group(3).replace(",", "")),
                                "young": int(m.group(4).replace(",", "")),
                            }
    return out


def licenses_by_sex(pdf_path, prefix):
    """Parse draw recaps -> {gmu: {sex_letter: quota}} summed across hunt codes."""
    out = {}
    code_re = re.compile(rf"\b{prefix}([MEF])(\d{{3}})[A-Z0-9]+\b")
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            m = code_re.search(t)
            if not m:
                continue
            sex, gmu = m.group(1), m.group(2)
            q = QUOTA_RE.search(t)
            if not q:
                continue
            d = out.setdefault(gmu, {})
            d[sex] = d.get(sex, 0) + int(q.group(2))
    return out
