import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict


DEFAULT_CONFIG_PATH = Path("config/config.json")


@dataclass(frozen=True)
class ScrapeConfig:
    base_url: str
    index_url: str
    chronological_index_url: str
    use_chronological_index: bool
    volume_urls: list[str]
    start_date: date
    end_date: date
    output_dir: Path
    raw_dir: Path
    full_text_dir: Path
    user_agent: str
    request_delay_seconds: float
    max_pages: int

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ScrapeConfig":
        start_date = _parse_date(data["start_date"])
        end_date = _parse_date(data["end_date"])
        volume_urls = data.get("volume_urls") or [data["index_url"]]
        chrono_url = data.get("chronological_index_url") or data["index_url"]
        use_chrono = data.get("use_chronological_index", False)
        return ScrapeConfig(
            base_url=data["base_url"].rstrip("/"),
            index_url=data["index_url"],
            chronological_index_url=chrono_url,
            use_chronological_index=use_chrono,
            volume_urls=volume_urls,
            start_date=start_date,
            end_date=end_date,
            output_dir=Path(data["output_dir"]),
            raw_dir=Path(data["raw_dir"]),
            full_text_dir=Path(data.get("full_text_dir", "data/full_text")),
            user_agent=data["user_agent"],
            request_delay_seconds=float(data["request_delay_seconds"]),
            max_pages=int(data["max_pages"]),
        )


def load_config(path: Path | None = None) -> ScrapeConfig:
    config_path = path or DEFAULT_CONFIG_PATH
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    return ScrapeConfig.from_dict(raw)


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()
