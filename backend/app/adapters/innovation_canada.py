"""
Innovation Canada Benefits Finder API adapter
Fetches program information from Innovation Canada's public API
"""
from typing import Optional

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.models.raw_grant import RawGrantRecord


class InnovationCanadaAdapter:
    """Adapter for fetching program records from Innovation Canada API"""
    
    BASE_URL = "https://api.canada.ca/en/boundless-benefits-finder/benefits"
    
    def __init__(self, http_client: httpx.AsyncClient):
        self.client = http_client
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    async def fetch_page(self, page: int, page_size: int = 20) -> dict:
        """
        Fetch a single page of program records from Innovation Canada API
        
        Args:
            page: Page number to fetch (1-indexed)
            page_size: Number of records per page
            
        Returns:
            Raw JSON response from the API
        """
        url = f"{self.BASE_URL}?lang=en&sortBy=relevance&page={page}&pageSize={page_size}"
        
        headers = {
            "User-Agent": "PublicusSignalEngine/1.0 (research prototype)"
        }
        
        try:
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise httpx.HTTPError(f"Failed to fetch page {page}: {e}")
    
    async def fetch_all(self, max_pages: int = 20) -> list[RawGrantRecord]:
        """
        Fetch all program records from Innovation Canada API
        
        Args:
            max_pages: Maximum number of pages to fetch
            
        Returns:
            List of RawGrantRecord objects
        """
        all_records = []
        page = 1
        
        while page <= max_pages:
            try:
                data = await self.fetch_page(page)
                
                # Extract records from response
                records = []
                if isinstance(data, dict):
                    if "data" in data:
                        records = data["data"]
                    elif "results" in data:
                        records = data["results"]
                    elif isinstance(data.get("result"), list):
                        records = data["result"]
                elif isinstance(data, list):
                    records = data
                
                for record in records:
                    try:
                        parsed = self._parse_record(record)
                        all_records.append(parsed)
                    except Exception as e:
                        # Log parse error but continue with other records
                        error_msg = f"Failed to parse record: {str(e)}"
                        print(f"  ⚠️  {error_msg}")
                        continue
                
                print(f"Fetched page {page}, {len(all_records)} records total")
                
                # Check if there are more pages
                if len(records) == 0:
                    break
                    
                page += 1
                
            except httpx.HTTPError as e:
                print(f"  ❌ Error fetching page {page}: {e}")
                break
            except Exception as e:
                print(f"  ❌ Unexpected error on page {page}: {e}")
                break
        
        return all_records
    
    def _parse_record(self, raw: dict) -> RawGrantRecord:
        """
        Parse a raw Innovation Canada record into RawGrantRecord
        
        Args:
            raw: Raw JSON record from Innovation Canada API
            
        Returns:
            RawGrantRecord object
        """
        # Extract provider name
        provider = raw.get("provider", {})
        if isinstance(provider, dict):
            issuer_raw = provider.get("name")
        else:
            issuer_raw = str(provider) if provider else None
        
        # These are programs, not individual awards
        recipient_name = "Eligible Businesses"
        
        # Description can come from description or title
        description = raw.get("description") or raw.get("title")
        
        # Program name is the title
        program_name = raw.get("title")
        
        # Source record ID
        source_record_id = str(raw.get("id")) if raw.get("id") is not None else None
        
        return RawGrantRecord(
            source="innovation_canada",
            source_record_id=source_record_id,
            issuer_raw=issuer_raw,
            recipient_name=recipient_name,
            amount_raw=None,  # Programs don't have specific amounts
            amount_cad=None,
            award_date_raw=None,  # Programs don't have award dates
            description=description,
            region_raw=None,
            program_name=program_name,
            raw_data=raw,
            fetch_errors=[],
        )


async def test():
    """Test function for InnovationCanadaAdapter"""
    async with httpx.AsyncClient(timeout=30) as client:
        adapter = InnovationCanadaAdapter(client)
        records = await adapter.fetch_all(max_pages=2)
        print(f"Fetched {len(records)} records")
        if records:
            print(records[0].model_dump())


if __name__ == "__main__":
    import asyncio
    
    asyncio.run(test())
