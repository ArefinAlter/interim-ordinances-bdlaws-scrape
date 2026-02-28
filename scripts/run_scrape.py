from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bdlaws_scraper.config import load_config
from bdlaws_scraper.pipeline import run_scrape


def main() -> None:
    config = load_config()
    records = run_scrape(config)
    print(f"Saved {len(records)} ordinance records.")


if __name__ == "__main__":
    main()
