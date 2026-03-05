"""
Proactive Disclosure of Grants and Contributions adapter
Fetches grant records from federal Proactive Disclosure CSV datasets
"""
import io
from typing import Optional

import httpx
import pandas as pd
from rapidfuzz import fuzz
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.models.raw_grant import RawGrantRecord


class ProactiveDisclosureAdapter:
    """Adapter for fetching grant records from Proactive Disclosure CSV datasets"""
    
    DATASET_ID = "432527ab-7aac-45b5-81d6-7597107a7013"
    API_BASE = "https://open.canada.ca/api/3/action"
    
    def __init__(self, http_client: httpx.AsyncClient):
        self.client = http_client
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    async def _fetch_dataset_info(self) -> dict:
        """
        Fetch dataset information from Open Canada API
        
        Returns:
            Dataset metadata including resource URLs
        """
        url = f"{self.API_BASE}/package_show?id={self.DATASET_ID}"
        
        headers = {
            "User-Agent": "PublicusSignalEngine/1.0 (research prototype)"
        }
        
        try:
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise httpx.HTTPError(f"Failed to fetch dataset info: {e}")
    
    def _find_csv_resource(self, dataset_info: dict) -> Optional[str]:
        """
        Find the most recent English CSV resource URL
        
        Args:
            dataset_info: Dataset metadata from API
            
        Returns:
            URL of the most recent CSV resource, or None if not found
        """
        result = dataset_info.get("result", {})
        resources = result.get("resources", [])
        
        csv_resources = []
        for resource in resources:
            format_type = resource.get("format", "").upper()
            language = resource.get("language", "").lower()
            
            # Look for CSV or XLSX files in English
            if format_type in ["CSV", "XLSX", "XLS"] and language in ["en", "eng", "english", ""]:
                csv_resources.append(resource)
        
        if not csv_resources:
            return None
        
        # Sort by last_modified (most recent first)
        csv_resources.sort(
            key=lambda x: x.get("last_modified", ""),
            reverse=True
        )
        
        # Prefer CSV over XLSX
        csv_url = None
        for resource in csv_resources:
            if resource.get("format", "").upper() == "CSV":
                csv_url = resource.get("url")
                break
        
        # If no CSV, use the first resource (XLSX)
        if not csv_url and csv_resources:
            csv_url = csv_resources[0].get("url")
        
        return csv_url
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    async def _download_csv(self, csv_url: str) -> bytes:
        """
        Download CSV file content
        
        Args:
            csv_url: URL of the CSV resource
            
        Returns:
            CSV file content as bytes
        """
        headers = {
            "User-Agent": "PublicusSignalEngine/1.0 (research prototype)"
        }
        
        try:
            async with self.client.stream("GET", csv_url, headers=headers) as response:
                response.raise_for_status()
                content = b""
                async for chunk in response.aiter_bytes():
                    content += chunk
                return content
        except httpx.HTTPError as e:
            raise httpx.HTTPError(f"Failed to download CSV: {e}")
    
    def _fuzzy_column_match(self, column_name: str, target_names: list[str]) -> Optional[str]:
        """
        Find the best matching column name using fuzzy matching
        
        Args:
            column_name: Target column name to find
            target_names: List of actual column names in the CSV
            
        Returns:
            Best matching column name, or None if no good match
        """
        best_match = None
        best_score = 0
        
        for target in target_names:
            # Use token_sort_ratio for better matching of column names
            score = fuzz.token_sort_ratio(column_name.lower(), target.lower())
            if score > best_score and score >= 80:  # 80% similarity threshold
                best_score = score
                best_match = target
        
        return best_match
    
    def _parse_dataframe(self, df: pd.DataFrame) -> list[RawGrantRecord]:
        """
        Parse pandas DataFrame into RawGrantRecord objects
        
        Args:
            df: DataFrame containing grant records
            
        Returns:
            List of RawGrantRecord objects
        """
        records = []
        column_names = df.columns.tolist()
        
        # Map expected column names to actual column names using fuzzy matching
        column_map = {}
        expected_columns = {
            "recipient_name": ["legal_name", "recipient_legal_name", "recipient_name", "recipient"],
            "amount_raw": ["agreement_value", "amendment_value", "value", "amount"],
            "award_date_raw": ["agreement_start_date", "award_date", "start_date", "date"],
            "issuer_raw": ["federal_organization", "owner_org", "organization", "issuer"],
            "region_raw": ["province_territory", "province", "region", "territory"],
            "description": ["description_en", "description", "description_fr"],
        }
        
        for expected, alternatives in expected_columns.items():
            # Try exact match first (case-insensitive)
            found = None
            for alt in alternatives:
                for col in column_names:
                    if col.lower() == alt.lower():
                        found = col
                        break
                if found:
                    break
            
            # If not found, try fuzzy matching
            if not found:
                for alt in alternatives:
                    found = self._fuzzy_column_match(alt, column_names)
                    if found:
                        break
            
            if found:
                column_map[expected] = found
        
        # Parse each row
        for idx, row in df.iterrows():
            try:
                # Extract values using column mapping
                recipient_name = None
                if "recipient_name" in column_map:
                    recipient_name = row.get(column_map["recipient_name"])
                    if pd.isna(recipient_name):
                        recipient_name = None
                    else:
                        recipient_name = str(recipient_name)
                
                amount_raw = None
                amount_cad = None
                if "amount_raw" in column_map:
                    amount_raw = row.get(column_map["amount_raw"])
                    if not pd.isna(amount_raw):
                        amount_raw = str(amount_raw)
                        try:
                            # Try to parse as float
                            cleaned = str(amount_raw).replace("$", "").replace(",", "").strip()
                            amount_cad = float(cleaned) if cleaned else None
                        except (ValueError, TypeError):
                            pass
                
                award_date_raw = None
                if "award_date_raw" in column_map:
                    award_date_raw = row.get(column_map["award_date_raw"])
                    if not pd.isna(award_date_raw):
                        award_date_raw = str(award_date_raw)
                
                issuer_raw = None
                if "issuer_raw" in column_map:
                    issuer_raw = row.get(column_map["issuer_raw"])
                    if not pd.isna(issuer_raw):
                        issuer_raw = str(issuer_raw)
                
                region_raw = None
                if "region_raw" in column_map:
                    region_raw = row.get(column_map["region_raw"])
                    if not pd.isna(region_raw):
                        region_raw = str(region_raw)
                
                description = None
                if "description" in column_map:
                    description = row.get(column_map["description"])
                    if not pd.isna(description):
                        description = str(description)
                
                # Create raw_data dict from the row
                raw_data = row.to_dict()
                
                # Generate source_record_id from index or row data
                source_record_id = str(idx)
                if "id" in column_names:
                    id_val = row.get("id")
                    if not pd.isna(id_val):
                        source_record_id = str(id_val)
                
                record = RawGrantRecord(
                    source="proactive_disclosure",
                    source_record_id=source_record_id,
                    issuer_raw=issuer_raw,
                    recipient_name=recipient_name,
                    amount_raw=amount_raw,
                    amount_cad=amount_cad,
                    award_date_raw=award_date_raw,
                    description=description,
                    region_raw=region_raw,
                    program_name=None,
                    raw_data=raw_data,
                    fetch_errors=[],
                )
                
                records.append(record)
                
            except Exception as e:
                # Log parse error but continue
                error_msg = f"Failed to parse row {idx}: {str(e)}"
                print(f"  ⚠️  {error_msg}")
                continue
        
        return records
    
    async def fetch_all(self) -> list[RawGrantRecord]:
        """
        Fetch all grant records from Proactive Disclosure dataset
        
        Returns:
            List of RawGrantRecord objects (limited to 1000 for prototype)
        """
        print("📋 Step 1: Fetching dataset information...")
        try:
            dataset_info = await self._fetch_dataset_info()
            print("✅ Dataset info retrieved")
        except Exception as e:
            print(f"❌ Failed to fetch dataset info: {e}")
            return []
        
        print("📋 Step 2: Finding CSV resource URL...")
        csv_url = self._find_csv_resource(dataset_info)
        if not csv_url:
            print("❌ No CSV resource found in dataset")
            return []
        print(f"✅ Found CSV resource: {csv_url}")
        
        print("📋 Step 3: Downloading CSV file...")
        try:
            csv_content = await self._download_csv(csv_url)
            print(f"✅ Downloaded {len(csv_content)} bytes")
        except Exception as e:
            print(f"❌ Failed to download CSV: {e}")
            return []
        
        print("📋 Step 4: Parsing CSV with pandas...")
        try:
            # Try UTF-8 first, fallback to latin-1
            try:
                df = pd.read_csv(io.BytesIO(csv_content), encoding="utf-8")
                print("✅ Parsed CSV with UTF-8 encoding")
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(csv_content), encoding="latin-1")
                print("✅ Parsed CSV with latin-1 encoding (fallback)")
        except Exception as e:
            print(f"❌ Failed to parse CSV: {e}")
            return []
        
        print(f"📊 Found {len(df)} rows in CSV")
        
        print("📋 Step 5: Mapping columns and parsing records...")
        # Limit to 1000 rows for prototype
        df_limited = df.head(1000)
        records = self._parse_dataframe(df_limited)
        
        print(f"✅ Parsed {len(records)} records")
        
        return records


async def test():
    """Test function for ProactiveDisclosureAdapter"""
    async with httpx.AsyncClient(timeout=60) as client:
        adapter = ProactiveDisclosureAdapter(client)
        records = await adapter.fetch_all()
        print(f"Fetched {len(records)} records")
        if records:
            print(records[0].model_dump())


if __name__ == "__main__":
    import asyncio
    
    asyncio.run(test())
