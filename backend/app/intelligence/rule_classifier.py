"""
Rule-Based Hybrid Classifier
1. Tries keyword/department matching first (instant, no API needed)
2. Falls back to LLM only for unmatched records
3. Auto-learns: new LLM classifications get saved as keyword rules for next time
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.intelligence.classifier import ClassificationResult, GrantClassifier
from app.models.cleaned_grant import CleanedGrantRecord

logger = logging.getLogger(__name__)

# Path to the learned keywords file (persists across runs)
LEARNED_KEYWORDS_PATH = Path(__file__).parent.parent.parent / "data" / "learned_keywords.json"

# ─── Fixed taxonomy: theme → procurement_category ───────────────────────────
THEME_TO_CATEGORY = {
    "Cybersecurity Modernization": "IT Security Consulting",
    "Digital Transformation": "Software Development & IT Consulting",
    "AI & Machine Learning": "AI/ML Consulting & Development",
    "Healthcare Digitization": "Health IT & EHR Systems",
    "Clean Energy Infrastructure": "Engineering & Environmental Consulting",
    "Municipal Modernization": "Cloud & SaaS Procurement",
    "Workforce Development": "Training & HR Consulting",
    "Research & Innovation": "Research & Advisory Services",
    "Transportation & Logistics": "Infrastructure & Systems Integration",
    "Environmental & Climate": "Environmental Consulting",
    "Indigenous Programs": "Community & Social Consulting",
    "Defence & Security": "Defence Consulting & Systems",
}

# ─── Department name → theme (highest confidence matching) ──────────────────
DEPARTMENT_RULES = {
    # Defence & Security
    "national defence": "Defence & Security",
    "department of national defence": "Defence & Security",
    "public safety canada": "Defence & Security",
    "royal canadian mounted police": "Defence & Security",
    "canadian security intelligence": "Defence & Security",
    "communications security establishment": "Defence & Security",
    "correctional service": "Defence & Security",
    
    # Healthcare
    "health canada": "Healthcare Digitization",
    "public health agency": "Healthcare Digitization",
    "canadian institutes of health research": "Healthcare Digitization",
    "canadian food inspection agency": "Healthcare Digitization",
    
    # Transportation
    "transport canada": "Transportation & Logistics",
    "infrastructure canada": "Transportation & Logistics",
    "marine atlantic": "Transportation & Logistics",
    "via rail": "Transportation & Logistics",
    "windsor-detroit bridge authority": "Transportation & Logistics",
    
    # Environment & Climate
    "environment and climate change canada": "Environmental & Climate",
    "parks canada": "Environmental & Climate",
    "impact assessment agency": "Environmental & Climate",
    
    # Clean Energy
    "natural resources canada": "Clean Energy Infrastructure",
    "canada energy regulator": "Clean Energy Infrastructure",
    "atomic energy of canada": "Clean Energy Infrastructure",
    
    # Digital Transformation
    "innovation, science and economic development": "Digital Transformation",
    "treasury board": "Digital Transformation",
    "shared services canada": "Digital Transformation",
    "statistics canada": "Digital Transformation",
    "canadian digital service": "Digital Transformation",
    
    # Cybersecurity
    "centre for cyber security": "Cybersecurity Modernization",
    "cyber security": "Cybersecurity Modernization",
    
    # Indigenous
    "indigenous services canada": "Indigenous Programs",
    "crown-indigenous relations": "Indigenous Programs",
    "indigenous services": "Indigenous Programs",
    
    # Workforce
    "employment and social development": "Workforce Development",
    "canada school of public service": "Workforce Development",
    "labour program": "Workforce Development",
    
    # Research & Innovation
    "national research council": "Research & Innovation",
    "social sciences and humanities research council": "Research & Innovation",
    "natural sciences and engineering research council": "Research & Innovation",
    "canadian institutes of health research": "Research & Innovation",
    "canada foundation for innovation": "Research & Innovation",
    "national science advisor": "Research & Innovation",
    "granting council": "Research & Innovation",
    
    # Municipal
    "federation of canadian municipalities": "Municipal Modernization",
    "municipal": "Municipal Modernization",
    
    # Additional departments discovered from CSV data
    "canadian space agency": "Research & Innovation",
    "federal economic development agency": "Municipal Modernization",
    "feddev ontario": "Municipal Modernization",
    "pacific economic development": "Municipal Modernization",
    "prairies economic development": "Municipal Modernization",
    "atlantic canada opportunities agency": "Municipal Modernization",
    "canada economic development for quebec": "Municipal Modernization",
    "department of justice": "Defence & Security",
    "justice canada": "Defence & Security",
    "canadian heritage": "Workforce Development",
    "department of canadian heritage": "Workforce Development",
    "global affairs canada": "Research & Innovation",
    "foreign affairs": "Research & Innovation",
    "immigration, refugees and citizenship": "Workforce Development",
    "public services and procurement canada": "Digital Transformation",
    "agriculture and agri-food canada": "Environmental & Climate",
    "fisheries and oceans canada": "Environmental & Climate",
    "canadian radio-television": "Digital Transformation",
    "canada revenue agency": "Digital Transformation",
    "veterans affairs canada": "Defence & Security",
    "women and gender equality": "Workforce Development",
    "canadian northern economic development agency": "Municipal Modernization",
    "privy council office": "Research & Innovation",
    "canada mortgage and housing": "Municipal Modernization",
}

# ─── Keyword → theme (matches against description + program name) ───────────
KEYWORD_RULES = {
    # Cybersecurity
    "cybersecurity": "Cybersecurity Modernization",
    "cyber security": "Cybersecurity Modernization",
    "cyber threat": "Cybersecurity Modernization",
    "information security": "Cybersecurity Modernization",
    "network security": "Cybersecurity Modernization",
    
    # AI & ML
    "artificial intelligence": "AI & Machine Learning",
    "machine learning": "AI & Machine Learning",
    "deep learning": "AI & Machine Learning",
    "neural network": "AI & Machine Learning",
    "natural language processing": "AI & Machine Learning",
    "computer vision": "AI & Machine Learning",
    
    # Digital Transformation
    "digital transformation": "Digital Transformation",
    "digital government": "Digital Transformation",
    "cloud migration": "Digital Transformation",
    "software development": "Digital Transformation",
    "data analytics": "Digital Transformation",
    "open data": "Digital Transformation",
    "digital service": "Digital Transformation",
    
    # Healthcare
    "health care": "Healthcare Digitization",
    "healthcare": "Healthcare Digitization",
    "hospital": "Healthcare Digitization",
    "medical": "Healthcare Digitization",
    "patient": "Healthcare Digitization",
    "clinical": "Healthcare Digitization",
    "pharmaceutical": "Healthcare Digitization",
    "mental health": "Healthcare Digitization",
    "pandemic": "Healthcare Digitization",
    "vaccine": "Healthcare Digitization",
    
    # Clean Energy
    "clean energy": "Clean Energy Infrastructure",
    "renewable energy": "Clean Energy Infrastructure",
    "solar energy": "Clean Energy Infrastructure",
    "wind energy": "Clean Energy Infrastructure",
    "electric vehicle": "Clean Energy Infrastructure",
    "battery": "Clean Energy Infrastructure",
    "hydrogen": "Clean Energy Infrastructure",
    "nuclear": "Clean Energy Infrastructure",
    "carbon capture": "Clean Energy Infrastructure",
    "net zero": "Clean Energy Infrastructure",
    "net-zero": "Clean Energy Infrastructure",
    "green building": "Clean Energy Infrastructure",
    "energy efficiency": "Clean Energy Infrastructure",
    
    # Municipal
    "smart city": "Municipal Modernization",
    "smart cities": "Municipal Modernization",
    "municipal infrastructure": "Municipal Modernization",
    "broadband": "Municipal Modernization",
    "connectivity": "Municipal Modernization",
    "rural internet": "Municipal Modernization",
    
    # Workforce
    "workforce development": "Workforce Development",
    "skills training": "Workforce Development",
    "job training": "Workforce Development",
    "apprenticeship": "Workforce Development",
    "employment program": "Workforce Development",
    "youth employment": "Workforce Development",
    "skills development": "Workforce Development",
    "labour market": "Workforce Development",
    "career development": "Workforce Development",
    
    # Research & Innovation
    "research grant": "Research & Innovation",
    "innovation fund": "Research & Innovation",
    "scientific research": "Research & Innovation",
    "r&d": "Research & Innovation",
    "research and development": "Research & Innovation",
    "prototype": "Research & Innovation",
    "pilot project": "Research & Innovation",
    
    # Transportation
    "transportation": "Transportation & Logistics",
    "highway": "Transportation & Logistics",
    "railway": "Transportation & Logistics",
    "rail infrastructure": "Transportation & Logistics",
    "port": "Transportation & Logistics",
    "airport": "Transportation & Logistics",
    "transit": "Transportation & Logistics",
    "supply chain": "Transportation & Logistics",
    "logistics": "Transportation & Logistics",
    
    # Environmental & Climate
    "climate change": "Environmental & Climate",
    "climate action": "Environmental & Climate",
    "greenhouse gas": "Environmental & Climate",
    "ghg emission": "Environmental & Climate",
    "environmental assessment": "Environmental & Climate",
    "biodiversity": "Environmental & Climate",
    "conservation": "Environmental & Climate",
    "pollution": "Environmental & Climate",
    "waste management": "Environmental & Climate",
    "water treatment": "Environmental & Climate",
    "clean water": "Environmental & Climate",
    
    # Indigenous
    "indigenous": "Indigenous Programs",
    "first nation": "Indigenous Programs",
    "first nations": "Indigenous Programs",
    "inuit": "Indigenous Programs",
    "métis": "Indigenous Programs",
    "metis": "Indigenous Programs",
    "aboriginal": "Indigenous Programs",
    "reconciliation": "Indigenous Programs",
    "treaty": "Indigenous Programs",
    
    # Defence & Security
    "defence": "Defence & Security",
    "defense": "Defence & Security",
    "military": "Defence & Security",
    "armed forces": "Defence & Security",
    "national security": "Defence & Security",
    "border security": "Defence & Security",
    "veterans": "Defence & Security",
    
    # Additional keywords from CSV analysis
    "space agency": "Research & Innovation",
    "official language": "Workforce Development",
    "linguistic": "Workforce Development",
    "multiculturalism": "Workforce Development",
    "anti-racism": "Workforce Development",
    "museum": "Workforce Development",
    "arts": "Workforce Development",
    "cultural": "Workforce Development",
    "heritage": "Workforce Development",
    "community infrastructure": "Municipal Modernization",
    "community asset": "Municipal Modernization",
    "economic development": "Municipal Modernization",
    "rural development": "Municipal Modernization",
    "agriculture": "Environmental & Climate",
    "fisheries": "Environmental & Climate",
    "aquaculture": "Environmental & Climate",
    "housing": "Municipal Modernization",
    "affordable housing": "Municipal Modernization",
    "homelessness": "Workforce Development",
    "immigration": "Workforce Development",
    "refugee": "Workforce Development",
    "justice": "Defence & Security",
    "court": "Defence & Security",
    "judicial": "Defence & Security",
    "policing": "Defence & Security",
}


class HybridClassifier:
    """
    Hybrid classifier: rules first, LLM fallback, auto-learns new keywords.
    
    Flow:
    1. Try department name matching (confidence 0.90)
    2. Try keyword matching on description/program (confidence 0.80)
    3. Try learned keywords from previous LLM runs (confidence 0.75)
    4. If still no match → send to LLM → save new keywords for next time
    """
    
    def __init__(self, use_llm_fallback: bool = True):
        self.use_llm_fallback = use_llm_fallback
        self.learned_keywords: dict[str, str] = {}
        self._load_learned_keywords()
        self._llm_classifier: Optional[GrantClassifier] = None
        
        # Stats for logging
        self.stats = {
            "department_match": 0,
            "keyword_match": 0,
            "learned_match": 0,
            "llm_fallback": 0,
            "no_match": 0,
        }
    
    def _load_learned_keywords(self):
        """Load previously learned keywords from JSON file"""
        try:
            if LEARNED_KEYWORDS_PATH.exists():
                with open(LEARNED_KEYWORDS_PATH, "r") as f:
                    data = json.load(f)
                    self.learned_keywords = data.get("keywords", {})
                    logger.info(f"[RULE_CLASSIFIER] Loaded {len(self.learned_keywords)} learned keywords")
            else:
                self.learned_keywords = {}
        except Exception as e:
            logger.warning(f"[RULE_CLASSIFIER] Could not load learned keywords: {e}")
            self.learned_keywords = {}
    
    def _save_learned_keywords(self):
        """Persist learned keywords to JSON file"""
        try:
            LEARNED_KEYWORDS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(LEARNED_KEYWORDS_PATH, "w") as f:
                json.dump({
                    "keywords": self.learned_keywords,
                    "updated_at": datetime.now().isoformat(),
                    "total_count": len(self.learned_keywords),
                }, f, indent=2)
            logger.info(f"[RULE_CLASSIFIER] Saved {len(self.learned_keywords)} learned keywords")
        except Exception as e:
            logger.warning(f"[RULE_CLASSIFIER] Could not save learned keywords: {e}")
    
    def _get_llm_classifier(self) -> GrantClassifier:
        """Lazy-init the LLM classifier (only when needed)"""
        if self._llm_classifier is None:
            self._llm_classifier = GrantClassifier()
        return self._llm_classifier
    
    def _match_department(self, issuer: str) -> Optional[str]:
        """Try to match on department/issuer name"""
        issuer_lower = issuer.lower().strip()
        
        # Exact substring match against department rules
        for keyword, theme in DEPARTMENT_RULES.items():
            if keyword in issuer_lower:
                return theme
        return None
    
    def _match_keywords(self, text: str) -> Optional[str]:
        """Try to match on description/program keywords"""
        text_lower = text.lower()
        
        for keyword, theme in KEYWORD_RULES.items():
            if keyword in text_lower:
                return theme
        return None
    
    def _match_learned(self, text: str) -> Optional[str]:
        """Try to match against learned keywords from previous LLM runs"""
        text_lower = text.lower()
        
        for keyword, theme in self.learned_keywords.items():
            if keyword in text_lower:
                return theme
        return None
    
    def _derive_sector_tags(self, theme: str, issuer: str, description: str, region: str) -> list[str]:
        """Generate sector tags from available data"""
        tags = set()
        
        issuer_lower = (issuer or "").lower()
        desc_lower = (description or "").lower()
        region_lower = (region or "").lower()
        
        # Add theme-based tag
        theme_tag = theme.lower().split()[0]  # e.g. "cybersecurity", "digital", "ai"
        tags.add(theme_tag)
        
        # Federal detection
        if any(w in issuer_lower for w in ["canada", "federal", "government of canada"]):
            tags.add("federal")
        
        # Province detection
        province_map = {
            "ontario": "ontario", "quebec": "quebec", "british columbia": "bc",
            "alberta": "alberta", "manitoba": "manitoba", "saskatchewan": "saskatchewan",
            "nova scotia": "nova_scotia", "new brunswick": "new_brunswick",
            "newfoundland": "newfoundland", "pei": "pei", "prince edward": "pei",
            "yukon": "yukon", "nunavut": "nunavut", "northwest": "nwt",
        }
        combined = f"{desc_lower} {region_lower} {issuer_lower}"
        for prov, tag in province_map.items():
            if prov in combined:
                tags.add(tag)
                break
        
        return list(tags)[:4]
    
    def classify_one(self, grant: CleanedGrantRecord) -> ClassificationResult:
        """
        Classify a single grant using rules. Returns None if no rule matches.
        """
        issuer = grant.issuer_canonical or ""
        description = grant.description or ""
        program = ""  # Not always available in CleanedGrantRecord
        region = grant.region or ""
        combined_text = f"{issuer} {description} {program}"
        
        # Pass 1: Department match (highest confidence)
        theme = self._match_department(issuer)
        if theme:
            self.stats["department_match"] += 1
            return ClassificationResult(
                grant_id=grant.id,
                funding_theme=theme,
                procurement_category=THEME_TO_CATEGORY[theme],
                sector_tags=self._derive_sector_tags(theme, issuer, description, region),
                confidence=0.90,
                reasoning=f"Department match: {issuer}",
                needs_review=False,
                classification_flags=["rule_department_match"],
            )
        
        # Pass 2: Keyword match on description
        theme = self._match_keywords(combined_text)
        if theme:
            self.stats["keyword_match"] += 1
            return ClassificationResult(
                grant_id=grant.id,
                funding_theme=theme,
                procurement_category=THEME_TO_CATEGORY[theme],
                sector_tags=self._derive_sector_tags(theme, issuer, description, region),
                confidence=0.80,
                reasoning=f"Keyword match in description",
                needs_review=False,
                classification_flags=["rule_keyword_match"],
            )
        
        # Pass 3: Learned keyword match
        theme = self._match_learned(combined_text)
        if theme:
            self.stats["learned_match"] += 1
            return ClassificationResult(
                grant_id=grant.id,
                funding_theme=theme,
                procurement_category=THEME_TO_CATEGORY.get(theme, "Research & Advisory Services"),
                sector_tags=self._derive_sector_tags(theme, issuer, description, region),
                confidence=0.75,
                reasoning=f"Learned keyword match from previous LLM classification",
                needs_review=False,
                classification_flags=["rule_learned_match"],
            )
        
        # No rule matched
        return None
    
    def _learn_from_llm_result(self, grant: CleanedGrantRecord, result: ClassificationResult):
        """
        Extract distinctive keywords from a grant that the LLM classified,
        and save them so we don't need the LLM for similar grants next time.
        """
        if result.confidence < 0.60:
            return  # Don't learn from low-confidence results
        
        theme = result.funding_theme
        if theme not in THEME_TO_CATEGORY:
            return  # Don't learn invalid themes
        
        description = (grant.description or "").lower().strip()
        issuer = (grant.issuer_canonical or "").lower().strip()
        
        # Extract meaningful phrases from the description (2-3 word chunks)
        words = description.split()
        new_keywords = []
        
        # Try 3-word phrases
        for i in range(len(words) - 2):
            phrase = " ".join(words[i:i+3])
            # Only learn phrases that are specific enough (>10 chars, not common)
            if len(phrase) > 10 and phrase not in KEYWORD_RULES:
                new_keywords.append(phrase)
        
        # Try 2-word phrases
        for i in range(len(words) - 1):
            phrase = " ".join(words[i:i+2])
            if len(phrase) > 8 and phrase not in KEYWORD_RULES:
                new_keywords.append(phrase)
        
        # Also learn the issuer name if it's not already in department rules
        if issuer and len(issuer) > 5 and issuer not in DEPARTMENT_RULES:
            new_keywords.append(issuer)
        
        # Save the most distinctive keywords (limit to 3 per grant)
        for kw in new_keywords[:3]:
            if kw not in self.learned_keywords:
                self.learned_keywords[kw] = theme
                logger.debug(f"[RULE_CLASSIFIER] Learned: '{kw}' → {theme}")
    
    async def classify_batch(
        self,
        grants: list[CleanedGrantRecord],
        batch_size: int = 25,
    ) -> list[ClassificationResult]:
        """
        Classify a batch of grants: rules first, LLM fallback for unknowns.
        Auto-learns new keywords from LLM results.
        """
        all_results: list[ClassificationResult] = []
        unmatched_grants: list[CleanedGrantRecord] = []
        
        # ── Phase 1: Rule-based classification (instant) ────────────────────
        for grant in grants:
            result = self.classify_one(grant)
            if result:
                all_results.append(result)
            else:
                unmatched_grants.append(grant)
        
        rule_count = len(all_results)
        logger.info(
            f"[RULE_CLASSIFIER] Rule-based: {rule_count}/{len(grants)} classified "
            f"(dept={self.stats['department_match']}, kw={self.stats['keyword_match']}, "
            f"learned={self.stats['learned_match']})"
        )
        
        # ── Phase 2: LLM fallback for unmatched (only if enabled) ───────────
        if unmatched_grants and self.use_llm_fallback:
            logger.info(
                f"[RULE_CLASSIFIER] Sending {len(unmatched_grants)} unmatched grants to LLM..."
            )
            try:
                llm = self._get_llm_classifier()
                llm_results = await llm.classify_batch(unmatched_grants, batch_size=batch_size)
                
                # Learn from LLM results
                learned_count = 0
                for grant, result in zip(unmatched_grants, llm_results):
                    self._learn_from_llm_result(grant, result)
                    learned_count += 1
                
                # Save learned keywords
                if learned_count > 0:
                    self._save_learned_keywords()
                    logger.info(
                        f"[RULE_CLASSIFIER] Auto-learned keywords from {learned_count} LLM results"
                    )
                
                all_results.extend(llm_results)
                self.stats["llm_fallback"] += len(llm_results)
                
            except Exception as e:
                logger.error(f"[RULE_CLASSIFIER] LLM fallback failed: {e}")
                # Create fallback results for unmatched grants
                for grant in unmatched_grants:
                    fallback = ClassificationResult(
                        grant_id=grant.id,
                        funding_theme="Research & Innovation",
                        procurement_category="Research & Advisory Services",
                        sector_tags=["unclassified"],
                        confidence=0.30,
                        reasoning="No rule match, LLM unavailable",
                        needs_review=True,
                        classification_flags=["no_match", "llm_error"],
                    )
                    all_results.append(fallback)
                    self.stats["no_match"] += 1
        
        elif unmatched_grants and not self.use_llm_fallback:
            # No LLM - assign default with low confidence
            for grant in unmatched_grants:
                fallback = ClassificationResult(
                    grant_id=grant.id,
                    funding_theme="Research & Innovation",
                    procurement_category="Research & Advisory Services",
                    sector_tags=["unclassified"],
                    confidence=0.30,
                    reasoning="No rule match (LLM disabled)",
                    needs_review=True,
                    classification_flags=["no_match", "llm_disabled"],
                )
                all_results.append(fallback)
                self.stats["no_match"] += 1
        
        # ── Summary ─────────────────────────────────────────────────────────
        logger.info(
            f"[RULE_CLASSIFIER] Classification complete: "
            f"{len(all_results)} total, "
            f"{rule_count} by rules, "
            f"{self.stats['llm_fallback']} by LLM, "
            f"{self.stats['no_match']} unclassified"
        )
        
        return all_results
    
    def get_stats(self) -> dict:
        """Return classification statistics"""
        return {
            **self.stats,
            "learned_keywords_count": len(self.learned_keywords),
        }
