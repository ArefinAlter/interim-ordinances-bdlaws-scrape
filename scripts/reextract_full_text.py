"""Re-extract full text from existing act-details HTML files (no re-scraping)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bdlaws_scraper.parse import extract_full_text_from_act_details

FULL_TEXT_DIR = ROOT / "data" / "full_text"


def main() -> None:
    if not FULL_TEXT_DIR.exists():
        print("data/full_text/ not found")
        return
    count = 0
    for html_path in sorted(FULL_TEXT_DIR.glob("act-details-*.html")):
        txt_path = html_path.with_suffix(".txt")
        html = html_path.read_text(encoding="utf-8-sig")
        text = extract_full_text_from_act_details(html)
        txt_path.write_text(text, encoding="utf-8-sig")
        count += 1
        print(f"  {html_path.name} -> {txt_path.name}")
    print(f"Re-extracted {count} full-text files")


if __name__ == "__main__":
    main()
