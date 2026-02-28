from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class OrdinanceRecord:
    title: str
    detail_url: str
    act_details_url: Optional[str]
    enactment_date: Optional[date]
    document_type: Optional[str]
    pdf_url: Optional[str]
    raw_source: str
    act_id: Optional[str]
    full_text_source: Optional[str]
    is_amendment: bool
    original_detail_url: Optional[str]
    original_title: Optional[str]
    original_raw_source: Optional[str]
    original_act_details_url: Optional[str]
    original_act_id: Optional[str]
    original_full_text_source: Optional[str]
    original_enactment_date: Optional[date]

    def to_dict(self) -> dict:
        data = asdict(self)
        if self.enactment_date is not None:
            data["enactment_date"] = self.enactment_date.isoformat()
        if self.original_enactment_date is not None:
            data["original_enactment_date"] = self.original_enactment_date.isoformat()
        return data
