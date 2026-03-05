"""
RFP Prediction Engine
Predicts specific RFP types that will likely emerge from government grants.

Core insight: When government awards a grant, that money gets spent through
procurement (RFPs, RFQs, RFIs). The type, value, and timing of those RFPs
is predictable based on the grant's theme, department, amount, and keywords.

This is 100% rule-based (no LLM needed) — fast, deterministic, and transparent.
"""
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RFPPrediction:
    """A single predicted RFP opportunity from a grant"""
    rfp_type: str                      # e.g. "Penetration Testing Services"
    timeline_months_min: int           # months from grant award
    timeline_months_max: int           # months from grant award
    likelihood: str                    # "high", "medium", "low"
    target_bidders: list[str]          # types of companies that should bid
    reasoning: str                     # why we predict this
    predicted_rfp_date_start: Optional[str] = None  # ISO date
    predicted_rfp_date_end: Optional[str] = None    # ISO date
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GrantRFPForecast:
    """Complete RFP forecast for a single grant"""
    grant_id: str
    total_predicted_rfps: int
    predictions: list[RFPPrediction]
    forecast_confidence: str           # "high", "medium", "low"
    forecast_summary: str              # human-readable summary
    
    def to_dict(self) -> dict:
        return {
            "grant_id": self.grant_id,
            "total_predicted_rfps": self.total_predicted_rfps,
            "forecast_confidence": self.forecast_confidence,
            "forecast_summary": self.forecast_summary,
            "predictions": [p.to_dict() for p in self.predictions],
        }


# ═══════════════════════════════════════════════════════════════════════════
# RFP PREDICTION TAXONOMY
# Maps (grant_theme) → list of RFP types that typically follow
# Each RFP type has: value as % of grant, timeline, likelihood, target bidders
# ═══════════════════════════════════════════════════════════════════════════

RFP_TAXONOMY = {
    "Cybersecurity Modernization": [
        {
            "name": "Penetration Testing & Vulnerability Assessment",
            "value_pct_min": 0.05, "value_pct_max": 0.15,
            "lag_months_min": 3, "lag_months_max": 6,
            "likelihood": "high",
            "target_bidders": ["Cybersecurity firms", "IT security consultants"],
            "keywords_boost": ["vulnerability", "assessment", "testing", "audit", "penetration"],
        },
        {
            "name": "Security Architecture & Design Services",
            "value_pct_min": 0.10, "value_pct_max": 0.25,
            "lag_months_min": 4, "lag_months_max": 9,
            "likelihood": "high",
            "target_bidders": ["IT security architects", "Systems integrators"],
            "keywords_boost": ["architecture", "design", "framework", "modernization", "zero trust"],
        },
        {
            "name": "Managed Security Operations (SOC/SIEM)",
            "value_pct_min": 0.15, "value_pct_max": 0.35,
            "lag_months_min": 6, "lag_months_max": 12,
            "likelihood": "medium",
            "target_bidders": ["Managed security service providers", "Large IT firms"],
            "keywords_boost": ["operations", "monitoring", "soc", "siem", "managed", "24/7"],
        },
        {
            "name": "Security Training & Awareness Programs",
            "value_pct_min": 0.03, "value_pct_max": 0.08,
            "lag_months_min": 2, "lag_months_max": 6,
            "likelihood": "medium",
            "target_bidders": ["Training providers", "Cybersecurity consultants"],
            "keywords_boost": ["training", "awareness", "education", "phishing"],
        },
        {
            "name": "Incident Response & Recovery Planning",
            "value_pct_min": 0.05, "value_pct_max": 0.12,
            "lag_months_min": 3, "lag_months_max": 8,
            "likelihood": "medium",
            "target_bidders": ["Cybersecurity firms", "Risk management consultants"],
            "keywords_boost": ["incident", "response", "recovery", "resilience", "continuity"],
        },
    ],
    
    "Digital Transformation": [
        {
            "name": "Custom Software Development",
            "value_pct_min": 0.20, "value_pct_max": 0.40,
            "lag_months_min": 3, "lag_months_max": 6,
            "likelihood": "high",
            "target_bidders": ["Software development firms", "IT consulting firms", "Digital agencies"],
            "keywords_boost": ["software", "application", "platform", "portal", "digital", "development"],
        },
        {
            "name": "Cloud Migration & Infrastructure",
            "value_pct_min": 0.10, "value_pct_max": 0.30,
            "lag_months_min": 3, "lag_months_max": 8,
            "likelihood": "high",
            "target_bidders": ["Cloud consulting firms", "Systems integrators", "AWS/Azure partners"],
            "keywords_boost": ["cloud", "migration", "aws", "azure", "infrastructure", "saas"],
        },
        {
            "name": "UX/UI Design & User Research",
            "value_pct_min": 0.05, "value_pct_max": 0.15,
            "lag_months_min": 2, "lag_months_max": 5,
            "likelihood": "medium",
            "target_bidders": ["Design agencies", "UX consulting firms"],
            "keywords_boost": ["user", "design", "experience", "interface", "accessibility", "usability"],
        },
        {
            "name": "Data Analytics & Business Intelligence",
            "value_pct_min": 0.08, "value_pct_max": 0.20,
            "lag_months_min": 4, "lag_months_max": 9,
            "likelihood": "medium",
            "target_bidders": ["Data analytics firms", "BI consultants"],
            "keywords_boost": ["data", "analytics", "intelligence", "dashboard", "reporting", "visualization"],
        },
        {
            "name": "IT Project Management & Advisory",
            "value_pct_min": 0.05, "value_pct_max": 0.12,
            "lag_months_min": 2, "lag_months_max": 6,
            "likelihood": "high",
            "target_bidders": ["Management consulting firms", "IT advisory firms"],
            "keywords_boost": ["management", "advisory", "governance", "strategy", "roadmap"],
        },
    ],
    
    "AI & Machine Learning": [
        {
            "name": "AI/ML Model Development & Training",
            "value_pct_min": 0.20, "value_pct_max": 0.40,
            "lag_months_min": 3, "lag_months_max": 8,
            "likelihood": "high",
            "target_bidders": ["AI/ML consulting firms", "Data science companies", "Tech companies"],
            "keywords_boost": ["model", "training", "algorithm", "neural", "deep learning", "prediction"],
        },
        {
            "name": "Data Engineering & Pipeline Development",
            "value_pct_min": 0.10, "value_pct_max": 0.25,
            "lag_months_min": 2, "lag_months_max": 6,
            "likelihood": "high",
            "target_bidders": ["Data engineering firms", "Cloud data partners"],
            "keywords_boost": ["data", "pipeline", "etl", "warehouse", "lake", "ingestion"],
        },
        {
            "name": "AI Ethics & Governance Consulting",
            "value_pct_min": 0.03, "value_pct_max": 0.10,
            "lag_months_min": 2, "lag_months_max": 6,
            "likelihood": "medium",
            "target_bidders": ["AI ethics consultants", "Policy advisory firms"],
            "keywords_boost": ["ethics", "governance", "responsible", "bias", "fairness", "transparency"],
        },
        {
            "name": "MLOps & AI Infrastructure",
            "value_pct_min": 0.08, "value_pct_max": 0.20,
            "lag_months_min": 4, "lag_months_max": 10,
            "likelihood": "medium",
            "target_bidders": ["DevOps/MLOps firms", "Cloud infrastructure providers"],
            "keywords_boost": ["mlops", "deployment", "infrastructure", "scaling", "production"],
        },
    ],
    
    "Healthcare Digitization": [
        {
            "name": "Electronic Health Records (EHR) Implementation",
            "value_pct_min": 0.20, "value_pct_max": 0.40,
            "lag_months_min": 6, "lag_months_max": 12,
            "likelihood": "high",
            "target_bidders": ["Health IT vendors", "EHR system providers", "Systems integrators"],
            "keywords_boost": ["ehr", "electronic health", "patient record", "health information", "interoperability"],
        },
        {
            "name": "Telehealth & Virtual Care Platforms",
            "value_pct_min": 0.10, "value_pct_max": 0.25,
            "lag_months_min": 4, "lag_months_max": 9,
            "likelihood": "medium",
            "target_bidders": ["Telehealth platform providers", "Health tech startups"],
            "keywords_boost": ["telehealth", "virtual care", "remote", "telemedicine", "video"],
        },
        {
            "name": "Health Data Analytics & Population Health",
            "value_pct_min": 0.08, "value_pct_max": 0.20,
            "lag_months_min": 4, "lag_months_max": 10,
            "likelihood": "medium",
            "target_bidders": ["Health analytics firms", "Data science companies"],
            "keywords_boost": ["analytics", "population health", "surveillance", "outcomes", "epidemiology"],
        },
        {
            "name": "Medical Device & Equipment Procurement",
            "value_pct_min": 0.15, "value_pct_max": 0.35,
            "lag_months_min": 6, "lag_months_max": 14,
            "likelihood": "medium",
            "target_bidders": ["Medical device companies", "Biotech firms", "Lab equipment suppliers"],
            "keywords_boost": ["device", "equipment", "laboratory", "diagnostic", "imaging"],
        },
        {
            "name": "Clinical Research & Trial Management",
            "value_pct_min": 0.10, "value_pct_max": 0.25,
            "lag_months_min": 3, "lag_months_max": 9,
            "likelihood": "medium",
            "target_bidders": ["CROs", "Clinical research consultants", "Pharmaceutical services"],
            "keywords_boost": ["clinical", "trial", "research", "study", "pharmaceutical", "drug"],
        },
    ],
    
    "Clean Energy Infrastructure": [
        {
            "name": "Engineering & Environmental Consulting",
            "value_pct_min": 0.10, "value_pct_max": 0.20,
            "lag_months_min": 6, "lag_months_max": 12,
            "likelihood": "high",
            "target_bidders": ["Engineering firms", "Environmental consultants"],
            "keywords_boost": ["engineering", "design", "environmental", "assessment", "feasibility"],
        },
        {
            "name": "Construction & Installation Services",
            "value_pct_min": 0.30, "value_pct_max": 0.60,
            "lag_months_min": 9, "lag_months_max": 18,
            "likelihood": "high",
            "target_bidders": ["Construction firms", "Renewable energy installers", "General contractors"],
            "keywords_boost": ["construction", "installation", "building", "site", "commissioning"],
        },
        {
            "name": "Energy Auditing & Performance Monitoring",
            "value_pct_min": 0.03, "value_pct_max": 0.10,
            "lag_months_min": 4, "lag_months_max": 10,
            "likelihood": "medium",
            "target_bidders": ["Energy auditors", "Sustainability consultants"],
            "keywords_boost": ["audit", "performance", "monitoring", "efficiency", "baseline"],
        },
        {
            "name": "Equipment & Technology Procurement",
            "value_pct_min": 0.15, "value_pct_max": 0.35,
            "lag_months_min": 8, "lag_months_max": 16,
            "likelihood": "medium",
            "target_bidders": ["Clean energy equipment suppliers", "Solar/wind manufacturers"],
            "keywords_boost": ["equipment", "solar", "wind", "battery", "turbine", "panel", "ev"],
        },
        {
            "name": "Project Management & Oversight",
            "value_pct_min": 0.05, "value_pct_max": 0.12,
            "lag_months_min": 6, "lag_months_max": 12,
            "likelihood": "high",
            "target_bidders": ["Project management firms", "Construction management consultants"],
            "keywords_boost": ["project management", "oversight", "coordination", "scheduling"],
        },
    ],
    
    "Municipal Modernization": [
        {
            "name": "Cloud & SaaS Platform Procurement",
            "value_pct_min": 0.15, "value_pct_max": 0.35,
            "lag_months_min": 4, "lag_months_max": 10,
            "likelihood": "high",
            "target_bidders": ["SaaS providers", "Cloud solution providers", "GovTech companies"],
            "keywords_boost": ["cloud", "saas", "platform", "digital", "online", "portal"],
        },
        {
            "name": "Broadband & Connectivity Infrastructure",
            "value_pct_min": 0.25, "value_pct_max": 0.50,
            "lag_months_min": 6, "lag_months_max": 14,
            "likelihood": "medium",
            "target_bidders": ["Telecom companies", "ISPs", "Network infrastructure firms"],
            "keywords_boost": ["broadband", "internet", "connectivity", "fiber", "network", "rural"],
        },
        {
            "name": "Smart City Technology Integration",
            "value_pct_min": 0.10, "value_pct_max": 0.30,
            "lag_months_min": 4, "lag_months_max": 12,
            "likelihood": "medium",
            "target_bidders": ["IoT providers", "Smart city technology firms", "Systems integrators"],
            "keywords_boost": ["smart", "iot", "sensor", "automation", "intelligent"],
        },
        {
            "name": "Municipal IT Consulting & Strategy",
            "value_pct_min": 0.05, "value_pct_max": 0.15,
            "lag_months_min": 3, "lag_months_max": 8,
            "likelihood": "high",
            "target_bidders": ["IT consulting firms", "Management consultants", "GovTech advisors"],
            "keywords_boost": ["strategy", "consulting", "advisory", "assessment", "roadmap", "plan"],
        },
        {
            "name": "Community Infrastructure Development",
            "value_pct_min": 0.20, "value_pct_max": 0.45,
            "lag_months_min": 6, "lag_months_max": 16,
            "likelihood": "medium",
            "target_bidders": ["Construction firms", "Engineering firms", "Architecture firms"],
            "keywords_boost": ["infrastructure", "facility", "building", "community", "recreation", "housing"],
        },
    ],
    
    "Workforce Development": [
        {
            "name": "Training Program Design & Delivery",
            "value_pct_min": 0.20, "value_pct_max": 0.40,
            "lag_months_min": 3, "lag_months_max": 8,
            "likelihood": "high",
            "target_bidders": ["Training providers", "E-learning companies", "HR consultants"],
            "keywords_boost": ["training", "program", "curriculum", "delivery", "learning"],
        },
        {
            "name": "HR & Workforce Management Systems",
            "value_pct_min": 0.10, "value_pct_max": 0.25,
            "lag_months_min": 4, "lag_months_max": 10,
            "likelihood": "medium",
            "target_bidders": ["HR tech vendors", "HRIS providers", "Workforce management platforms"],
            "keywords_boost": ["system", "platform", "management", "tracking", "hr"],
        },
        {
            "name": "Labour Market Research & Analysis",
            "value_pct_min": 0.05, "value_pct_max": 0.15,
            "lag_months_min": 2, "lag_months_max": 6,
            "likelihood": "medium",
            "target_bidders": ["Research firms", "Economic consultants", "Policy analysts"],
            "keywords_boost": ["research", "analysis", "study", "labour market", "survey", "evaluation"],
        },
        {
            "name": "Program Evaluation & Impact Assessment",
            "value_pct_min": 0.05, "value_pct_max": 0.12,
            "lag_months_min": 6, "lag_months_max": 14,
            "likelihood": "medium",
            "target_bidders": ["Evaluation consultants", "Research firms", "Policy advisory"],
            "keywords_boost": ["evaluation", "impact", "assessment", "outcomes", "measurement"],
        },
    ],
    
    "Research & Innovation": [
        {
            "name": "Research Equipment & Lab Supplies",
            "value_pct_min": 0.15, "value_pct_max": 0.35,
            "lag_months_min": 3, "lag_months_max": 8,
            "likelihood": "high",
            "target_bidders": ["Scientific equipment suppliers", "Lab supply companies"],
            "keywords_boost": ["equipment", "laboratory", "instrument", "supplies", "facility"],
        },
        {
            "name": "Specialized Research Consulting",
            "value_pct_min": 0.10, "value_pct_max": 0.25,
            "lag_months_min": 3, "lag_months_max": 9,
            "likelihood": "medium",
            "target_bidders": ["Research consultants", "Subject matter experts", "Advisory firms"],
            "keywords_boost": ["consulting", "expert", "advisory", "review", "analysis"],
        },
        {
            "name": "Technology Commercialization Services",
            "value_pct_min": 0.05, "value_pct_max": 0.15,
            "lag_months_min": 6, "lag_months_max": 14,
            "likelihood": "medium",
            "target_bidders": ["Tech transfer offices", "Commercialization consultants", "IP lawyers"],
            "keywords_boost": ["commercialization", "technology transfer", "patent", "licensing", "market"],
        },
        {
            "name": "Prototype Development & Testing",
            "value_pct_min": 0.10, "value_pct_max": 0.30,
            "lag_months_min": 4, "lag_months_max": 10,
            "likelihood": "medium",
            "target_bidders": ["Engineering firms", "Product development companies", "Testing labs"],
            "keywords_boost": ["prototype", "testing", "development", "pilot", "proof of concept"],
        },
    ],
    
    "Transportation & Logistics": [
        {
            "name": "Transportation Engineering & Design",
            "value_pct_min": 0.10, "value_pct_max": 0.20,
            "lag_months_min": 6, "lag_months_max": 12,
            "likelihood": "high",
            "target_bidders": ["Civil engineering firms", "Transportation planners", "Design firms"],
            "keywords_boost": ["engineering", "design", "planning", "study", "feasibility"],
        },
        {
            "name": "Infrastructure Construction & Rehabilitation",
            "value_pct_min": 0.35, "value_pct_max": 0.60,
            "lag_months_min": 9, "lag_months_max": 18,
            "likelihood": "high",
            "target_bidders": ["Construction companies", "Infrastructure contractors", "Heavy civil firms"],
            "keywords_boost": ["construction", "rehabilitation", "upgrade", "expansion", "repair"],
        },
        {
            "name": "Fleet & Equipment Procurement",
            "value_pct_min": 0.15, "value_pct_max": 0.30,
            "lag_months_min": 6, "lag_months_max": 14,
            "likelihood": "medium",
            "target_bidders": ["Vehicle manufacturers", "Fleet management companies", "Equipment dealers"],
            "keywords_boost": ["fleet", "vehicle", "bus", "train", "equipment", "rolling stock"],
        },
        {
            "name": "Transportation Technology & ITS",
            "value_pct_min": 0.05, "value_pct_max": 0.15,
            "lag_months_min": 4, "lag_months_max": 10,
            "likelihood": "medium",
            "target_bidders": ["ITS providers", "Traffic management firms", "Transportation tech"],
            "keywords_boost": ["technology", "its", "signal", "traffic", "intelligent", "system"],
        },
        {
            "name": "Supply Chain & Logistics Consulting",
            "value_pct_min": 0.05, "value_pct_max": 0.12,
            "lag_months_min": 3, "lag_months_max": 8,
            "likelihood": "medium",
            "target_bidders": ["Supply chain consultants", "Logistics firms", "Management consultants"],
            "keywords_boost": ["supply chain", "logistics", "distribution", "freight", "shipping"],
        },
    ],
    
    "Environmental & Climate": [
        {
            "name": "Environmental Impact Assessment (EIA)",
            "value_pct_min": 0.08, "value_pct_max": 0.18,
            "lag_months_min": 3, "lag_months_max": 9,
            "likelihood": "high",
            "target_bidders": ["Environmental consultants", "EIA specialists", "Engineering firms"],
            "keywords_boost": ["assessment", "impact", "environmental", "review", "study"],
        },
        {
            "name": "Remediation & Cleanup Services",
            "value_pct_min": 0.20, "value_pct_max": 0.45,
            "lag_months_min": 6, "lag_months_max": 14,
            "likelihood": "medium",
            "target_bidders": ["Environmental remediation firms", "Waste management companies"],
            "keywords_boost": ["remediation", "cleanup", "contamination", "waste", "pollution", "soil"],
        },
        {
            "name": "Climate Monitoring & Reporting Systems",
            "value_pct_min": 0.05, "value_pct_max": 0.15,
            "lag_months_min": 4, "lag_months_max": 10,
            "likelihood": "medium",
            "target_bidders": ["Environmental tech firms", "Data/monitoring companies", "GIS specialists"],
            "keywords_boost": ["monitoring", "reporting", "ghg", "emissions", "tracking", "measurement"],
        },
        {
            "name": "Conservation & Biodiversity Consulting",
            "value_pct_min": 0.10, "value_pct_max": 0.25,
            "lag_months_min": 4, "lag_months_max": 12,
            "likelihood": "medium",
            "target_bidders": ["Ecology consultants", "Conservation specialists", "Wildlife experts"],
            "keywords_boost": ["conservation", "biodiversity", "species", "habitat", "wildlife", "ecosystem"],
        },
        {
            "name": "Water Treatment & Infrastructure",
            "value_pct_min": 0.20, "value_pct_max": 0.40,
            "lag_months_min": 6, "lag_months_max": 16,
            "likelihood": "medium",
            "target_bidders": ["Water engineering firms", "Treatment system providers", "Municipal contractors"],
            "keywords_boost": ["water", "treatment", "wastewater", "drinking", "infrastructure", "plant"],
        },
    ],
    
    "Indigenous Programs": [
        {
            "name": "Community Infrastructure & Housing",
            "value_pct_min": 0.25, "value_pct_max": 0.50,
            "lag_months_min": 6, "lag_months_max": 14,
            "likelihood": "high",
            "target_bidders": ["Construction firms", "Indigenous-owned contractors", "Engineering firms"],
            "keywords_boost": ["housing", "infrastructure", "building", "construction", "facility", "water"],
        },
        {
            "name": "Program Management & Consulting",
            "value_pct_min": 0.08, "value_pct_max": 0.20,
            "lag_months_min": 3, "lag_months_max": 9,
            "likelihood": "high",
            "target_bidders": ["Indigenous consulting firms", "Management consultants", "Social consultants"],
            "keywords_boost": ["management", "consulting", "advisory", "support", "capacity"],
        },
        {
            "name": "Health & Social Services Delivery",
            "value_pct_min": 0.10, "value_pct_max": 0.25,
            "lag_months_min": 3, "lag_months_max": 10,
            "likelihood": "medium",
            "target_bidders": ["Health service providers", "Social service organizations", "Mental health providers"],
            "keywords_boost": ["health", "mental", "social", "wellness", "addiction", "support"],
        },
        {
            "name": "Education & Training Services",
            "value_pct_min": 0.10, "value_pct_max": 0.20,
            "lag_months_min": 3, "lag_months_max": 8,
            "likelihood": "medium",
            "target_bidders": ["Education providers", "Training organizations", "Curriculum developers"],
            "keywords_boost": ["education", "training", "school", "youth", "learning", "language"],
        },
    ],
    
    "Defence & Security": [
        {
            "name": "Defence Systems & Technology",
            "value_pct_min": 0.20, "value_pct_max": 0.40,
            "lag_months_min": 6, "lag_months_max": 12,
            "likelihood": "high",
            "target_bidders": ["Defence contractors", "Military technology firms", "Systems integrators"],
            "keywords_boost": ["system", "technology", "platform", "capability", "equipment", "weapon"],
        },
        {
            "name": "IT & Communications Security",
            "value_pct_min": 0.10, "value_pct_max": 0.25,
            "lag_months_min": 4, "lag_months_max": 9,
            "likelihood": "high",
            "target_bidders": ["IT security firms", "Communications companies", "Defence IT"],
            "keywords_boost": ["it", "communications", "network", "cyber", "secure", "classified"],
        },
        {
            "name": "Professional & Management Consulting",
            "value_pct_min": 0.05, "value_pct_max": 0.15,
            "lag_months_min": 3, "lag_months_max": 8,
            "likelihood": "high",
            "target_bidders": ["Management consultants", "Strategy firms", "Defence advisory"],
            "keywords_boost": ["consulting", "advisory", "management", "strategy", "review", "assessment"],
        },
        {
            "name": "Training & Simulation Services",
            "value_pct_min": 0.08, "value_pct_max": 0.18,
            "lag_months_min": 4, "lag_months_max": 10,
            "likelihood": "medium",
            "target_bidders": ["Training companies", "Simulation providers", "Defence training firms"],
            "keywords_boost": ["training", "simulation", "exercise", "readiness", "personnel"],
        },
        {
            "name": "Facilities & Base Infrastructure",
            "value_pct_min": 0.15, "value_pct_max": 0.30,
            "lag_months_min": 6, "lag_months_max": 16,
            "likelihood": "medium",
            "target_bidders": ["Construction firms", "Facility management companies", "Engineering firms"],
            "keywords_boost": ["facility", "base", "infrastructure", "construction", "maintenance"],
        },
    ],
}

# ═══════════════════════════════════════════════════════════════════════════
# DEPARTMENT-SPECIFIC ADJUSTMENTS
# Some departments have stronger procurement patterns than others
# ═══════════════════════════════════════════════════════════════════════════

DEPARTMENT_PROCUREMENT_BOOST = {
    # High procurement departments — more likely to generate RFPs
    "shared services canada": 1.3,
    "public services and procurement canada": 1.3,
    "national defence": 1.2,
    "treasury board": 1.2,
    "transport canada": 1.2,
    "infrastructure canada": 1.2,
    "innovation, science and economic development": 1.15,
    "health canada": 1.1,
    "natural resources canada": 1.1,
    "environment and climate change canada": 1.1,
    
    # Lower procurement departments — more internal or transfer-based
    "canadian heritage": 0.8,
    "women and gender equality": 0.7,
    "social sciences and humanities research council": 0.6,
    "natural sciences and engineering research council": 0.6,
    "canada council for the arts": 0.5,
}

# Minimum grant amount to generate RFP predictions
MIN_GRANT_AMOUNT_FOR_PREDICTIONS = 25_000


def _format_currency(amount: float) -> str:
    """Format currency for display"""
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"${amount / 1_000:.0f}K"
    else:
        return f"${amount:,.0f}"


def _add_months_to_date(base_date: date, months: int) -> date:
    """Add months to a date"""
    year = base_date.year
    month = base_date.month + months
    while month > 12:
        year += 1
        month -= 12
    try:
        return date(year, month, min(base_date.day, 28))
    except ValueError:
        return date(year, month, 28)


def predict_rfps(
    grant_id: str,
    funding_theme: Optional[str],
    amount_cad: Optional[float],
    award_date: Optional[date],
    description: Optional[str] = None,
    issuer_canonical: Optional[str] = None,
    business_relevance: Optional[str] = None,
    business_relevance_score: Optional[float] = None,
) -> GrantRFPForecast:
    """
    Predict specific RFP opportunities that will likely emerge from a grant.
    
    Args:
        grant_id: Grant record ID
        funding_theme: Classified funding theme (e.g., "Cybersecurity Modernization")
        amount_cad: Grant amount in CAD
        award_date: Grant award date
        description: Grant description (for keyword boosting)
        issuer_canonical: Department name (for department-specific adjustments)
        business_relevance: Business relevance category
        business_relevance_score: Business relevance score (0-1)
    
    Returns:
        GrantRFPForecast with list of predicted RFP opportunities
    """
    
    # No predictions for unknown themes or irrelevant grants
    if not funding_theme or funding_theme not in RFP_TAXONOMY:
        return GrantRFPForecast(
            grant_id=grant_id,
            total_predicted_rfps=0,
            predictions=[],
            forecast_confidence="low",
            forecast_summary="Insufficient data for RFP prediction. Grant theme not classified.",
        )
    
    # Skip low-relevance grants
    if business_relevance == "low":
        return GrantRFPForecast(
            grant_id=grant_id,
            total_predicted_rfps=0,
            predictions=[],
            forecast_confidence="low",
            forecast_summary="Low business relevance — unlikely to generate procurement opportunities.",
        )
    
    # Use default amount if unknown (for filtering purposes only)
    effective_amount = amount_cad or 100_000
    
    # Skip very small grants
    if effective_amount < MIN_GRANT_AMOUNT_FOR_PREDICTIONS:
        return GrantRFPForecast(
            grant_id=grant_id,
            total_predicted_rfps=0,
            predictions=[],
            forecast_confidence="low",
            forecast_summary="Grant amount too small to likely generate RFPs.",
        )
    
    # Get base predictions from taxonomy
    rfp_templates = RFP_TAXONOMY[funding_theme]
    
    # Calculate department boost
    dept_boost = 1.0
    if issuer_canonical:
        issuer_lower = issuer_canonical.lower()
        for dept_key, boost in DEPARTMENT_PROCUREMENT_BOOST.items():
            if dept_key in issuer_lower:
                dept_boost = boost
                break
    
    # Build description text for keyword matching
    desc_lower = (description or "").lower()
    
    # Generate predictions
    predictions: list[RFPPrediction] = []
    
    for template in rfp_templates:
        # Calculate keyword match score — boost likelihood if keywords match description
        keyword_matches = 0
        if desc_lower:
            for kw in template["keywords_boost"]:
                if kw in desc_lower:
                    keyword_matches += 1
        
        # Determine effective likelihood
        base_likelihood = template["likelihood"]
        if keyword_matches >= 2:
            # Boost likelihood if multiple keywords match
            if base_likelihood == "medium":
                base_likelihood = "high"
            elif base_likelihood == "low":
                base_likelihood = "medium"
        
        # Calculate predicted dates
        predicted_start = None
        predicted_end = None
        if award_date:
            predicted_start = _add_months_to_date(award_date, template["lag_months_min"]).isoformat()
            predicted_end = _add_months_to_date(award_date, template["lag_months_max"]).isoformat()
        
        # Build reasoning
        reasoning_parts = [
            f"Based on {funding_theme} grants from {issuer_canonical or 'government'}"
        ]
        if keyword_matches > 0:
            matched_kws = [kw for kw in template["keywords_boost"] if kw in desc_lower]
            reasoning_parts.append(f"Keywords matched: {', '.join(matched_kws[:3])}")
        if dept_boost > 1.0:
            reasoning_parts.append(f"Department ({issuer_canonical}) has strong procurement history")
        
        prediction = RFPPrediction(
            rfp_type=template["name"],
            timeline_months_min=template["lag_months_min"],
            timeline_months_max=template["lag_months_max"],
            likelihood=base_likelihood,
            target_bidders=template["target_bidders"],
            reasoning=". ".join(reasoning_parts),
            predicted_rfp_date_start=predicted_start,
            predicted_rfp_date_end=predicted_end,
        )
        
        predictions.append(prediction)
    
    # Sort by likelihood (high first)
    likelihood_order = {"high": 0, "medium": 1, "low": 2}
    predictions.sort(key=lambda p: likelihood_order.get(p.likelihood, 3))
    
    # Count high likelihood predictions
    high_count = sum(1 for p in predictions if p.likelihood == "high")
    
    # Determine overall forecast confidence
    if high_count >= 2 and effective_amount >= 500_000:
        forecast_confidence = "high"
    elif high_count >= 1 and effective_amount >= 100_000:
        forecast_confidence = "medium"
    else:
        forecast_confidence = "low"
    
    # Generate summary (without money values)
    summary = (
        f"This {funding_theme.lower()} grant "
        f"from {issuer_canonical or 'government'} is expected to generate "
        f"{len(predictions)} procurement opportunity{'ies' if len(predictions) != 1 else 'y'} "
        f"over the next {predictions[0].timeline_months_min if predictions else 3}-"
        f"{predictions[-1].timeline_months_max if predictions else 12} months."
    )
    
    return GrantRFPForecast(
        grant_id=grant_id,
        total_predicted_rfps=len(predictions),
        predictions=predictions,
        forecast_confidence=forecast_confidence,
        forecast_summary=summary,
    )


def predict_rfps_for_signal(
    signal_name: str,
    funding_theme: str,
    total_funding_cad: float,
    grant_count: int,
    department_cluster: Optional[str] = None,
) -> dict:
    """
    Generate aggregated RFP predictions for a procurement signal
    (a cluster of related grants).
    
    Returns a dict with aggregated predictions suitable for display.
    """
    if funding_theme not in RFP_TAXONOMY:
        return {
            "signal_name": signal_name,
            "aggregated_rfps": [],
            "summary": "No RFP predictions available for this signal theme.",
        }
    
    rfp_templates = RFP_TAXONOMY[funding_theme]
    
    aggregated = []
    for template in rfp_templates:
        # For signals, we estimate the number of individual RFPs
        estimated_count_min = max(1, int(grant_count * 0.3)) if template["likelihood"] == "high" else max(1, int(grant_count * 0.15))
        estimated_count_max = max(1, int(grant_count * 0.6)) if template["likelihood"] == "high" else max(1, int(grant_count * 0.3))
        
        aggregated.append({
            "rfp_type": template["name"],
            "estimated_rfp_count_min": estimated_count_min,
            "estimated_rfp_count_max": estimated_count_max,
            "timeline_months_min": template["lag_months_min"],
            "timeline_months_max": template["lag_months_max"],
            "likelihood": template["likelihood"],
            "target_bidders": template["target_bidders"],
        })
    
    summary = (
        f"This cluster of {grant_count} {funding_theme.lower()} grants "
        f"is expected to generate "
        f"{sum(a['estimated_rfp_count_min'] for a in aggregated)}-"
        f"{sum(a['estimated_rfp_count_max'] for a in aggregated)} RFPs "
        f"over the next {aggregated[0]['timeline_months_min'] if aggregated else 3}-"
        f"{aggregated[-1]['timeline_months_max'] if aggregated else 12} months."
    )
    
    return {
        "signal_name": signal_name,
        "aggregated_rfps": aggregated,
        "summary": summary,
    }
