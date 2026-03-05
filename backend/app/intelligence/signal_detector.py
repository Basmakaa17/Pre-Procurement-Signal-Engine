"""
Signal Detection Engine
Reads classified grants from Supabase and generates procurement signals
"""
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from app.database.client import get_supabase_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SignalResult:
    """Result of signal detection for a grant group"""
    
    signal_name: str
    funding_theme: str
    procurement_category: str
    department_cluster: Optional[str]
    region: Optional[str]
    total_funding_cad: float
    grant_count: int
    earliest_grant_date: Optional[date]
    latest_grant_date: Optional[date]
    time_horizon_min_months: int
    time_horizon_max_months: int
    confidence_score: float
    signal_strength: str
    predicted_rfp_window_start: Optional[date]
    predicted_rfp_window_end: Optional[date]
    supporting_grant_ids: list[str]
    momentum_score: float = 0.0
    momentum_direction: str = "stable"
    last_signal_refresh: Optional[datetime] = None
    recommended_action: Optional[str] = None
    why_this_signal: Optional[str] = None


class SignalDetector:
    """Detects procurement signals from classified grant records"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.taxonomy_cache: dict[str, dict] = {}
        self._load_taxonomy_cache()
    
    def _load_taxonomy_cache(self):
        """Load taxonomy into cache for fast lookups"""
        try:
            response = self.supabase.table("procurement_taxonomy").select("*").execute()
            for row in response.data:
                theme = row["grant_theme"]
                self.taxonomy_cache[theme] = {
                    "procurement_category": row["procurement_category"],
                    "lag_months_min": row["lag_months_min"],
                    "lag_months_max": row["lag_months_max"],
                    "confidence_base": float(row["confidence_base"]) if row["confidence_base"] else 0.75,
                }
            logger.info(f"Loaded {len(self.taxonomy_cache)} taxonomy entries into cache")
        except Exception as e:
            logger.error(f"Failed to load taxonomy cache: {e}")
            raise
    
    async def detect_signals(self) -> list[SignalResult]:
        """
        Detect procurement signals from classified grants
        
        Returns:
            List of SignalResult objects
        """
        logger.info("[SIGNAL_DETECTOR] Starting signal detection...")
        
        # Query grant_records grouped by (funding_theme, procurement_category, region)
        # WHERE is_quarantined = false AND llm_confidence >= 0.70
        # AND award_date >= NOW() - INTERVAL '18 months'
        
        try:
            # Calculate date 18 months ago
            eighteen_months_ago = datetime.now() - timedelta(days=18 * 30)
            date_str = eighteen_months_ago.strftime("%Y-%m-%d")
            
            # Fetch all qualifying grants
            response = self.supabase.table("grant_records").select(
                "id, funding_theme, procurement_category, region, amount_cad, award_date, issuer_canonical"
            ).eq("is_quarantined", False).gte("llm_confidence", 0.70).gte("award_date", date_str).execute()
            
            grants = response.data
            logger.info(f"[SIGNAL_DETECTOR] Found {len(grants)} qualifying grants")
            
            if not grants:
                return []
            
            # Group grants by (funding_theme, procurement_category, region)
            groups: dict[tuple, list[dict]] = {}
            
            for grant in grants:
                theme = grant.get("funding_theme")
                category = grant.get("procurement_category")
                region = grant.get("region") or "Unknown"
                
                if not theme or not category:
                    continue
                
                key = (theme, category, region)
                if key not in groups:
                    groups[key] = []
                groups[key].append(grant)
            
            logger.info(f"[SIGNAL_DETECTOR] Grouped into {len(groups)} signal groups")
            
            # Process each group
            signals = []
            for (theme, category, region), group_grants in groups.items():
                # Calculate group statistics
                grant_count = len(group_grants)
                total_funding = sum(
                    float(g.get("amount_cad", 0) or 0)
                    for g in group_grants
                )
                
                # SIGNAL THRESHOLD: only create signal if grant_count >= 3 OR total_funding >= 1,000,000
                if grant_count < 3 and total_funding < 1_000_000:
                    continue
                
                # Get dates (handle various date formats)
                dates = []
                for g in group_grants:
                    award_date = g.get("award_date")
                    if not award_date:
                        continue
                    
                    try:
                        if isinstance(award_date, str):
                            # Try ISO format first
                            if "T" in award_date:
                                date_obj = datetime.fromisoformat(award_date.split("T")[0]).date()
                            else:
                                date_obj = datetime.fromisoformat(award_date).date()
                        elif isinstance(award_date, date):
                            date_obj = award_date
                        else:
                            continue
                        dates.append(date_obj)
                    except (ValueError, TypeError):
                        continue
                
                if not dates:
                    continue
                
                earliest_date = min(dates)
                latest_date = max(dates)
                
                # Load matching taxonomy row
                taxonomy = self.taxonomy_cache.get(theme)
                if not taxonomy:
                    logger.warning(f"No taxonomy found for theme: {theme}")
                    continue
                
                lag_min = taxonomy["lag_months_min"]
                lag_max = taxonomy["lag_months_max"]
                confidence_base = taxonomy["confidence_base"]
                
                # Calculate predicted RFP window
                predicted_start = self._add_months(latest_date, lag_min)
                predicted_end = self._add_months(latest_date, lag_max)
                
                # Calculate confidence score
                volume_bonus = min(0.10, grant_count * 0.01)  # max +10%
                recency_bonus = 0.05 if latest_date > (date.today() - timedelta(days=90)) else 0
                confidence_score = min(0.99, confidence_base + volume_bonus + recency_bonus)
                
                # Assign signal strength
                if total_funding >= 10_000_000 or grant_count >= 10:
                    signal_strength = "strong"
                elif total_funding >= 1_000_000 or grant_count >= 5:
                    signal_strength = "moderate"
                else:
                    signal_strength = "weak"
                
                # Generate signal name
                signal_name = f"{theme} - {category}"
                if region and region != "Unknown":
                    signal_name += f" ({region})"
                
                # Get department cluster (most common issuer)
                issuers = [g.get("issuer_canonical") for g in group_grants if g.get("issuer_canonical")]
                department_cluster = max(set(issuers), key=issuers.count) if issuers else None
                
                # Get supporting grant IDs with deduplication
                # First deduplicate grants based on content
                seen_hashes = set()
                unique_grants = []
                
                for grant in group_grants:
                    # Create a content hash for deduplication
                    content_hash = f"{grant.get('recipient_name', '')}|{grant.get('amount_cad', '')}|{grant.get('award_date', '')}|{grant.get('issuer_canonical', '')}"
                    
                    if content_hash not in seen_hashes:
                        seen_hashes.add(content_hash)
                        unique_grants.append(grant)
                
                supporting_grant_ids = [g["id"] for g in unique_grants]
                
                signal = SignalResult(
                    signal_name=signal_name,
                    funding_theme=theme,
                    procurement_category=category,
                    department_cluster=department_cluster,
                    region=region if region != "Unknown" else None,
                    total_funding_cad=total_funding,
                    grant_count=grant_count,
                    earliest_grant_date=earliest_date,
                    latest_grant_date=latest_date,
                    time_horizon_min_months=lag_min,
                    time_horizon_max_months=lag_max,
                    confidence_score=confidence_score,
                    signal_strength=signal_strength,
                    predicted_rfp_window_start=predicted_start,
                    predicted_rfp_window_end=predicted_end,
                    supporting_grant_ids=supporting_grant_ids,
                )
                
                signals.append(signal)
            
            # Upsert signals to database
            logger.info(f"[SIGNAL_DETECTOR] Upserting {len(signals)} signals to database...")
            
            for signal in signals:
                try:
                    # Check if signal already exists (same funding_theme + region + procurement_category)
                    existing = self.supabase.table("procurement_signals").select("id").eq(
                        "funding_theme", signal.funding_theme
                    ).eq("procurement_category", signal.procurement_category).eq(
                        "region", signal.region or "Unknown"
                    ).execute()
                    
                    signal_data = {
                        "signal_name": signal.signal_name,
                        "funding_theme": signal.funding_theme,
                        "procurement_category": signal.procurement_category,
                        "department_cluster": signal.department_cluster,
                        "region": signal.region,
                        "total_funding_cad": signal.total_funding_cad,
                        "grant_count": signal.grant_count,
                        "earliest_grant_date": signal.earliest_grant_date.isoformat() if signal.earliest_grant_date else None,
                        "latest_grant_date": signal.latest_grant_date.isoformat() if signal.latest_grant_date else None,
                        "time_horizon_min_months": signal.time_horizon_min_months,
                        "time_horizon_max_months": signal.time_horizon_max_months,
                        "confidence_score": signal.confidence_score,
                        "signal_strength": signal.signal_strength,
                        "predicted_rfp_window_start": signal.predicted_rfp_window_start.isoformat() if signal.predicted_rfp_window_start else None,
                        "predicted_rfp_window_end": signal.predicted_rfp_window_end.isoformat() if signal.predicted_rfp_window_end else None,
                        "supporting_grant_ids": signal.supporting_grant_ids,
                        "is_active": True,
                        "momentum_score": signal.momentum_score,
                        "momentum_direction": signal.momentum_direction,
                        "last_signal_refresh": datetime.now().isoformat(),
                        "recommended_action": signal.recommended_action,
                        "why_this_signal": signal.why_this_signal,
                    }
                    
                    if existing.data:
                        # Update existing signal
                        signal_id = existing.data[0]["id"]
                        self.supabase.table("procurement_signals").update(signal_data).eq("id", signal_id).execute()
                    else:
                        # Insert new signal
                        self.supabase.table("procurement_signals").insert(signal_data).execute()
                        
                except Exception as e:
                    logger.error(f"Failed to upsert signal {signal.signal_name}: {e}")
                    continue
            
            logger.info(f"[SIGNAL_DETECTOR] Successfully created/updated {len(signals)} signals")
            return signals
            
        except Exception as e:
            logger.error(f"[SIGNAL_DETECTOR] Error during signal detection: {e}")
            raise
    
    def _add_months(self, date_obj: date, months: int) -> date:
        """Add months to a date"""
        year = date_obj.year
        month = date_obj.month + months
        
        while month > 12:
            year += 1
            month -= 12
        
        while month < 1:
            year -= 1
            month += 12
        
        # Handle day overflow (e.g., Feb 30 -> Feb 28)
        try:
            return date(year, month, date_obj.day)
        except ValueError:
            # If day doesn't exist in target month, use last day of month
            if month == 2:
                day = 28 if year % 4 != 0 or (year % 100 == 0 and year % 400 != 0) else 29
            elif month in [4, 6, 9, 11]:
                day = 30
            else:
                day = 31
            return date(year, month, min(day, date_obj.day))


async def run_full_intelligence_pipeline():
    """
    Run the full intelligence pipeline:
    1. Fetch unclassified grants from Supabase
    2. Run classifier on them
    3. Update grant_records with classification results
    4. Run detect_signals()
    5. Log summary
    """
    logger.info("=" * 60)
    logger.info("🚀 Starting Full Intelligence Pipeline")
    logger.info("=" * 60)
    
    try:
        # Step 1: Fetch unclassified grants
        logger.info("[PIPELINE] Step 1: Fetching unclassified grants...")
        supabase = get_supabase_client()
        
        response = supabase.table("grant_records").select(
            "id, source, issuer_canonical, recipient_name, amount_cad, award_date, region, description"
        ).is_("funding_theme", "null").eq("is_quarantined", False).execute()
        
        grants_data = response.data
        logger.info(f"[PIPELINE] Found {len(grants_data)} unclassified grants")
        
        if not grants_data:
            logger.info("[PIPELINE] No unclassified grants to process")
        else:
            # Convert to CleanedGrantRecord
            from app.models.cleaned_grant import CleanedGrantRecord
            from app.intelligence.rule_classifier import HybridClassifier
            
            grants = []
            for g in grants_data:
                try:
                    award_date = None
                    if g.get("award_date"):
                        if isinstance(g["award_date"], str):
                            award_date = datetime.fromisoformat(g["award_date"].split("T")[0]).date()
                        elif isinstance(g["award_date"], date):
                            award_date = g["award_date"]
                    
                    grant = CleanedGrantRecord(
                        id=g["id"],
                        source=g["source"],
                        issuer_canonical=g["issuer_canonical"],
                        recipient_name=g["recipient_name"],
                        amount_cad=float(g["amount_cad"]) if g.get("amount_cad") else None,
                        award_date=award_date,
                        region=g.get("region"),
                        description=g.get("description"),
                    )
                    grants.append(grant)
                except Exception as e:
                    logger.warning(f"Failed to parse grant {g.get('id')}: {e}")
                    continue
            
            # Step 2: Run hybrid classifier (rules first, LLM only for unknowns)
            logger.info(f"[PIPELINE] Step 2: Classifying {len(grants)} grants (hybrid: rules + LLM fallback)...")
            classifier = HybridClassifier(use_llm_fallback=True)
            classifications = await classifier.classify_batch(grants, batch_size=25)
            logger.info(f"[PIPELINE] Classified {len(classifications)} grants — stats: {classifier.get_stats()}")
            
            # Step 3: Update grant_records
            logger.info("[PIPELINE] Step 3: Updating grant_records with classifications...")
            updated_count = 0
            
            for classification in classifications:
                try:
                    update_data = {
                        "funding_theme": classification.funding_theme,
                        "procurement_category": classification.procurement_category,
                        "sector_tags": classification.sector_tags,
                        "llm_confidence": classification.confidence,
                        "llm_classified_at": datetime.now().isoformat(),
                        "quality_flags": classification.classification_flags,
                    }
                    
                    supabase.table("grant_records").update(update_data).eq("id", classification.grant_id).execute()
                    updated_count += 1
                except Exception as e:
                    logger.error(f"Failed to update grant {classification.grant_id}: {e}")
            
            logger.info(f"[PIPELINE] Updated {updated_count} grant records")
        
        # Step 4: Run signal detection
        logger.info("[PIPELINE] Step 4: Detecting procurement signals...")
        detector = SignalDetector()
        signals = await detector.detect_signals()
        logger.info(f"[PIPELINE] Detected {len(signals)} signals")
        
        # Step 5: Summary
        logger.info("=" * 60)
        logger.info("✅ Intelligence Pipeline Completed")
        logger.info("=" * 60)
        logger.info(f"  - Grants classified: {len(classifications) if 'classifications' in locals() else 0}")
        logger.info(f"  - Signals detected: {len(signals)}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"[PIPELINE] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    import asyncio
    
    asyncio.run(run_full_intelligence_pipeline())
