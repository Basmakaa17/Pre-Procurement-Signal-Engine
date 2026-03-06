"""
Open Canada Grants & Contributions adapter
Fetches grant records from the CKAN datastore_search API with
sort-descending pagination and early date-based stop.
"""
import asyncio
import json
import logging
import os
from datetime import date, datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.models.raw_grant import RawGrantRecord

logger = logging.getLogger(__name__)

# Helper function for safe debug logging (only in development)
def _safe_debug_log(data: dict):
    """Safely write debug log only if the file exists or can be created"""
    debug_log_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        '.cursor',
        'debug.log'
    )
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)
        with open(debug_log_path, 'a') as f:
            f.write(json.dumps(data) + "\n")
    except (OSError, IOError, PermissionError):
        # Silently fail in production - debug logging is optional
        pass

# Known resource ID for "Proactive Disclosure - Grants and Contributions"
# Discovered via package_show; hardcoded as fallback so we don't need an
# extra API call on every run.
GRANTS_RESOURCE_ID = "1d15a62f-5656-49ad-8c88-f40ce689d831"
DATASET_ID = "432527ab-7aac-45b5-81d6-7597107a7013"
BASE_URL = "https://open.canada.ca/data/en/api/3/action"
PAGE_SIZE = 10_000  # max reliable limit per datastore_search call
COURTESY_DELAY_S = 1  # seconds between paginated requests


class OpenCanadaAdapter:
    """
    Fetches grants from the Open Canada CKAN datastore API.

    Strategy: sort by agreement_start_date DESC, paginate with offset,
    stop when records fall before min_date or max_records is reached.
    """

    def __init__(self, http_client: httpx.AsyncClient):
        self.client = http_client

    # ------------------------------------------------------------------
    # Resource discovery (with hardcoded fallback)
    # ------------------------------------------------------------------
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=(
            retry_if_exception_type(httpx.HTTPError)
            | retry_if_exception_type(httpx.TimeoutException)
        ),
    )
    async def _discover_resource_id(self) -> str:
        """
        Hit package_show to find the latest English CSV resource with an
        active datastore.  Falls back to the hardcoded GRANTS_RESOURCE_ID.
        """
        url = f"{BASE_URL}/package_show?id={DATASET_ID}"
        headers = {"User-Agent": "PublicusSignalEngine/1.0 research-prototype"}

        try:
            resp = await self.client.get(url, headers=headers, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()

            if not data.get("success"):
                logger.warning("package_show unsuccessful, using hardcoded resource ID")
                return GRANTS_RESOURCE_ID

            resources = data.get("result", {}).get("resources", [])
            for r in resources:
                if (
                    r.get("format", "").upper() == "CSV"
                    and r.get("datastore_active") is True
                    and r.get("name", "").startswith("Proactive Disclosure - Grants and Contributions")
                    and "Nothing to Report" not in r.get("name", "")
                ):
                    rid = r["id"]
                    logger.info(f"Discovered datastore resource: {rid}")
                    return rid

            logger.warning("No matching datastore resource found, using hardcoded ID")
            return GRANTS_RESOURCE_ID

        except Exception as e:
            logger.warning(f"Resource discovery failed ({e}), using hardcoded ID")
            return GRANTS_RESOURCE_ID

    # ------------------------------------------------------------------
    # Main fetch method
    # ------------------------------------------------------------------
    async def fetch_grants(
        self,
        min_date: str = "2025-01-01",
        max_records: Optional[int] = 5000,
    ) -> List[RawGrantRecord]:
        """
        Fetch grants from the CKAN datastore, newest first, stopping when
        records fall before *min_date* or *max_records* is reached.

        Args:
            min_date:    ISO date string (inclusive). Records before this are
                         dropped and pagination stops.
            max_records: Hard cap on total records returned.  None = unlimited.

        Returns:
            List[RawGrantRecord] sorted newest-first, capped at max_records.
        """
        resource_id = await self._discover_resource_id()
        cutoff = date.fromisoformat(min_date)
        headers = {"User-Agent": "PublicusSignalEngine/1.0 research-prototype"}

        all_records: List[RawGrantRecord] = []
        offset = 0
        page_num = 0
        expected_total: Optional[int] = None
        hit_date_boundary = False

        logger.info(
            f"[OpenCanada] Starting fetch — min_date={min_date}, "
            f"max_records={max_records or 'unlimited'}, resource={resource_id}, PAGE_SIZE={PAGE_SIZE}"
        )

        while True:
            page_num += 1
            url = (
                f"{BASE_URL}/datastore_search"
                f"?resource_id={resource_id}"
                f"&limit={PAGE_SIZE}"
                f"&offset={offset}"
                f"&sort=agreement_start_date desc"
            )

            try:
                resp = await self.client.get(
                    url, headers=headers, timeout=60.0
                )
                resp.raise_for_status()
                body = resp.json()
            except Exception as e:
                logger.error(f"[OpenCanada] API error on page {page_num}: {e}")
                raise

            if not body.get("success"):
                raise ValueError(
                    f"datastore_search returned error: {body.get('error', {})}"
                )

            result = body["result"]
            page_records = result.get("records", [])
            current_total = result.get("total", 0)

            # --- Race-condition guard ---
            if expected_total is None:
                expected_total = current_total
                logger.info(
                    f"[OpenCanada] Datastore total: {expected_total:,} records"
                )
            elif current_total != expected_total:
                logger.warning(
                    f"[OpenCanada] Dataset shifted mid-run! "
                    f"Page 1 total={expected_total:,}, "
                    f"page {page_num} total={current_total:,}. "
                    f"Results may contain duplicates or gaps."
                )

            if not page_records:
                logger.info(f"[OpenCanada] No records on page {page_num}, done.")
                # #region agent log
                _safe_debug_log({"runId":"debug","hypothesisId":"A","location":"open_canada.py:171","message":"Pagination stopped: empty page","data":{"page_num":page_num,"offset":offset,"all_records_count":len(all_records),"max_records":max_records},"timestamp":int(datetime.now().timestamp()*1000)})
                # #endregion
                break

            # --- Parse & date-filter this page ---
            page_parsed: List[RawGrantRecord] = []
            records_before_cutoff = 0
            for raw in page_records:
                record_date_str = raw.get("agreement_start_date", "")
                try:
                    record_date = date.fromisoformat(record_date_str[:10])
                except (ValueError, TypeError):
                    record_date = None

                if record_date is not None and record_date < cutoff:
                    records_before_cutoff += 1
                    # Don't set hit_date_boundary here - we'll check after processing the page
                    continue  # skip this record, but keep parsing the page

                parsed = self._parse_datastore_record(raw)
                if parsed:
                    page_parsed.append(parsed)

            all_records.extend(page_parsed)

            # --- Enforce cap before logging ---
            if max_records and len(all_records) >= max_records:
                all_records = all_records[:max_records]

            # --- Progress logging ---
            cap_pct = ""
            if max_records:
                cap_pct = f" ({len(all_records) / max_records * 100:.0f}% of cap)"
            logger.info(
                f"[OpenCanada] Page {page_num}: {len(page_parsed)} parsed (skipped {records_before_cutoff} before {min_date}), "
                f"{len(all_records)} total{cap_pct}"
            )

            # --- Stop conditions ---
            # Only stop on date boundary if ALL records on this page were before cutoff
            # AND we haven't reached max_records yet
            # This ensures we continue fetching if we need more records
            if records_before_cutoff == len(page_records) and len(page_parsed) == 0:
                # All records on this page were before cutoff, and we're sorted DESC
                # So all future records will also be before cutoff
                hit_date_boundary = True
                logger.info(
                    f"[OpenCanada] Reached date boundary ({min_date}) - all records on page {page_num} were before cutoff, stopping."
                )
                # #region agent log
                _safe_debug_log({"runId":"debug","hypothesisId":"A","location":"open_canada.py:218","message":"Pagination stopped: date boundary","data":{"page_num":page_num,"offset":offset,"all_records_count":len(all_records),"records_before_cutoff":records_before_cutoff,"page_records_count":len(page_records),"min_date":min_date},"timestamp":int(datetime.now().timestamp()*1000)})
                # #endregion
                break

            if max_records and len(all_records) >= max_records:
                all_records = all_records[:max_records]
                logger.info(
                    f"[OpenCanada] Hit max_records cap ({max_records}), stopping pagination."
                )
                # #region agent log
                _safe_debug_log({"runId":"debug","hypothesisId":"A","location":"open_canada.py:225","message":"Pagination stopped: max_records reached","data":{"page_num":page_num,"offset":offset,"all_records_count":len(all_records),"max_records":max_records},"timestamp":int(datetime.now().timestamp()*1000)})
                # #endregion
                break

            if len(page_records) < PAGE_SIZE:
                logger.info(f"[OpenCanada] Last page reached (got {len(page_records)} records, less than PAGE_SIZE={PAGE_SIZE}).")
                # #region agent log
                _safe_debug_log({"runId":"debug","hypothesisId":"A","location":"open_canada.py:229","message":"Pagination stopped: last page","data":{"page_num":page_num,"offset":offset,"all_records_count":len(all_records),"page_records_count":len(page_records)},"timestamp":int(datetime.now().timestamp()*1000)})
                # #endregion
                break

            # Continue to next page
            offset += PAGE_SIZE
            logger.info(f"[OpenCanada] Continuing to next page: offset={offset}, current_total={len(all_records)}")
            await asyncio.sleep(COURTESY_DELAY_S)

        # Final trim to cap (in case last page pushed us over)
        if max_records and len(all_records) > max_records:
            all_records = all_records[:max_records]

        logger.info(
            f"[OpenCanada] Fetch complete — {len(all_records)} records "
            f"(pages={page_num}, min_date={min_date})"
        )
        # #region agent log
        _safe_debug_log({"runId":"debug","hypothesisId":"A","location":"open_canada.py:237","message":"Adapter fetch_grants completed","data":{"total_records":len(all_records),"max_records":max_records,"min_date":min_date.isoformat() if min_date else None},"timestamp":int(datetime.now().timestamp()*1000)})
        # #endregion
        return all_records

    # ------------------------------------------------------------------
    # Backward-compatible entry point used by the orchestrator
    # ------------------------------------------------------------------
    async def fetch_all(
        self,
        mode: str = "datastore",
        min_date: str = "2025-01-01",
        max_records: Optional[int] = 5000,
        **_kwargs,
    ) -> List[RawGrantRecord]:
        """
        Unified entry point. The *mode* parameter is kept for backward
        compatibility but ignored — we always use the datastore strategy.
        Extra kwargs (year_filter, since_date) are silently ignored.
        """
        return await self.fetch_grants(
            min_date=min_date,
            max_records=max_records,
        )

    # ------------------------------------------------------------------
    # Record parsing (datastore column names)
    # ------------------------------------------------------------------
    def _parse_datastore_record(
        self, row: Dict[str, Any]
    ) -> Optional[RawGrantRecord]:
        """
        Map one datastore_search record → RawGrantRecord.
        Returns None for completely unusable rows.
        """
        try:
            recipient_name = row.get("recipient_legal_name") or ""
            recipient_name = recipient_name.strip()
            if not recipient_name:
                return None

            # Amount
            amount_raw = row.get("agreement_value")
            amount_cad = None
            if amount_raw is not None and str(amount_raw).strip():
                try:
                    amount_cad = float(amount_raw)
                except (ValueError, TypeError):
                    pass

            # Description: combine description, program purpose, expected results
            parts = []
            if row.get("description_en"):
                parts.append(str(row["description_en"]))
            if row.get("prog_purpose_en"):
                parts.append(f"Program Purpose: {row['prog_purpose_en']}")
            if row.get("expected_results_en"):
                parts.append(f"Expected Results: {row['expected_results_en']}")
            description = "\n\n".join(parts) if parts else None

            # Issuer: owner_org_title is bilingual "English | French"
            issuer_raw = row.get("owner_org_title") or ""
            if "|" in issuer_raw:
                issuer_raw = issuer_raw.split("|")[0].strip()

            # Region
            region_raw = row.get("recipient_province")

            # Award date
            award_date_raw = row.get("agreement_start_date")

            # Source record ID
            source_record_id = row.get("ref_number")
            if source_record_id:
                source_record_id = str(source_record_id).strip()

            # Program name
            program_name = row.get("prog_name_en")

            # Raw data for later use (includes all fields for 6-dimension scoring)
            raw_data = {
                "agreement_number": row.get("agreement_number"),
                "agreement_type": row.get("agreement_type"),
                "naics_code": row.get("naics_identifier"),
                "agreement_title": row.get("agreement_title_en"),
                "recipient_type_raw": row.get("recipient_type"),
                "recipient_business_number": row.get("recipient_business_number"),
                "recipient_city": row.get("recipient_city"),
                "recipient_country": row.get("recipient_country"),
                "recipient_postal_code": row.get("recipient_postal_code"),
                "recipient_operating_name": row.get("recipient_operating_name"),
                "research_organization": row.get("research_organization_name"),
                "agreement_start_date": row.get("agreement_start_date"),
                "agreement_end_date": row.get("agreement_end_date"),
                "coverage": row.get("coverage"),
                "federal_riding": row.get("federal_riding_name_en"),
                "additional_info": row.get("additional_information_en"),
                "amendment_number": row.get("amendment_number"),
                "amendment_date": row.get("amendment_date"),
                "owner_org": row.get("owner_org"),
            }
            # Strip None values to keep raw_data compact
            raw_data = {k: v for k, v in raw_data.items() if v is not None}

            return RawGrantRecord(
                source="open_canada",
                source_record_id=source_record_id,
                issuer_raw=issuer_raw,
                recipient_name=recipient_name,
                amount_raw=str(amount_raw) if amount_raw is not None else None,
                amount_cad=amount_cad,
                award_date_raw=award_date_raw,
                description=description,
                region_raw=region_raw,
                program_name=program_name,
                raw_data=raw_data,
                fetch_errors=[],
            )

        except Exception as e:
            logger.warning(f"Error parsing datastore record: {e}")
            return None
