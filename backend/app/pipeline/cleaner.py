"""
Data Cleaning Module for Pipeline
Contains quality rules, cleaning functions, and validation logic
"""
import logging
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List, Optional, Set, Tuple, Union, Any

import hashlib
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)

# Valid province codes
VALID_PROVINCES = ["AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT", "CA"]

# Province name to code mapping (for CSV files with full names)
PROVINCE_NAME_TO_CODE = {
    "Ontario": "ON",
    "Quebec": "QC",
    "British Columbia": "BC",
    "Alberta": "AB",
    "Manitoba": "MB",
    "New Brunswick": "NB",
    "Newfoundland & Labrador": "NL",
    "Newfoundland and Labrador": "NL",
    "Saskatchewan": "SK",
    "Nova Scotia": "NS",
    "Prince Edward Island": "PE",
    "Northwest Territories": "NT",
    "Nunavut": "NU",
    "Yukon": "YT",
    "Other": "CA",  # International recipients
}

# Recipient type mapping (for CSV files and Open Canada data)
RECIPIENT_TYPE_MAPPING = {
    # Individuals — hard-filtered by procurement signal scorer
    "Individual or sole proprietorship": "individual",
    # For-profit organisations
    "For-profit organization": "private_company",
    # Non-profits
    "Not-for-profit organization or charity": "nonprofit",
    # International
    "International (non-government)": "international",
    # Indigenous
    "Indigenous recipients": "indigenous",
    # Academic
    "Academia": "university",
    # Government entities
    "Municipal government": "municipal_government",
    "Provincial government": "provincial_government",
    "Federal government": "federal_government",
    # Specialised public bodies
    "Crown corporation": "crown_corporation",
    "Hospital or health authority": "hospital_health",
    "Port authority": "port_authority",
    # Fallbacks
    "Other": "unknown",
    "-": "unknown",
    "": "unknown",
    None: "unknown",
}

# Quality rules schema
QUALITY_RULES = {
    "recipient_name": {
        "required": True,
        "min_length": 3,
        "reject_values": ["unknown", "n/a", "na", "tbd", "none", "-"],
    },
    "recipient_type": {
        "required": False,
        "valid_values": ["business", "individual", "nonprofit", "government", "academic", "other"],
    },
    "issuer_canonical": {
        "required": True,
        "reject_values": ["unknown", "n/a", "na", "tbd", "none", "-"],
    },
    "amount_cad": {
        "required": False,
        "min": 0,
        "max": 500_000_000,  # Flag but don't reject amounts over 500M
    },
    "award_date": {
        "required": False,
        "min_year": 2000,
        "max_year": 2030,
    },
    "region": {
        "required": False,
        "valid_values": VALID_PROVINCES,
    },
    "description": {
        "required": False,
        "min_length": 20,
    },
    "program_name": {
        "required": False,
        "min_length": 3,
    },
    "description_quality": {
        "required": False,
        "valid_values": ["high", "medium", "low", "unknown"],
    }
}

# Department canonical mapping
DEPT_CANONICAL = {
    # Health
    "health canada": "Health Canada",
    "santé canada": "Health Canada",
    "hc": "Health Canada",
    
    # Innovation, Science and Economic Development
    "ised": "Innovation, Science and Economic Development Canada",
    "innovation science and economic development": "Innovation, Science and Economic Development Canada",
    "innovation science and economic development canada": "Innovation, Science and Economic Development Canada",
    "industry canada": "Innovation, Science and Economic Development Canada",
    
    # Infrastructure
    "infrastructure canada": "Infrastructure Canada",
    "infc": "Infrastructure Canada",
    
    # Treasury Board
    "treasury board": "Treasury Board of Canada Secretariat",
    "tbs": "Treasury Board of Canada Secretariat",
    "treasury board secretariat": "Treasury Board of Canada Secretariat",
    
    # National Research Council
    "national research council": "National Research Council Canada",
    "nrc": "National Research Council Canada",
    "cnrc": "National Research Council Canada",
    
    # Transport Canada
    "transport canada": "Transport Canada",
    "tc": "Transport Canada",
    "transports canada": "Transport Canada",
    
    # Environment and Climate Change
    "environment and climate change canada": "Environment and Climate Change Canada",
    "eccc": "Environment and Climate Change Canada",
    "environment canada": "Environment and Climate Change Canada",
    
    # National Defence
    "national defence": "Department of National Defence",
    "dnd": "Department of National Defence",
    "défense nationale": "Department of National Defence",
    "department of national defence": "Department of National Defence",
    
    # Public Safety
    "public safety canada": "Public Safety Canada",
    "sécurité publique": "Public Safety Canada",
    "sécurité publique canada": "Public Safety Canada",
    
    # Indigenous Services
    "indigenous services canada": "Indigenous Services Canada",
    "isc": "Indigenous Services Canada",
    "services aux autochtones": "Indigenous Services Canada",
    "services aux autochtones canada": "Indigenous Services Canada",
    
    # Natural Resources
    "natural resources canada": "Natural Resources Canada",
    "nrcan": "Natural Resources Canada",
    "ressources naturelles canada": "Natural Resources Canada",
    
    # Global Affairs
    "global affairs canada": "Global Affairs Canada",
    "gac": "Global Affairs Canada",
    "affaires mondiales": "Global Affairs Canada",
    "affaires mondiales canada": "Global Affairs Canada",
    
    # Agriculture
    "agriculture and agri-food canada": "Agriculture and Agri-Food Canada",
    "aafc": "Agriculture and Agri-Food Canada",
    "agriculture et agroalimentaire canada": "Agriculture and Agri-Food Canada",
    
    # Fisheries and Oceans
    "fisheries and oceans canada": "Fisheries and Oceans Canada",
    "dfo": "Fisheries and Oceans Canada",
    "pêches et océans": "Fisheries and Oceans Canada",
    "pêches et océans canada": "Fisheries and Oceans Canada",
    
    # Canada Revenue Agency
    "canada revenue agency": "Canada Revenue Agency",
    "cra": "Canada Revenue Agency",
    "arc": "Canada Revenue Agency",
    "agence du revenu du canada": "Canada Revenue Agency",
    
    # Canadian Heritage
    "canadian heritage": "Canadian Heritage",
    "patrimoine canadien": "Canadian Heritage",
    "pch": "Canadian Heritage",
    
    # Canadian Institutes of Health Research
    "canadian institutes of health research": "Canadian Institutes of Health Research",
    "cihr": "Canadian Institutes of Health Research",
    "instituts de recherche en santé du canada": "Canadian Institutes of Health Research",
    "irsc": "Canadian Institutes of Health Research",
    
    # Social Sciences and Humanities Research Council
    "social sciences and humanities research council of canada": "Social Sciences and Humanities Research Council of Canada",
    "sshrc": "Social Sciences and Humanities Research Council of Canada",
    "conseil de recherches en sciences humaines": "Social Sciences and Humanities Research Council of Canada",
    "crsh": "Social Sciences and Humanities Research Council of Canada",
    
    # Natural Sciences and Engineering Research Council
    "natural sciences and engineering research council of canada": "Natural Sciences and Engineering Research Council of Canada",
    "nserc": "Natural Sciences and Engineering Research Council of Canada",
    "conseil de recherches en sciences naturelles et en génie": "Natural Sciences and Engineering Research Council of Canada",
    "crsng": "Natural Sciences and Engineering Research Council of Canada",
    
    # Atlantic Canada Opportunities Agency
    "atlantic canada opportunities agency": "Atlantic Canada Opportunities Agency",
    "acoa": "Atlantic Canada Opportunities Agency",
    "agence de promotion économique du canada atlantique": "Atlantic Canada Opportunities Agency",
    "apeca": "Atlantic Canada Opportunities Agency",
    
    # Canada Economic Development for Quebec Regions
    "canada economic development for quebec regions": "Canada Economic Development for Quebec Regions",
    "ced": "Canada Economic Development for Quebec Regions",
    "développement économique canada pour les régions du québec": "Canada Economic Development for Quebec Regions",
    "déc": "Canada Economic Development for Quebec Regions",
    
    # Parks Canada
    "parks canada": "Parks Canada",
    "parcs canada": "Parks Canada",
    "pc": "Parks Canada",
    
    # Department of Housing, Infrastructure and Communities
    "department of housing, infrastructure and communities": "Department of Housing, Infrastructure and Communities",
    "housing infrastructure and communities": "Department of Housing, Infrastructure and Communities",
    "infrastructure and communities": "Department of Housing, Infrastructure and Communities",
    "infc": "Department of Housing, Infrastructure and Communities",
    
    # Department of Justice
    "department of justice canada": "Department of Justice Canada",
    "justice canada": "Department of Justice Canada",
    "ministère de la justice": "Department of Justice Canada",
    "doj": "Department of Justice Canada",
    
    # Employment and Social Development Canada
    "employment and social development canada": "Employment and Social Development Canada",
    "esdc": "Employment and Social Development Canada",
    "emploi et développement social canada": "Employment and Social Development Canada",
    "edsc": "Employment and Social Development Canada",
    
    # Canadian Nuclear Safety Commission
    "canadian nuclear safety commission": "Canadian Nuclear Safety Commission",
    "cnsc": "Canadian Nuclear Safety Commission",
    "commission canadienne de sûreté nucléaire": "Canadian Nuclear Safety Commission",
    "ccsn": "Canadian Nuclear Safety Commission",
    
    # Prairies Economic Development Canada
    "prairies economic development canada": "Prairies Economic Development Canada",
    "prairiescan": "Prairies Economic Development Canada",
    "développement économique canada pour les prairies": "Prairies Economic Development Canada",
    
    # Veterans Affairs Canada
    "veterans affairs canada": "Veterans Affairs Canada",
    "vac": "Veterans Affairs Canada",
    "anciens combattants canada": "Veterans Affairs Canada",
    "acc": "Veterans Affairs Canada",
    
    # Canada Water Agency
    "canada water agency": "Canada Water Agency",
    "cwa": "Canada Water Agency",
    "agence canadienne de l'eau": "Canada Water Agency",
    
    # Federal Economic Development Agency for Northern Ontario
    "federal economic development agency for northern ontario": "Federal Economic Development Agency for Northern Ontario",
    "fednor": "Federal Economic Development Agency for Northern Ontario",
    "agence fédérale de développement économique pour le nord de l'ontario": "Federal Economic Development Agency for Northern Ontario",
    
    # Crown-Indigenous Relations and Northern Affairs Canada
    "crown-indigenous relations and northern affairs canada": "Crown-Indigenous Relations and Northern Affairs Canada",
    "cirnac": "Crown-Indigenous Relations and Northern Affairs Canada",
    "relations couronne-autochtones et affaires du nord canada": "Crown-Indigenous Relations and Northern Affairs Canada",
    "rcaanc": "Crown-Indigenous Relations and Northern Affairs Canada",
    
    # Canadian Space Agency
    "canadian space agency": "Canadian Space Agency",
    "csa": "Canadian Space Agency",
    "agence spatiale canadienne": "Canadian Space Agency",
    "asc": "Canadian Space Agency",
    
    # Canadian Northern Economic Development Agency
    "canadian northern economic development agency": "Canadian Northern Economic Development Agency",
    "cannor": "Canadian Northern Economic Development Agency",
    "agence canadienne de développement économique du nord": "Canadian Northern Economic Development Agency",
    
    # Public Health Agency of Canada
    "public health agency of canada": "Public Health Agency of Canada",
    "phac": "Public Health Agency of Canada",
    "agence de la santé publique du canada": "Public Health Agency of Canada",
    "aspc": "Public Health Agency of Canada",
    
    # Royal Canadian Mounted Police
    "royal canadian mounted police": "Royal Canadian Mounted Police",
    "rcmp": "Royal Canadian Mounted Police",
    "gendarmerie royale du canada": "Royal Canadian Mounted Police",
    "grc": "Royal Canadian Mounted Police",
    
    # Correctional Service of Canada
    "correctional service of canada": "Correctional Service of Canada",
    "csc": "Correctional Service of Canada",
    "service correctionnel du canada": "Correctional Service of Canada",
    "scc": "Correctional Service of Canada",
    
    # Pacific Economic Development Canada
    "pacific economic development canada": "Pacific Economic Development Canada",
    "pacdevcan": "Pacific Economic Development Canada",
    "développement économique canada pour le pacifique": "Pacific Economic Development Canada",
    
    # Women and Gender Equality Canada
    "women and gender equality canada": "Women and Gender Equality Canada",
    "wage": "Women and Gender Equality Canada",
    "femmes et égalité des genres canada": "Women and Gender Equality Canada",
    "fegc": "Women and Gender Equality Canada",
    
    # Accessibility Standards Canada
    "accessibility standards canada": "Accessibility Standards Canada",
    "asc": "Accessibility Standards Canada",
    "normes d'accessibilité canada": "Accessibility Standards Canada",
    
    # Canada Energy Regulator
    "canada energy regulator": "Canada Energy Regulator",
    "cer": "Canada Energy Regulator",
    "régie de l'énergie du canada": "Canada Energy Regulator",
    
    # Federal Economic Development Agency for Southern Ontario
    "federal economic development agency for southern ontario": "Federal Economic Development Agency for Southern Ontario",
    "feddev": "Federal Economic Development Agency for Southern Ontario",
    "agence fédérale de développement économique pour le sud de l'ontario": "Federal Economic Development Agency for Southern Ontario",
    
    # Immigration, Refugees and Citizenship Canada
    "immigration, refugees and citizenship canada": "Immigration, Refugees and Citizenship Canada",
    "ircc": "Immigration, Refugees and Citizenship Canada",
    "immigration, réfugiés et citoyenneté canada": "Immigration, Refugees and Citizenship Canada",
    
    # Canadian Food Inspection Agency
    "canadian food inspection agency": "Canadian Food Inspection Agency",
    "cfia": "Canadian Food Inspection Agency",
    "agence canadienne d'inspection des aliments": "Canadian Food Inspection Agency",
    "acia": "Canadian Food Inspection Agency",
    
    # Department of Finance Canada
    "department of finance canada": "Department of Finance Canada",
    "finance canada": "Department of Finance Canada",
    "ministère des finances": "Department of Finance Canada",
    
    # Polar Knowledge Canada
    "polar knowledge canada": "Polar Knowledge Canada",
    "polar": "Polar Knowledge Canada",
    "savoir polaire canada": "Polar Knowledge Canada",
}

# French month translations
FRENCH_MONTHS = {
    "janvier": "january",
    "février": "february", 
    "mars": "march",
    "avril": "april",
    "mai": "may",
    "juin": "june",
    "juillet": "july",
    "août": "august",
    "septembre": "september",
    "octobre": "october",
    "novembre": "november",
    "décembre": "december"
}

# Flag categories
QUARANTINE_FLAGS = {
    "missing_recipient", 
    "missing_department",
    "date_parse_failed",
    "date_missing",
    "amount_parse_failed",
    "insufficient_data"
}

WARNING_FLAGS = {
    "amount_missing",
    "future_date",
    "unknown_department",
    "suspicious_amount_over_500M",
    "negative_amount",
    "zero_amount",
    "french_date_translated"
}


def clean_amount(amount_raw: Optional[str]) -> Tuple[Optional[float], List[str]]:
    """
    Clean and normalize amount values
    
    Args:
        amount_raw: Raw amount string
        
    Returns:
        Tuple of (cleaned_amount, flags)
    """
    flags = []
    
    # Handle None/empty values
    if amount_raw is None or (isinstance(amount_raw, str) and not amount_raw.strip()):
        return None, ["amount_missing"]
    
    # Convert to string if not already
    if not isinstance(amount_raw, str):
        try:
            # If it's already a number, just convert and return
            amount = float(amount_raw)
            if amount == 0:
                flags.append("zero_amount")
            elif amount < 0:
                flags.append("negative_amount")
            elif amount > 500_000_000:
                flags.append("suspicious_amount_over_500M")
            return amount, flags
        except (ValueError, TypeError):
            return None, ["amount_parse_failed", f"raw_value:{amount_raw}"]
    
    # Clean string - ensure it's a string before calling methods
    if not isinstance(amount_raw, str):
        return None, ["amount_parse_failed", f"not_a_string:{type(amount_raw).__name__}"]
    
    amount_str = amount_raw.strip().lower()
    
    # Check for n/a values
    na_values = ["n/a", "na", "tbd", "none", "-", "not available", "not applicable"]
    if amount_str in na_values:
        return None, ["amount_not_available"]
    
    # Remove currency symbols and commas
    amount_str = amount_str.replace("$", "").replace(",", "")
    
    # Handle French number format (spaces between digits)
    amount_str = re.sub(r'(\d)\s(\d)', r'\1\2', amount_str)
    
    # Handle accounting negative format (500,000) -> -500000
    if amount_str.startswith("(") and amount_str.endswith(")"):
        amount_str = "-" + amount_str[1:-1]
        flags.append("negative_amount")
    
    # Handle K/M suffixes
    if amount_str.endswith("k") or amount_str.endswith("K"):
        try:
            amount = float(amount_str[:-1]) * 1_000
            return amount, flags
        except (ValueError, TypeError):
            return None, ["amount_parse_failed", f"raw_value:{amount_raw}"]
    
    if amount_str.endswith("m") or amount_str.endswith("M"):
        try:
            amount = float(amount_str[:-1]) * 1_000_000
            return amount, flags
        except (ValueError, TypeError):
            return None, ["amount_parse_failed", f"raw_value:{amount_raw}"]
    
    # Try to parse as float
    try:
        amount = float(amount_str)
        
        # Apply validation rules
        if amount == 0:
            flags.append("zero_amount")
        elif amount < 0:
            flags.append("negative_amount")
        elif amount > 500_000_000:
            flags.append("suspicious_amount_over_500M")
        
        return amount, flags
    except (ValueError, TypeError):
        return None, ["amount_parse_failed", f"raw_value:{amount_raw}"]


def clean_date(date_raw: Optional[str]) -> Tuple[Optional[date], List[str]]:
    """
    Clean and normalize date values
    Handles ISO 8601 dates, null placeholders, and various formats
    
    Args:
        date_raw: Raw date string
        
    Returns:
        Tuple of (cleaned_date, flags)
    """
    flags = []
    
    # Handle None/empty values
    if date_raw is None or (isinstance(date_raw, str) and not date_raw.strip()):
        return None, ["date_missing"]
    
    # Check for null placeholders (CSV format)
    if isinstance(date_raw, str):
        date_str = date_raw.strip()
        
        # Check for CSV null placeholder
        if date_str == "0001-01-01T00:00:00Z":
            flags.append("amendment_date_null_placeholder")
            return None, flags
        
        # Ensure date_str is a string before calling .lower()
        if not isinstance(date_str, str):
            return None, ["date_parse_failed", f"not_a_string:{type(date_str).__name__}"]
        
        date_str_lower = date_str.lower()
        na_values = ["n/a", "na", "tbd", "none", "-", "0000-00-00", "null", "not available"]
        if date_str_lower in na_values:
            return None, ["date_not_available"]
        
        # Handle ISO 8601 format (strip timezone if present)
        # Format: "2026-01-01T00:00:00Z" or "2026-01-01"
        if "T" in date_str:
            # ISO 8601 with time - extract date part
            date_str = date_str.split("T")[0]
            flags.append("iso_date_stripped")
        
        # Check for French month names and translate if found
        translated = False
        for french, english in FRENCH_MONTHS.items():
            if french in date_str_lower:
                date_str = date_str.replace(french, english)
                translated = True
        
        if translated:
            flags.append("french_date_translated")
    else:
        date_str = date_raw
    
    # Try to parse the date
    try:
        from dateutil import parser
        parsed_date = parser.parse(date_str, fuzzy=True).date()
        
        # Validate date
        today = date.today()
        
        if parsed_date.year < 2000:
            return None, ["date_before_2000"]
        elif parsed_date.year > 2030:
            return None, ["date_after_2030"]
        elif parsed_date > today:
            flags.append("future_date")
            
        return parsed_date, flags
    except Exception:
        return None, ["date_parse_failed", f"raw_value:{date_raw}"]


def extract_fiscal_year(d: date) -> str:
    """
    Extract Canadian fiscal year from date
    Canadian fiscal year runs from April 1 to March 31
    
    Args:
        d: Date object
        
    Returns:
        Fiscal year string in format "YYYY-YY"
    """
    if d.month >= 4:  # April or later
        start_year = d.year
    else:  # January to March
        start_year = d.year - 1
        
    end_year = start_year + 1
    end_year_short = end_year % 100  # Get last two digits
    
    return f"{start_year}-{end_year_short:02d}"


def canonicalize_department(dept_raw: Optional[str]) -> Tuple[str, str, List[str]]:
    """
    Canonicalize department name using two-pass system:
    1. Exact match against DEPT_CANONICAL dict
    2. Fuzzy match using rapidfuzz
    
    Args:
        dept_raw: Raw department name
        
    Returns:
        Tuple of (canonical_name, match_type, flags)
    """
    flags = []
    
    if not dept_raw or dept_raw is None or not isinstance(dept_raw, str):
        return "Unknown", "unmatched", ["missing_department"]
    
    # Normalize input
    dept_norm = dept_raw.lower().strip()
    dept_norm = re.sub(r'\s+', ' ', dept_norm)
    
    # Pass 1: Exact match
    if dept_norm in DEPT_CANONICAL:
        return DEPT_CANONICAL[dept_norm], "exact", flags
    
    # Pass 2: Fuzzy match
    if dept_norm:
        fuzzy_result = process.extractOne(
            dept_norm, 
            list(DEPT_CANONICAL.keys()), 
            scorer=fuzz.partial_ratio,
            score_cutoff=85
        )
        if fuzzy_result:
            match, score, _ = fuzzy_result
            return DEPT_CANONICAL[match], "fuzzy", flags
    
    # Fallback: Keep raw value
    return dept_raw, "unmatched", ["unknown_department"]


def normalize_recipient(recipient_raw: Optional[str]) -> Tuple[str, str]:
    """
    Normalize recipient name
    
    Args:
        recipient_raw: Raw recipient name
        
    Returns:
        Tuple of (display_name, normalized_name)
    """
    if not recipient_raw or recipient_raw is None or not isinstance(recipient_raw, str):
        return "Unknown", "unknown"
    
    # Basic cleaning for display name
    display_name = recipient_raw.strip()
    display_name = re.sub(r'\s+', ' ', display_name)
    
    # Deep normalization for matching
    # Unicode normalization
    normalized = unicodedata.normalize('NFKD', display_name)
    normalized = ''.join(c for c in normalized if not unicodedata.combining(c))
    
    # Lowercase
    normalized = normalized.lower()
    
    # Remove legal suffixes (longer ones first to avoid partial matches)
    legal_suffixes = [
        " incorporated", " inc.", " inc", 
        " limited", " ltd.", " ltd", 
        " llc", " l.l.c.", 
        " corporation", " corp.", " corp", 
        " company", " co.", " co", 
        " ltée", " ltee", 
        " s.e.n.c", " enr", 
        " s.a.", " sa",
        " lp", " llp"
    ]
    
    for suffix in legal_suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
            break
    
    # Remove special characters except hyphens and apostrophes
    normalized = re.sub(r'[^\w\s\'-]', '', normalized)
    
    # Collapse multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return display_name, normalized


def map_province_name_to_code(province_name: Optional[str]) -> Optional[str]:
    """
    Map full province name to province code (for CSV files)
    
    Args:
        province_name: Full province name (e.g., "Ontario", "British Columbia")
        
    Returns:
        Province code (e.g., "ON", "BC") or None
    """
    if not province_name:
        return None
    
    # Direct lookup
    if province_name in PROVINCE_NAME_TO_CODE:
        return PROVINCE_NAME_TO_CODE[province_name]
    
    # Case-insensitive lookup
    province_lower = province_name.strip()
    for name, code in PROVINCE_NAME_TO_CODE.items():
        if name.lower() == province_lower.lower():
            return code
    
    # If already a code, return as-is
    if province_name.upper() in VALID_PROVINCES:
        return province_name.upper()
    
    return None


def map_recipient_type(recipient_type_raw: Optional[str]) -> str:
    """
    Map CSV recipient type to normalized recipient type
    
    Args:
        recipient_type_raw: Raw recipient type from CSV
        
    Returns:
        Normalized recipient type
    """
    if not recipient_type_raw or recipient_type_raw is None:
        return "unknown"
    
    # Ensure it's a string before calling strip()
    if not isinstance(recipient_type_raw, str):
        return "unknown"
    
    recipient_type_clean = recipient_type_raw.strip()
    
    # If empty after stripping, return unknown
    if not recipient_type_clean:
        return "unknown"
    
    # Direct lookup
    if recipient_type_clean in RECIPIENT_TYPE_MAPPING:
        return RECIPIENT_TYPE_MAPPING[recipient_type_clean]
    
    # Case-insensitive lookup
    recipient_type_lower = recipient_type_clean.lower()
    for key, value in RECIPIENT_TYPE_MAPPING.items():
        # Skip None keys
        if key is None or not isinstance(key, str):
            continue
        if key.lower() == recipient_type_lower:
            return value
    
    return "unknown"


def should_quarantine(flags: List[str]) -> Tuple[bool, str]:
    """
    Determine if a record should be quarantined based on its flags
    Note: amendment_date_null_placeholder is NOT a quarantine reason
    
    Args:
        flags: List of quality flags
        
    Returns:
        Tuple of (quarantine: bool, reason: str)
    """
    # Filter out non-quarantine flags
    quarantine_flags = [f for f in flags if f in QUARANTINE_FLAGS]
    
    # Count critical flags
    critical_count = len(quarantine_flags)
    
    # Check for 2+ critical flags
    if critical_count >= 2:
        return True, f"Multiple critical quality issues ({critical_count} critical flags)"
    
    # Check for specific combinations
    if "missing_recipient" in flags and "date_missing" in flags:
        return True, "Missing both recipient and date"
    
    # Not quarantined
    return False, ""


class CleaningReport:
    """Report on data cleaning results"""
    
    def __init__(self, source: str):
        self.source = source
        self.total_raw = 0
        self.total_clean = 0
        self.total_quarantined = 0
        self.total_duplicates = 0
        self.flag_counts = defaultdict(int)
        self.dept_match_types = defaultdict(int)
        
    def add_flags(self, flags: List[str]) -> None:
        """Add flags to the report"""
        for flag in flags:
            self.flag_counts[flag] += 1
    
    def add_dept_match(self, match_type: str) -> None:
        """Add department match type to the report"""
        self.dept_match_types[match_type] += 1
    
    def print_summary(self) -> None:
        """Print a formatted summary of the cleaning report"""
        retention_rate = (self.total_clean / self.total_raw * 100) if self.total_raw > 0 else 0
        
        print(f"\nCleaning Report for {self.source}")
        print(f"{'=' * 40}")
        print(f"Total Raw Records:     {self.total_raw}")
        print(f"Total Clean Records:   {self.total_clean}")
        print(f"Total Quarantined:     {self.total_quarantined}")
        print(f"Total Duplicates:      {self.total_duplicates}")
        print(f"Retention Rate:        {retention_rate:.1f}%")
        print(f"\nTop 5 Quality Issues:")
        
        # Sort flags by count descending
        sorted_flags = sorted(self.flag_counts.items(), key=lambda x: x[1], reverse=True)
        for flag, count in sorted_flags[:5]:
            pct = (count / self.total_raw * 100) if self.total_raw > 0 else 0
            print(f"  {flag}: {count} ({pct:.1f}%)")
        
        print(f"\nDepartment Matching:")
        for match_type, count in self.dept_match_types.items():
            pct = (count / self.total_raw * 100) if self.total_raw > 0 else 0
            print(f"  {match_type}: {count} ({pct:.1f}%)")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for database storage"""
        return {
            "source": self.source,
            "total_raw": self.total_raw,
            "total_clean": self.total_clean,
            "total_quarantined": self.total_quarantined,
            "total_duplicates": self.total_duplicates,
            "retention_rate": (self.total_clean / self.total_raw * 100) if self.total_raw > 0 else 0,
            "flag_counts": dict(self.flag_counts),
            "dept_match_types": dict(self.dept_match_types)
        }