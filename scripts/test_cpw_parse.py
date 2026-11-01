"""Pytest tests for the CPW PDF regex parsers in scripts/cpw_parse.py.

These use short fixture text snippets that mirror the real CPW table
layouts, so no PDFs are needed — we exercise the regex parsers directly
with the same line shapes pdfplumber extracts from the real documents.
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from cpw_parse import BEAR_RE, HARVEST_RE, QUOTA_RE, parse_bear, parse_eight_col, parse_tables  # noqa: E402


# --- Fixture text snippets (mirroring real CPW PDF table rows) -------------

HARVEST_LINE = "201  2,145  1,876  312  4,333  12,401  35  118,552"
BEAR_LINE = "201 12 8 20 44"
QUOTA_TEXT = (
    "EE101O1M  Elk  GMU 201  Either Sex\n"
    "201 LPP Restricted (up to)  25  25  Determined\n"
)


def test_harvest_re_matches_eight_col_row():
    m = HARVEST_RE.match(HARVEST_LINE)
    assert m is not None
    gmu, males, females, young, total, hunters, pct, days = m.groups()
    assert (gmu, males, females, young, total, hunters, pct, days) == (
        "201", "2,145", "1,876", "312", "4,333", "12,401", "35", "118,552",
    )


def test_harvest_re_rejects_short_rows():
    # A 3-column summary row must not be mistaken for an 8-column harvest row.
    assert HARVEST_RE.match("201  4,333  12,401") is None


def test_bear_re_matches_bear_row():
    m = BEAR_RE.match(BEAR_LINE)
    assert m is not None
    gmu, boars, sows, harvest, days = m.groups()
    assert (gmu, boars, sows, harvest, days) == ("201", "12", "8", "20", "44")


def test_quota_re_extracts_quota_and_sex_totals():
    m = QUOTA_RE.search(QUOTA_TEXT)
    assert m is not None
    # group(1) is the GMU prefix on the line; group(2) is the quota count.
    assert m.group(1) == "201"
    assert m.group(2) == "25"


def test_parse_eight_col(tmp_path):
    pdf = tmp_path / "elk_2023.pdf"
    pdf.write_text("")  # parse_eight_col reads via pdfplumber text extraction
    # pdfplumber returns no text for an empty PDF, so feed the regex path
    # through a stubbed text source instead: verify against the raw regex.
    # To keep this test dependency-free of real PDFs, exercise the parser
    # with a monkeypatched line iterator.
    import cpw_parse

    cpw_parse.iter_pdf_lines = lambda _pdf: iter([HARVEST_LINE])
    stats = parse_eight_col(str(pdf))
    assert stats == {"201": {"harvest": 4333, "hunters": 12401, "success_pct": 35}}


def test_parse_bear(tmp_path):
    import cpw_parse

    cpw_parse.iter_pdf_lines = lambda _pdf: iter([BEAR_LINE])
    stats = parse_bear(str(tmp_path / "bear_2023.pdf"))
    assert stats == {"201": {"harvest": 20, "rec_days": 44}}


def test_parse_tables_routes_rows_by_season_marker(tmp_path, monkeypatch):
    import cpw_parse

    tables = {"all": "for All Manners of Take", "rifle_1": "for First Rifle Seasons"}

    class FakePage:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class FakePdf:
        pages = [
            FakePage("2023 for All Manners of Take\n" + HARVEST_LINE),
            FakePage("2023 for First Rifle Seasons\n" + HARVEST_LINE),
        ]

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(cpw_parse.pdfplumber, "open", lambda _pdf: FakePdf())
    out = parse_tables(str(tmp_path / "elk.pdf"), tables)
    assert set(out) == {"all", "rifle_1"}
    for season in out.values():
        assert season["201"] == {
            "harvest": 4333,
            "hunters": 12401,
            "success_pct": 35,
            "males": 2145,
            "females": 1876,
            "young": 312,
        }


def test_parse_tables_bear_variant(tmp_path, monkeypatch):
    import cpw_parse

    tables = {"all": "for All Manners of Take"}

    class FakePage:
        def extract_text(self):
            return "2023 for All Manners of Take\n" + BEAR_LINE

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(cpw_parse.pdfplumber, "open", lambda _pdf: FakePdf())
    out = parse_tables(str(tmp_path / "bear.pdf"), tables, bear=True)
    assert out == {
        "all": {"201": {"harvest": 20, "rec_days": 44, "males": 12, "females": 8}}
    }
