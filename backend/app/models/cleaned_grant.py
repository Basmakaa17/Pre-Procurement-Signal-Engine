"""
Cleaned grant record model
Represents a grant record after cleaning/normalization but before LLM classification
"""
from datetime import date
from typing import Optional

from pydantic import BaseModel


class CleanedGrantRecord(BaseModel):
    """Cleaned grant record ready for LLM classification"""
    
    id: str  # UUID from database
    source: str
    issuer_canonical: str
    recipient_name: str
    amount_cad: Optional[float] = None
    award_date: Optional[date] = None
    region: Optional[str] = None
    description: Optional[str] = None
