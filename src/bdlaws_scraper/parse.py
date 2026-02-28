from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Tuple

from bs4 import BeautifulSoup

from .utils import is_numeric_text, normalize_bengali_digits, normalize_url, parse_date_from_text


DETAIL_LINK_PATTERNS = (
    r"/act-details-",
    r"/law-details-",
    r"/act-details\?id=",
    r"/law-details\?id=",
)

ACT_LINK_PATTERN = r"/(act|law)-\d+\.html"


def parse_index_links(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    links: List[str] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if _is_detail_link(href):
            links.append(normalize_url(base_url, href))
    return sorted(set(links))


def parse_index_entries(html: str, base_url: str) -> List[Tuple[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    entries: List[Tuple[str, str]] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if re.search(ACT_LINK_PATTERN, href) or _is_detail_link(href):
            url = normalize_url(base_url, href)
            text = anchor.get_text(" ", strip=True)
            if text and not _looks_like_law_number(text):
                entries.append((url, text))
    return entries


def parse_detail_page(html: str, url: str, base_url: str = "") -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")
    title = _extract_title(soup)
    pdf_url = _extract_pdf_url(soup)
    act_details_url = extract_act_details_url(soup, base_url) if base_url else None
    labels = _extract_labeled_fields(soup)
    page_text = soup.get_text(" ", strip=True)
    doc_type = _pick_document_type(labels, page_text, title)
    enactment_date = _pick_date(soup, labels, page_text)
    return {
        "title": title,
        "detail_url": url,
        "document_type": doc_type,
        "enactment_date": enactment_date.isoformat() if enactment_date else None,
        "pdf_url": pdf_url,
        "act_details_url": act_details_url,
    }


def extract_act_links(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    links: List[str] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if re.search(ACT_LINK_PATTERN, href):
            links.append(normalize_url(base_url, href))
    return sorted(set(links))


def extract_full_text_from_act_details(html: str) -> str:
    """Extract plain text of the full ordinance from act-details page.
    BDLaws structure: section.bg-striped contains div.txt-head + div.txt-details with ordinance content."""
    soup = BeautifulSoup(html, "lxml")
    for skip in soup.find_all(["script", "style", "nav", "header", "footer"]):
        skip.decompose()
    section = soup.find("section", class_="bg-striped")
    if section:
        parts = []
        for row in section.find_all("div", class_="row"):
            txt_details = row.find("div", class_="txt-details")
            if txt_details:
                parts.append(txt_details.get_text(separator="\n", strip=True))
            txt_head = row.find("div", class_="txt-head")
            if txt_head and txt_details is None:
                parts.append(txt_head.get_text(separator="\n", strip=True))
        if parts:
            return "\n\n".join(parts)
    all_txt = soup.find_all("div", class_="txt-details")
    if all_txt:
        return "\n\n".join(d.get_text(separator="\n", strip=True) for d in all_txt)
    main = soup.find("div", class_="act-details-content") or soup.find("main") or soup.find("body")
    if main:
        return main.get_text(separator="\n", strip=True)
    return soup.get_text(separator="\n", strip=True)


def extract_act_details_url(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """Extract full-act link, e.g. /act-details-1594.html"""
    link = soup.find("a", class_="view-full-law-button", href=True)
    if link and re.search(r"/act-details-\d+\.html", link["href"]):
        return normalize_url(base_url, link["href"])
    return None


def parse_chronological_index_entries(
    html: str,
    base_url: str,
    year_filter: Optional[List[int]] = None,
    ordinance_only: bool = False,
) -> List[Tuple[str, str]]:
    """
    Parse chronological index table: tr > td (x3) with anchors.
    First column = title, third = year.
    year_filter: e.g. [2024, 2025, 2026] for interim period.
    ordinance_only: keep only entries with অধ্যাদেশ or Ordinance in title.
    """
    soup = BeautifulSoup(html, "lxml")
    entries: List[Tuple[str, str]] = []
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        first_anchor = cells[0].find("a", href=True)
        if not first_anchor or not re.search(ACT_LINK_PATTERN, first_anchor["href"]):
            continue
        url = normalize_url(base_url, first_anchor["href"])
        title = first_anchor.get_text(" ", strip=True)
        if not title or _looks_like_law_number(title):
            continue
        if ordinance_only and "অধ্যাদেশ" not in title and "ordinance" not in title.lower():
            continue
        if year_filter:
            year_cell = cells[2].get_text(strip=True)
            year_str = normalize_bengali_digits(year_cell)
            try:
                year = int(year_str)
            except ValueError:
                continue
            if year not in year_filter:
                continue
        entries.append((url, title))
    return entries


def _is_detail_link(href: str) -> bool:
    href_lower = href.lower()
    return any(re.search(pattern, href_lower) for pattern in DETAIL_LINK_PATTERNS)


def _extract_title(soup: BeautifulSoup) -> str:
    # BDLaws ordinance pages: main title in section.bg-act-section > h3
    act_section = soup.find("section", class_="bg-act-section")
    if act_section:
        h3 = act_section.find("h3")
        if h3 and h3.get_text(strip=True):
            return h3.get_text(strip=True)
    for tag in ("h1", "h2", "h3"):
        heading = soup.find(tag)
        if heading and heading.get_text(strip=True):
            return heading.get_text(strip=True)
    title_tag = soup.find("title")
    if title_tag:
        return title_tag.get_text(strip=True)
    return "Unknown title"


def _extract_pdf_url(soup: BeautifulSoup) -> Optional[str]:
    # BDLaws: PDF in "গেজেটেড অনুলিপি" panel, inside td.act-up-files
    act_up = soup.find("td", class_="act-up-files")
    if act_up:
        link = act_up.find("a", href=True)
        if link and link["href"].lower().endswith(".pdf"):
            return link["href"]
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].lower()
        if href.endswith(".pdf"):
            return anchor["href"]
    return None


def _extract_labeled_fields(soup: BeautifulSoup) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    for row in soup.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) >= 2:
            key = cells[0].get_text(" ", strip=True).lower()
            value = cells[1].get_text(" ", strip=True)
            if key and value:
                fields[key] = value
    return fields


def _pick_document_type(
    labels: Dict[str, str], page_text: str, title: Optional[str]
) -> Optional[str]:
    candidates = [labels.get("type"), labels.get("category"), labels.get("law type")]
    for candidate in candidates:
        if candidate:
            return candidate
    lowered = page_text.lower()
    if "ordinance" in lowered or "অধ্যাদেশ" in page_text or "ordinance" in (title or "").lower():
        return "Ordinance"
    return None


def _pick_date(soup: BeautifulSoup, labels: Dict[str, str], page_text: str):
    # BDLaws: explicit publish-date div, e.g. [ ০১  জানুয়ারি, ২০২৬   ]
    publish_div = soup.find("div", class_="publish-date")
    if publish_div:
        raw = publish_div.get_text(strip=True)
        raw = re.sub(r"^\[|\]$", "", raw).strip()
        parsed = parse_date_from_text(raw)
        if parsed:
            return parsed
    date_keys = (
        "date of assent",
        "date of enactment",
        "enactment date",
        "date",
    )
    for key in date_keys:
        if key in labels:
            parsed = parse_date_from_text(labels[key])
            if parsed:
                return parsed
    bracketed = _extract_bracketed_date(page_text)
    if bracketed:
        parsed = parse_date_from_text(bracketed)
        if parsed:
            return parsed
    return None


def _extract_bracketed_date(text: str) -> Optional[str]:
    months = (
        "January|February|March|April|May|June|July|August|September|October|November|December|"
        "জানুয়ারি|ফেব্রুয়ারি|মার্চ|এপ্রিল|মে|জুন|জুলাই|আগস্ট|অগাস্ট|সেপ্টেম্বর|অক্টোবর|নভেম্বর|ডিসেম্বর"
    )
    pattern = rf"\[\s*([^\]]*({months})[^\]]*)\s*\]"
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None


def _looks_like_law_number(text: str) -> bool:
    if len(text) > 4:
        return False
    return is_numeric_text(text)
