"""Test parsing against local page-source files or fixtures (no network)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bdlaws_scraper.parse import parse_detail_page, parse_index_entries
from bdlaws_scraper.utils import normalize_url

BASE = "http://bdlaws.minlaw.gov.bd"


def main() -> None:
    # Test with fixture first (always works)
    fixture = ROOT / "tests" / "fixtures" / "sample_ordinance.html"
    if fixture.exists():
        html = fixture.read_text(encoding="utf-8")
        parsed = parse_detail_page(html, "http://bdlaws.minlaw.gov.bd/act-1594.html", BASE)
        print("=== sample_ordinance.html (fixture) ===")
        print("  title:", parsed["title"][:30] + "..." if len(parsed["title"] or "") > 30 else parsed["title"])
        print("  enactment_date:", parsed["enactment_date"])
        print("  pdf_url:", "OK" if parsed["pdf_url"] else None)
        print("  act_details_url:", "OK" if parsed["act_details_url"] else None)
        assert parsed["title"] == "বাণিজ্যিক আদালত অধ্যাদেশ, ২০২৬"
        assert parsed["enactment_date"] == "2026-01-01"
        assert parsed["pdf_url"] is not None
        assert parsed["act_details_url"] is not None
        print("  OK: All assertions passed")

    page_source = ROOT / "page-source"
    if not page_source.exists():
        return

    # Test act1594 from page-source if present and non-empty
    act_path = page_source / "bdlaws-act1594.html"
    if act_path.exists():
        html = act_path.read_text(encoding="utf-8")
        if not html:
            print("\nbdlaws-act1594.html is empty - paste View Source content first")
        else:
            parsed = parse_detail_page(html, "http://bdlaws.minlaw.gov.bd/act-1594.html", BASE)
            print("\n=== bdlaws-act1594.html ===")
            for k, v in parsed.items():
                print(f"  {k}: {v}")

    # Test chronological index
    chrono_path = page_source / "bdlaws-chronological.html"
    if chrono_path.exists():
        html = chrono_path.read_text(encoding="utf-8")
        if html:
            entries = parse_index_entries(html, BASE)
            ordinance_2026 = [(u, t) for u, t in entries if "২০২৬" in t or "2026" in t]
            print("\n=== Chronological index (2026 ordinances sample) ===")
            for url, title in ordinance_2026[:5]:
                print(f"  {title[:60]}... -> {url}")


if __name__ == "__main__":
    main()
