from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from dateutil import parser as date_parser


def safe_filename(text: str, max_len: int = 120) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", text).strip("-")
    if not cleaned:
        cleaned = "item"
    return cleaned[:max_len]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def normalize_url(base_url: str, href: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", href)


def parse_date_from_text(text: str) -> Optional[date]:
    text = text.strip()
    if not text:
        return None
    text = normalize_bengali_digits(text)
    text = normalize_bengali_months(text)
    try:
        parsed = date_parser.parse(text, dayfirst=True, fuzzy=True)
        return parsed.date()
    except (ValueError, TypeError):
        return None


def normalize_title(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[\(\)\[\]\{\}\.,;:!?/]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def strip_amendment_terms(text: str) -> str:
    terms = (
        "amendment",
        "amending",
        "amended",
        "amendments",
        "amendatory",
        "amendment ordinance",
        "amendment act",
        "amendment order",
        "second amendment",
        "first amendment",
        "সংশোধন",
        "সংবাদ",
        "সংশোধনী",
        "দ্বিতীয় সংশোধন",
        "প্রথম সংশোধন",
    )
    stripped = text
    for term in terms:
        stripped = stripped.replace(term, " ")
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return stripped


def normalize_bengali_digits(text: str) -> str:
    mapping = str.maketrans(
        {
            "০": "0",
            "১": "1",
            "২": "2",
            "৩": "3",
            "৪": "4",
            "৫": "5",
            "৬": "6",
            "৭": "7",
            "৮": "8",
            "৯": "9",
        }
    )
    return text.translate(mapping)


def normalize_bengali_months(text: str) -> str:
    months = {
        "জানুয়ারি": "January",
        "ফেব্রুয়ারি": "February",
        "মার্চ": "March",
        "এপ্রিল": "April",
        "মে": "May",
        "জুন": "June",
        "জুলাই": "July",
        "অগাস্ট": "August",
        "আগস্ট": "August",
        "সেপ্টেম্বর": "September",
        "অক্টোবর": "October",
        "নভেম্বর": "November",
        "ডিসেম্বর": "December",
    }
    normalized = text
    for bn, en in months.items():
        normalized = normalized.replace(bn, en)
    return normalized


def is_numeric_text(text: str) -> bool:
    normalized = normalize_bengali_digits(text)
    normalized = re.sub(r"\s+", "", normalized)
    return bool(normalized) and normalized.isdigit()
