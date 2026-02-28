"""Regenerate CSV/JSONL with act numbers instead of full text (no re-scraping)."""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DATA_DIR = ROOT / "data" / "processed"


def extract_act_id(url: str | None) -> str | None:
    if not url:
        return None
    m = re.search(r"act-(\d+)\.html", url)
    return f"act-{m.group(1)}" if m else None


def main() -> None:
    jsonl_path = DATA_DIR / "ordinances.jsonl"
    if not jsonl_path.exists():
        print("ordinances.jsonl not found")
        return

    records = []
    with jsonl_path.open(encoding="utf-8-sig") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            act_id = extract_act_id(rec.get("detail_url"))
            orig_act_id = extract_act_id(rec.get("original_detail_url"))
            rec["act_id"] = act_id
            rec["original_act_id"] = orig_act_id
            rec.pop("full_text", None)
            rec.pop("original_full_text", None)
            records.append(rec)

    fieldnames = [
        "title", "detail_url", "act_details_url", "enactment_date", "document_type",
        "pdf_url", "raw_source", "act_id", "full_text_source", "is_amendment",
        "original_detail_url", "original_title", "original_raw_source",
        "original_act_details_url", "original_act_id", "original_full_text_source",
        "original_enactment_date",
    ]

    csv_path = DATA_DIR / "ordinances.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            writer.writerow(rec)

    with jsonl_path.open("w", encoding="utf-8-sig") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Updated {len(records)} records in {csv_path} and {jsonl_path}")


if __name__ == "__main__":
    main()
