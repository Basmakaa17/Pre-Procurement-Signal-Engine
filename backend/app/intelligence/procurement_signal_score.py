"""
Procurement Signal Score
Predicts likelihood of a grant generating RFPs before expensive LLM classification.

Based on six key dimensions:
1. Money Flow Direction (Agreement Type)
2. Recipient Capacity Gap (Recipient Type)
3. What The Money Is For (Description / Program keywords)
4. NAICS Code (if available)
5. Grant Duration (end_date − start_date)
6. Amount Thresholds

Scoring:
  >= 60  → HIGH   — Will almost certainly generate public RFP(s)
  40-59  → MEDIUM — Likely generates at least one procurement action
  20-39  → LOW    — Possible informal / sole-source procurement
  < 20   → NOISE  — Transfer payment, no procurement signal
"""
import logging
from typing import Tuple, List, Optional
from datetime import date

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# DIMENSION 1 — Money Flow Direction (Agreement Type)
# ═══════════════════════════════════════════════════════════════════════════
# "Contribution" → government expects the recipient to DO something → may subcontract
# "Grant"        → government gives with fewer strings → less likely to procure
# "Other transfer payment" → pure financial benefit → never generates RFP

AGREEMENT_TYPE_SCORES = {
    "contribution": 30,
    "grant": 10,
    "other transfer payment": -100,   # Hard filter — instant noise
}


# ═══════════════════════════════════════════════════════════════════════════
# DIMENSION 2 — Recipient Capacity Gap
# ═══════════════════════════════════════════════════════════════════════════
# The key question: does the recipient have the internal staff to do the work?

RECIPIENT_TYPE_SCORES = {
    # HIGH CAPACITY GAP — will hire vendors
    "municipal_government": 35,
    "municipality": 35,
    "crown_corporation": 35,
    "port_authority": 35,
    "hospital_health": 35,
    "hospital": 35,
    "provincial_government": 35,
    "federal_government": 35,

    # MEDIUM CAPACITY GAP — for-profit receiving contribution (IRAP-style)
    "private_company": 25,

    # LOW CAPACITY GAP — may do work internally
    "university": 5,
    "nonprofit": 0,
    "indigenous": 0,

    # ZERO CAPACITY GAP — they ARE the service
    "individual": -100,       # Hard filter
    "international": -50,

    "unknown": 0,
}

# Name-based recipient type inference patterns
_MUNICIPALITY_PATTERNS = [
    "city of", "municipality", "town of", "village of", "district of",
    "regional district", "county of", "township of", "région de", "ville de",
]
_HOSPITAL_PATTERNS = [
    "hospital", "health authority", "health region", "hôpital",
    "centre hospitalier",
]
_UNIVERSITY_PATTERNS = [
    "university", "college", "université", "école", "polytechnique",
    "institute of technology",
]
_INDIVIDUAL_PATTERNS = ["mr.", "ms.", "mrs.", "dr.", "professor"]
_ORG_INDICATORS = [
    "inc", "ltd", "llc", "corporation", "association", "foundation",
    "society", "group", "company", "co.", "corp", "authority",
]


# ═══════════════════════════════════════════════════════════════════════════
# DIMENSION 3 — What The Money Is Actually For (Keywords)
# ═══════════════════════════════════════════════════════════════════════════

POSITIVE_KEYWORDS = {
    # Construction & Physical Infrastructure
    "construction": 20,
    "capital improvement": 20,
    "capital improvements": 20,
    "terminal": 20,
    "facility": 15,
    # Digital & Modernization
    "modernization": 18,
    "digital": 18,
    "platform": 18,
    "system": 15,
    "software": 18,
    # Technology & Innovation
    "technology": 12,
    "innovation": 12,
    "r&d": 12,
    # Infrastructure & Equipment
    "expansion": 15,
    "infrastructure": 15,
    "equipment": 15,
}

NEGATIVE_KEYWORDS = {
    # Hard-filter keywords (instant noise)
    "scholarship": -100,
    "fellowship": -100,
    "assessed contribution": -100,
    "membership fee": -100,
    # Program / service delivery — soft negatives
    "program delivery": -15,
    "service delivery": -15,
    "cultural": -15,
    "training": -10,
    "capacity building": -10,
    # Academic & research
    "research": -20,
    "study": -20,
    # Other transfer payments
    "arts": -15,
    "language": -15,
    "heritage": -15,
    "youth employment": -15,
    "crime prevention": -15,
}


# ═══════════════════════════════════════════════════════════════════════════
# DIMENSION 4 — NAICS Code (when available)
# ═══════════════════════════════════════════════════════════════════════════

NAICS_SCORES = {
    "237": 20,     # Heavy and Civil Engineering Construction
    "5415": 18,    # Computer Systems Design
    "541": 15,     # Professional, Scientific and Technical Services
    "711": -20,    # Performing Arts, Spectator Sports
    "611": -10,    # Educational Services
}


# ═══════════════════════════════════════════════════════════════════════════
# DIMENSION 5 — Grant Duration
# ═══════════════════════════════════════════════════════════════════════════
# Short grants (< 6 mo) → likely sole-source, not public RFP
# Long grants (> 12 mo) → enough time for proper procurement cycles

DURATION_SCORES = {
    "short": -20,    # < 6 months
    "medium": 0,     # 6-12 months
    "long": 15,      # > 12 months
}


# ═══════════════════════════════════════════════════════════════════════════
# DIMENSION 6 — Amount Thresholds
# ═══════════════════════════════════════════════════════════════════════════

AMOUNT_THRESHOLDS = [
    (5_000_000, 25),   # ≥$5M
    (1_000_000, 20),   # ≥$1M
    (250_000, 10),     # ≥$250K
    (50_000, 5),       # ≥$50K
    (0, -20),          # <$50K — too small for public RFP
]


# ═══════════════════════════════════════════════════════════════════════════
# MAIN SCORING FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def _infer_recipient_type(recipient_name: str) -> Optional[str]:
    """
    Infer recipient type from the recipient name when no explicit type is available.
    Returns a key from RECIPIENT_TYPE_SCORES or None.
    """
    name_lower = recipient_name.lower()

    if any(p in name_lower for p in _MUNICIPALITY_PATTERNS):
        return "municipal_government"
    if any(p in name_lower for p in _HOSPITAL_PATTERNS):
        return "hospital_health"
    if any(p in name_lower for p in _UNIVERSITY_PATTERNS):
        return "university"
    # Individual check: explicit title or no org indicator
    if any(p in name_lower for p in _INDIVIDUAL_PATTERNS):
        return "individual"
    # If none of the org indicators are present and name is short, likely individual
    if not any(ind in name_lower for ind in _ORG_INDICATORS) and len(name_lower) < 40:
        # Only flag as individual if very short (likely a person's name)
        if len(name_lower.split()) <= 3 and not any(c.isdigit() for c in name_lower):
            return "individual"

    return None


def calculate_procurement_signal_score(
    agreement_type: Optional[str] = None,
    recipient_name: Optional[str] = None,
    recipient_type: Optional[str] = None,
    amount_cad: Optional[float] = None,
    program_name: Optional[str] = None,
    description: Optional[str] = None,
    naics_code: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Tuple[int, List[str], str, Optional[int]]:
    """
    Calculate procurement signal score using the 6-dimension model.

    Returns:
        (score, reasons, signal_category, duration_months)
        signal_category: "high" (>=60), "medium" (40-59), "low" (20-39), "noise" (<20)
    """
    score = 0
    reasons: List[str] = []
    duration_months: Optional[int] = None

    # ── Dimension 5: Grant Duration ──────────────────────────────────────
    if start_date and end_date and end_date > start_date:
        duration_months = (
            (end_date.year - start_date.year) * 12
            + end_date.month - start_date.month
        )
        if duration_months < 6:
            score += DURATION_SCORES["short"]
            reasons.append(f"duration:short:{DURATION_SCORES['short']}")
        elif duration_months <= 12:
            score += DURATION_SCORES["medium"]
            reasons.append(f"duration:medium:{DURATION_SCORES['medium']}")
        else:
            score += DURATION_SCORES["long"]
            reasons.append(f"duration:long:{DURATION_SCORES['long']}")

    # ── Dimension 1: Agreement Type ──────────────────────────────────────
    if agreement_type:
        at_lower = agreement_type.strip().lower()
        for key, value in AGREEMENT_TYPE_SCORES.items():
            if key in at_lower:
                score += value
                reasons.append(f"agreement_type:{key}:{value}")
                if value <= -100:
                    return 0, [f"hard_filter:agreement_type:{key}"], "noise", duration_months
                break

    # ── Dimension 2: Recipient Capacity Gap ──────────────────────────────
    effective_type = recipient_type
    if (not effective_type or effective_type == "unknown") and recipient_name:
        inferred = _infer_recipient_type(recipient_name)
        if inferred:
            effective_type = inferred

    if effective_type and effective_type in RECIPIENT_TYPE_SCORES:
        val = RECIPIENT_TYPE_SCORES[effective_type]
        score += val
        reasons.append(f"recipient_type:{effective_type}:{val}")
        if val <= -100:
            return 0, [f"hard_filter:recipient_type:{effective_type}"], "noise", duration_months

    # ── Dimension 3: Keywords ────────────────────────────────────────────
    search_text = " ".join(
        filter(None, [(program_name or "").lower(), (description or "").lower()])
    )

    # Hard-filter keywords first
    for keyword, val in NEGATIVE_KEYWORDS.items():
        if val <= -100 and keyword in search_text:
            return 0, [f"hard_filter:keyword:{keyword}"], "noise", duration_months

    # Positive keywords (accumulate all matches)
    pos_matches: List[str] = []
    for keyword, val in POSITIVE_KEYWORDS.items():
        if keyword in search_text:
            score += val
            pos_matches.append(f"{keyword}:{val}")
    if pos_matches:
        reasons.append(f"keywords_pos:{','.join(pos_matches)}")

    # Negative keywords (soft)
    neg_matches: List[str] = []
    for keyword, val in NEGATIVE_KEYWORDS.items():
        if val > -100 and keyword in search_text:
            score += val
            neg_matches.append(f"{keyword}:{val}")
    if neg_matches:
        reasons.append(f"keywords_neg:{','.join(neg_matches)}")

    # ── Dimension 4: NAICS Code ──────────────────────────────────────────
    if naics_code and str(naics_code).strip() not in ("-", ""):
        naics_str = str(naics_code).strip()
        for prefix, val in NAICS_SCORES.items():
            if naics_str.startswith(prefix):
                score += val
                reasons.append(f"naics:{prefix}:{val}")
                break

    # ── Dimension 6: Amount ──────────────────────────────────────────────
    if amount_cad is not None:
        for threshold, val in AMOUNT_THRESHOLDS:
            if amount_cad >= threshold:
                score += val
                reasons.append(f"amount:>={threshold}:{val}")
                break

    # ── Final score clamping & categorisation ────────────────────────────
    score = max(0, min(100, score))

    if score >= 60:
        category = "high"
    elif score >= 40:
        category = "medium"
    elif score >= 20:
        category = "low"
    else:
        category = "noise"

    return score, reasons, category, duration_months
