"""
Business Relevance Filter
Determines if a grant is likely to lead to future business opportunities/RFPs
Filters out irrelevant grants like scholarships and individual benefits
"""
import re
import logging
from typing import Tuple, List, Dict, Set, Optional, Union, Any

logger = logging.getLogger(__name__)

# Keywords that indicate a grant is NOT business-relevant
NON_BUSINESS_KEYWORDS = {
    # Education/Individual focused
    "scholarship": 0.9,
    "scholarships": 0.9,
    "tuition": 0.9,
    "student grant": 0.9,
    "fellowship": 0.9,
    "bursary": 0.9,
    "bursaries": 0.9,
    "educational grant": 0.8,
    "academic grant": 0.8,
    "phd": 0.7,
    "masters degree": 0.7,
    "postdoctoral": 0.8,
    "doctoral": 0.7,
    "thesis": 0.8,
    "dissertation": 0.8,
    
    # Individual benefits
    "income support": 0.8,
    "income assistance": 0.8,
    "disability benefit": 0.8,
    "personal benefit": 0.8,
    "individual support": 0.7,
    "living allowance": 0.8,
    "housing benefit": 0.7,
    "personal subsidy": 0.8,
    "child benefit": 0.9,
    "pension": 0.7,
    
    # Small cultural/arts grants
    "artist grant": 0.7,
    "artistic project": 0.6,
    "cultural exchange": 0.6,
    "cultural event": 0.6,
    "festival funding": 0.6,
    "performance grant": 0.6,
    "exhibition grant": 0.6,
}

# Keywords that indicate a grant IS business-relevant
BUSINESS_KEYWORDS = {
    # Infrastructure & Development
    "infrastructure": 0.8,
    "development project": 0.7,
    "construction": 0.8,
    "building": 0.6,
    "facility": 0.7,
    "renovation": 0.7,
    "expansion": 0.7,
    "modernization": 0.8,
    "upgrade": 0.7,
    
    # Technology
    "technology": 0.7,
    "software": 0.8,
    "hardware": 0.8,
    "digital": 0.7,
    "cybersecurity": 0.9,
    "network": 0.7,
    "system implementation": 0.9,
    "it infrastructure": 0.9,
    "data center": 0.8,
    "cloud": 0.7,
    
    # Consulting
    "consulting": 0.9,
    "professional services": 0.9,
    "advisory": 0.8,
    "assessment": 0.7,
    "evaluation": 0.6,
    "analysis": 0.6,
    "strategy development": 0.8,
    "implementation plan": 0.8,
    
    # Research with commercial applications
    "applied research": 0.7,
    "commercialization": 0.9,
    "market development": 0.8,
    "product development": 0.9,
    "technology transfer": 0.8,
    "innovation": 0.7,
    "prototype": 0.8,
    "pilot project": 0.8,
    
    # Business development
    "business development": 0.9,
    "economic development": 0.8,
    "industry development": 0.9,
    "sector development": 0.8,
    "supply chain": 0.8,
    "procurement": 0.9,
    "contract": 0.8,
}

# Recipient types that indicate business relevance
BUSINESS_RECIPIENT_TYPES = {
    "private_company": 0.9,
    "municipal_government": 0.8,
    "provincial_government": 0.8,
    "federal_government": 0.7,
    "nonprofit": 0.6,
    "university": 0.5,
    "hospital_health": 0.7,
    "indigenous": 0.7,
    "unknown": 0.5,
}

# Amount thresholds - larger grants are more likely to lead to RFPs
AMOUNT_THRESHOLDS = [
    (1000000, 0.9),  # >$1M: very likely
    (500000, 0.8),   # >$500K: likely
    (250000, 0.7),   # >$250K: somewhat likely
    (100000, 0.6),   # >$100K: possible
    (50000, 0.5),    # >$50K: neutral
]

def calculate_business_relevance(
    description: Optional[str], 
    amount_cad: Optional[float], 
    recipient_type: Optional[str] = None,
    funding_theme: Optional[str] = None,
    issuer_canonical: Optional[str] = None,
) -> Tuple[str, float, List[str]]:
    """
    Calculate business relevance score and category
    
    Args:
        description: Grant description text
        amount_cad: Grant amount in CAD
        recipient_type: Type of recipient (private_company, nonprofit, etc.)
        funding_theme: Classified funding theme
        issuer_canonical: Canonical department name
        
    Returns:
        Tuple of (relevance_category, relevance_score, match_reasons)
        Categories: 'high', 'medium', 'low', 'unknown'
    """
    score = 0.5  # Start neutral
    matches = []
    
    # Normalize text for matching
    desc_lower = (description or "").lower()
    
    # Check for non-business keywords
    for keyword, penalty in NON_BUSINESS_KEYWORDS.items():
        if keyword in desc_lower:
            score -= penalty * 0.2  # Apply penalty with dampening
            matches.append(f"non_business:{keyword}")
    
    # Check for business keywords
    for keyword, bonus in BUSINESS_KEYWORDS.items():
        if keyword in desc_lower:
            score += bonus * 0.2  # Apply bonus with dampening
            matches.append(f"business:{keyword}")
    
    # Check recipient type
    if recipient_type and recipient_type in BUSINESS_RECIPIENT_TYPES:
        recipient_score = BUSINESS_RECIPIENT_TYPES[recipient_type]
        score += recipient_score * 0.1  # Smaller weight for recipient type
        matches.append(f"recipient:{recipient_type}")
    
    # Check amount
    if amount_cad:
        for threshold, amount_score in AMOUNT_THRESHOLDS:
            if amount_cad >= threshold:
                score += amount_score * 0.1  # Smaller weight for amount
                matches.append(f"amount:{threshold}")
                break
    
    # Apply funding theme bonuses
    theme_bonuses = {
        "Cybersecurity Modernization": 0.15,
        "Digital Transformation": 0.15,
        "AI & Machine Learning": 0.15,
        "Healthcare Digitization": 0.10,
        "Clean Energy Infrastructure": 0.15,
        "Municipal Modernization": 0.15,
        "Transportation & Logistics": 0.15,
        "Environmental & Climate": 0.10,
        "Defence & Security": 0.15,
        "Research & Innovation": 0.05,  # Lower because some research is academic
        "Workforce Development": 0.05,  # Lower because some workforce dev is individual
        "Indigenous Programs": 0.05,    # Lower because some indigenous programs are individual
    }
    
    if funding_theme and funding_theme in theme_bonuses:
        score += theme_bonuses[funding_theme]
        matches.append(f"theme:{funding_theme}")
    
    # Department bonuses - some departments are more likely to lead to business opportunities
    dept_bonuses = {
        "Shared Services Canada": 0.15,
        "Public Services and Procurement Canada": 0.15,
        "Treasury Board of Canada Secretariat": 0.15,
        "Innovation, Science and Economic Development Canada": 0.15,
        "Transport Canada": 0.15,
        "Infrastructure Canada": 0.15,
        "National Defence": 0.15,
        "Public Safety Canada": 0.15,
        "Natural Resources Canada": 0.10,
        "Environment and Climate Change Canada": 0.10,
        "Health Canada": 0.10,
    }
    
    if issuer_canonical and issuer_canonical in dept_bonuses:
        score += dept_bonuses[issuer_canonical]
        matches.append(f"dept:{issuer_canonical}")
    
    # Clamp score to 0-1 range
    score = max(0.0, min(1.0, score))
    
    # Determine category
    if score >= 0.7:
        category = "high"
    elif score >= 0.4:
        category = "medium"
    elif score > 0:
        category = "low"
    else:
        category = "unknown"
    
    return (category, score, matches)


def filter_by_relevance(grants: List[Dict[str, Any]], min_relevance: str = "low") -> List[Dict[str, Any]]:
    """
    Filter grants by business relevance
    
    Args:
        grants: List of grant dictionaries
        min_relevance: Minimum relevance category ("high", "medium", "low", or "all")
        
    Returns:
        Filtered list of grants
    """
    if min_relevance == "all":
        return grants
    
    relevance_levels = {
        "high": 3,
        "medium": 2,
        "low": 1,
        "unknown": 0
    }
    
    min_level = relevance_levels.get(min_relevance, 0)
    
    filtered = []
    for grant in grants:
        relevance = grant.get("business_relevance", "unknown")
        if relevance_levels.get(relevance, 0) >= min_level:
            filtered.append(grant)
    
    return filtered