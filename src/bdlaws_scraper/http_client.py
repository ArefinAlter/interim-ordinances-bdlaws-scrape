from __future__ import annotations

import time
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import ScrapeConfig


def build_session(config: ScrapeConfig) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.8",
        }
    )
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def get_html(
    session: requests.Session,
    url: str,
    *,
    delay_seconds: float,
    timeout_seconds: int = 30,
) -> str:
    if delay_seconds > 0:
        time.sleep(delay_seconds)
    response = session.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    enc = response.encoding or response.apparent_encoding or "utf-8"
    if enc and "utf" not in enc.lower():
        enc = "utf-8"
    response.encoding = enc
    return response.text
