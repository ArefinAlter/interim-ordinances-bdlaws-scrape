from __future__ import annotations

import csv
import json
import re
from datetime import date
from pathlib import Path
from typing import Iterable, List

from tqdm import tqdm

from .config import ScrapeConfig
from .http_client import build_session, get_html
from .models import OrdinanceRecord
from .parse import (
    extract_act_links,
    extract_full_text_from_act_details,
    parse_chronological_index_entries,
    parse_detail_page,
    parse_index_entries,
)
from .utils import (
    ensure_dir,
    normalize_title,
    normalize_url,
    parse_date_from_text,
    safe_filename,
    strip_amendment_terms,
)


def run_scrape(config: ScrapeConfig) -> List[OrdinanceRecord]:
    ensure_dir(config.raw_dir)
    ensure_dir(config.output_dir)
    ensure_dir(config.full_text_dir)

    session = build_session(config)
    index_entries: List[tuple[str, str]] = []
    if config.use_chronological_index:
        chrono_html = get_html(
            session,
            config.chronological_index_url,
            delay_seconds=config.request_delay_seconds,
        )
        _write_raw(config.raw_dir / "chronological-index.html", chrono_html)
        index_entries = parse_chronological_index_entries(
            chrono_html,
            config.base_url,
            year_filter=[2024, 2025, 2026],
            ordinance_only=True,
        )
    else:
        for idx, volume_url in enumerate(config.volume_urls, start=1):
            volume_html = get_html(
                session,
                volume_url,
                delay_seconds=config.request_delay_seconds,
            )
            _write_raw(config.raw_dir / f"volume-{idx}.html", volume_html)
            index_entries.extend(parse_index_entries(volume_html, config.base_url))

    detail_links = sorted({url for url, _ in index_entries})
    title_lookup = _build_title_lookup(index_entries)
    records: List[OrdinanceRecord] = []
    fetched_full_text: set[str] = set()

    for url in tqdm(detail_links[: config.max_pages], desc="Fetching details"):
        html = get_html(session, url, delay_seconds=config.request_delay_seconds)
        filename = safe_filename(url) + ".html"
        _write_raw(config.raw_dir / filename, html)

        parsed = parse_detail_page(html, url, config.base_url)
        is_amendment = _is_amendment_title(parsed["title"] or "")
        original = None
        original_raw = None
        original_title = None
        original_act_details_url = None
        original_full_text = None
        original_full_text_source = None
        original_enactment_date = None
        orig_act_id = "unknown"
        if is_amendment:
            candidate_links = [
                link
                for link in extract_act_links(html, config.base_url)
                if link != url and not _is_constitution_link(link)
            ]
            original = candidate_links[0] if candidate_links else None
            if not original:
                original = _find_original_link(parsed["title"] or "", title_lookup)
            if original:
                orig_act_id = _extract_act_id_from_url(original)
                original_html = get_html(
                    session, original, delay_seconds=config.request_delay_seconds
                )
                original_filename = safe_filename(original) + ".html"
                _write_raw(config.raw_dir / original_filename, original_html)
                original_parsed = parse_detail_page(original_html, original, config.base_url)
                original_title = original_parsed.get("title")
                original_raw = str(config.raw_dir / original_filename)
                original_enactment_date = _parse_iso_date(original_parsed.get("enactment_date"))
                orig_act_id = _extract_act_id_from_url(original)
                if orig_act_id != "unknown":
                    original_act_details_url = f"{config.base_url}/act-details-{orig_act_id}.html"
                    orig_full_txt_path = config.full_text_dir / f"act-details-{orig_act_id}.txt"
                    if orig_act_id in fetched_full_text and orig_full_txt_path.exists():
                        original_full_text_source = str(orig_full_txt_path)
                    else:
                        orig_full_html = get_html(
                            session, original_act_details_url, delay_seconds=config.request_delay_seconds
                        )
                        orig_full_html_path = config.full_text_dir / f"act-details-{orig_act_id}.html"
                        _write_raw(orig_full_html_path, orig_full_html)
                        original_full_text = extract_full_text_from_act_details(orig_full_html)
                        _write_raw(orig_full_txt_path, original_full_text)
                        original_full_text_source = str(orig_full_txt_path)
                        fetched_full_text.add(orig_act_id)
        pdf_url = parsed.get("pdf_url")
        if pdf_url and pdf_url.startswith("/"):
            pdf_url = normalize_url(config.base_url, pdf_url)
        act_details_url = parsed.get("act_details_url")
        if act_details_url and act_details_url.startswith("/"):
            act_details_url = normalize_url(config.base_url, act_details_url)
        act_id = _extract_act_id_from_url(url)
        if not act_details_url and act_id != "unknown":
            act_details_url = f"{config.base_url}/act-details-{act_id}.html"
        full_text_source = None
        full_text = None
        if act_details_url:
            full_html = get_html(
                session, act_details_url, delay_seconds=config.request_delay_seconds
            )
            full_html_path = config.full_text_dir / f"act-details-{act_id}.html"
            full_txt_path = config.full_text_dir / f"act-details-{act_id}.txt"
            _write_raw(full_html_path, full_html)
            full_text = extract_full_text_from_act_details(full_html)
            _write_raw(full_txt_path, full_text)
            full_text_source = str(full_txt_path)
        act_id_ref = f"act-{act_id}" if act_id != "unknown" else None
        orig_act_id_ref = f"act-{orig_act_id}" if original and orig_act_id != "unknown" else None
        record = OrdinanceRecord(
            title=parsed["title"] or "Unknown title",
            detail_url=url,
            act_details_url=act_details_url,
            enactment_date=_parse_iso_date(parsed.get("enactment_date")),
            document_type=parsed.get("document_type"),
            pdf_url=pdf_url,
            raw_source=str(config.raw_dir / filename),
            act_id=act_id_ref,
            full_text_source=full_text_source,
            is_amendment=is_amendment,
            original_detail_url=original,
            original_title=original_title,
            original_raw_source=original_raw,
            original_act_details_url=original_act_details_url,
            original_act_id=orig_act_id_ref,
            original_full_text_source=original_full_text_source,
            original_enactment_date=original_enactment_date,
        )

        if _within_window(record.enactment_date, config.start_date, config.end_date) and _is_ordinance(
            record
        ):
            records.append(record)

    _write_outputs(records, config.output_dir)
    return records


def _write_raw(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8-sig")


def _write_outputs(records: List[OrdinanceRecord], output_dir: Path) -> None:
    jsonl_path = output_dir / "ordinances.jsonl"
    csv_path = output_dir / "ordinances.csv"

    with jsonl_path.open("w", encoding="utf-8-sig") as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "title",
                "detail_url",
                "act_details_url",
                "enactment_date",
                "document_type",
                "pdf_url",
                "raw_source",
                "act_id",
                "full_text_source",
                "is_amendment",
                "original_detail_url",
                "original_title",
                "original_raw_source",
                "original_act_details_url",
                "original_act_id",
                "original_full_text_source",
                "original_enactment_date",
            ],
        )
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_dict())


def _within_window(value: date | None, start: date, end: date) -> bool:
    if value is None:
        return False
    return start <= value <= end


def _is_ordinance(record: OrdinanceRecord) -> bool:
    if record.document_type is None:
        return False
    return "ordinance" in record.document_type.lower()


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    return parse_date_from_text(value)


def _is_amendment_title(title: str) -> bool:
    normalized = normalize_title(title)
    return "amend" in normalized or "সংশোধন" in title


def _build_title_lookup(index_entries: List[tuple[str, str]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for url, text in index_entries:
        if not text:
            continue
        normalized = normalize_title(text)
        if normalized not in lookup:
            lookup[normalized] = url
    return lookup


def _find_original_link(title: str, lookup: dict[str, str]) -> str | None:
    normalized = normalize_title(title)
    stripped = strip_amendment_terms(normalized)
    if stripped in lookup:
        return lookup[stripped]
    return None


def _is_constitution_link(url: str) -> bool:
    return "/act-957" in url or "act-957.html" in url


def _extract_act_id_from_url(url: str) -> str:
    m = re.search(r"act-(\d+)\.html", url)
    return m.group(1) if m else "unknown"
