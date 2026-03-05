"""
Data source adapters for fetching raw government grant data
"""
from app.adapters.innovation_canada import InnovationCanadaAdapter
from app.adapters.open_canada import OpenCanadaAdapter
from app.adapters.proactive_disclosure import ProactiveDisclosureAdapter
from app.adapters.mock_grants import MockGrantsAdapter
from app.adapters.csv_file import CSVFileAdapter

__all__ = [
    "OpenCanadaAdapter",
    "InnovationCanadaAdapter",
    "ProactiveDisclosureAdapter",
    "MockGrantsAdapter",
    "CSVFileAdapter",
]
