"""
Raw grant record model for data source adapters
Represents unprocessed grant data from various government sources
"""
from typing import Optional

from pydantic import BaseModel


class RawGrantRecord(BaseModel):
    """Raw grant record from a data source adapter"""
    
    source: str
    source_record_id: Optional[str] = None
    issuer_raw: Optional[str] = None
    recipient_name: Optional[str] = None
    amount_raw: Optional[str] = None  # raw string before parsing
    amount_cad: Optional[float] = None
    award_date_raw: Optional[str] = None
    description: Optional[str] = None
    region_raw: Optional[str] = None
    program_name: Optional[str] = None
    raw_data: dict  # full original record
    fetch_errors: list[str] = []
