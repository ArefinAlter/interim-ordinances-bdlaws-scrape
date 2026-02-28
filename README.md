# BDLaws Interim Ordinances Scraper

Scrape Bangladesh interim-government ordinances from the BDLaws site for the
period **2024-08-05 to 2026-02-14**.

## Project layout

- `src/bdlaws_scraper/` — scraper package
- `scripts/` — runnable entry points
- `config/` — configuration files
- `data/raw/` — raw HTML responses
- `data/processed/` — extracted records
- `logs/` — run logs
- `docs/` — notes and references

## Setup

1. Create a virtual environment (recommended).
2. Install dependencies:
   - `pip install -r requirements.txt`

## Configure

Edit `config/config.json` as needed. The defaults already target:
- `start_date`: `2024-08-05`
- `end_date`: `2026-02-14`
- `volume_urls`: 2024–2026 ordinance volumes (55, 56, 57)
- `use_chronological_index`: `false` — set `true` to use the full chronological index instead (filters by year 2024–2026 and ordinance-only)

## Run

```
python scripts/run_scrape.py
```

Outputs:
- Raw HTML saved to `data/raw/`
- Extracted records to `data/processed/ordinances.jsonl` and
  `data/processed/ordinances.csv`
- If a scraped ordinance title includes amendment terms (e.g., "Amendment",
  "সংশোধন"), the scraper also downloads the original law's page and links it
  in the output (from any linked act page or by title matching).

## Test parsing (no network)

```
python scripts/test_parse_local.py
```

Uses `tests/fixtures/sample_ordinance.html` and, if present, `page-source/*.html`.

## Notes

See `docs/NOTES.md` for assumptions and parsing heuristics.
