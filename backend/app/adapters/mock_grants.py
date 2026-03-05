"""
Mock adapter for generating realistic grant data
Used for testing when the real data source is unavailable
"""
import asyncio
import random
from datetime import datetime, timedelta, date
from typing import List, Optional

import httpx

from app.models.raw_grant import RawGrantRecord


class MockGrantsAdapter:
    """
    Generates realistic mock grant data for testing
    """
    
    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        self.http_client = http_client  # Not used, but kept for API compatibility
    
    async def fetch_all(
        self,
        count: int = 50,
        year_filter: Optional[int] = None,
        since_date: Optional[date] = None
    ) -> List[RawGrantRecord]:
        """
        Generate mock grant records
        
        Args:
            count: Number of records to generate
            year_filter: Only generate grants for this year
            since_date: Only generate grants since this date
            
        Returns:
            List of RawGrantRecord objects
        """
        print(f"[MockData] Generating {count} sample grant records...")
        
        # Use current year if not specified
        if not year_filter:
            year_filter = datetime.now().year
        
        # Use organizations from real data
        organizations = [
            "Natural Sciences and Engineering Research Council of Canada",
            "Innovation, Science and Economic Development Canada",
            "Canadian Institutes of Health Research",
            "Social Sciences and Humanities Research Council",
            "National Research Council Canada",
            "Agriculture and Agri-Food Canada",
            "Environment and Climate Change Canada",
            "Department of National Defence",
            "Health Canada",
            "Transport Canada"
        ]
        
        # Use realistic recipient types
        recipient_types = [
            "University",
            "Research Institute",
            "Non-profit Organization",
            "Private Company",
            "Municipality",
            "Provincial Government",
            "Indigenous Organization",
            "Hospital",
            "Individual"
        ]
        
        # Use realistic recipient names
        recipient_templates = [
            "{} University",
            "{} College",
            "{} Institute",
            "{} Research Center",
            "{} Technologies Inc.",
            "{} Solutions",
            "City of {}",
            "{} Hospital",
            "{} Foundation",
            "{} Association"
        ]
        
        # Cities for recipient names
        cities = [
            "Toronto", "Montreal", "Vancouver", "Calgary", "Edmonton",
            "Ottawa", "Winnipeg", "Quebec City", "Halifax", "Victoria",
            "Saskatoon", "Regina", "St. John's", "Fredericton", "Charlottetown"
        ]
        
        # Provinces
        provinces = [
            "Ontario", "Quebec", "British Columbia", "Alberta", "Manitoba",
            "Saskatchewan", "Nova Scotia", "New Brunswick", "Newfoundland and Labrador",
            "Prince Edward Island", "Northwest Territories", "Yukon", "Nunavut"
        ]
        
        # Program names
        program_templates = [
            "Strategic {} Initiative",
            "{} Research Program",
            "{} Innovation Fund",
            "Advanced {} Grant",
            "{} Development Project",
            "Sustainable {} Program",
            "{} Excellence Funding",
            "{} Capacity Building",
            "{} Infrastructure Support",
            "Next Generation {} Initiative"
        ]
        
        # Fields for program names
        fields = [
            "Technology", "Science", "Research", "Innovation", "Digital",
            "Healthcare", "Climate", "Energy", "Agriculture", "Transportation",
            "Education", "Infrastructure", "Manufacturing", "Biotechnology", "AI"
        ]
        
        records = []
        
        # Generate records
        for i in range(count):
            # Generate date within the specified year or since the since_date
            if since_date:
                days_since = (datetime.now().date() - since_date).days
                days_ago = random.randint(0, max(0, days_since))
                award_date = datetime.now().date() - timedelta(days=days_ago)
            else:
                # Generate a date in the specified year
                year = year_filter or datetime.now().year
                month = random.randint(1, 12)
                day = random.randint(1, 28)  # Avoid month boundary issues
                award_date = date(year, month, day)
            
            # Format the date
            award_date_str = award_date.strftime("%Y-%m-%d")
            
            # Generate amount (realistic for grants)
            amount_category = random.choices(
                ["small", "medium", "large", "very_large"],
                weights=[0.4, 0.3, 0.2, 0.1]
            )[0]
            
            if amount_category == "small":
                amount = random.randint(5000, 50000)
            elif amount_category == "medium":
                amount = random.randint(50001, 250000)
            elif amount_category == "large":
                amount = random.randint(250001, 1000000)
            else:  # very_large
                amount = random.randint(1000001, 5000000)
            
            # Format amount with dollar sign and commas
            amount_str = f"${amount:,}"
            
            # Generate recipient name
            city = random.choice(cities)
            template = random.choice(recipient_templates)
            recipient_name = template.format(city)
            
            # Generate issuer
            issuer = random.choice(organizations)
            
            # Generate program name
            field = random.choice(fields)
            program_template = random.choice(program_templates)
            program_name = program_template.format(field)
            
            # Generate region
            region = random.choice(provinces)
            
            # Generate description (more realistic for grants)
            descriptions = [
                f"Funding to support {field.lower()} research and development activities focused on sustainable solutions.",
                f"Grant to advance {field.lower()} innovation through collaborative partnerships with industry and academia.",
                f"Support for {field.lower()} infrastructure development to enhance research capabilities and outcomes.",
                f"Funding to promote {field.lower()} education and training programs for the next generation of researchers.",
                f"Grant to establish a center of excellence in {field.lower()} research and innovation.",
                f"Support for {field.lower()} knowledge mobilization and technology transfer activities.",
                f"Funding to enhance {field.lower()} capacity and capabilities in underrepresented communities.",
                f"Grant to develop new {field.lower()} applications and methodologies for addressing societal challenges.",
                f"Support for {field.lower()} commercialization activities to bring research outcomes to market.",
                f"Funding for collaborative {field.lower()} projects involving multiple stakeholders and sectors."
            ]
            description = random.choice(descriptions)
            
            # Generate a stable ID
            source_id = f"mock-{year_filter}-{i:04d}"
            
            # Create the record
            record = RawGrantRecord(
                source="open_canada",
                source_record_id=source_id,
                issuer_raw=issuer,
                recipient_name=recipient_name,
                amount_raw=amount_str,
                amount_cad=float(amount),
                award_date_raw=award_date_str,
                description=description,
                region_raw=region,
                program_name=program_name,
                raw_data={
                    "recipient_type": random.choice(recipient_types),
                    "fiscal_year": f"{award_date.year}/{award_date.year + 1}",
                    "agreement_number": f"AGR-{award_date.year}-{random.randint(10000, 99999)}",
                    "calendar_year": str(award_date.year),
                },
                fetch_errors=[],
            )
            
            records.append(record)
        
        print(f"  ✓ Generated {len(records)} mock grant records")
        return records


async def test():
    """Test the mock adapter"""
    adapter = MockGrantsAdapter()
    
    # Test generating grants for current year
    current_year = datetime.now().year
    records = await adapter.fetch_all(count=20, year_filter=current_year)
    
    print(f"Generated {len(records)} mock records for {current_year}")
    
    if records:
        print("\nSample record:")
        sample = records[0]
        print(f"  Source: {sample.source}")
        print(f"  ID: {sample.source_record_id}")
        print(f"  Recipient: {sample.recipient_name}")
        print(f"  Issuer: {sample.issuer_raw}")
        print(f"  Amount: {sample.amount_raw} (${sample.amount_cad})")
        print(f"  Date: {sample.award_date_raw}")
        print(f"  Description: {sample.description}")
        print(f"  Region: {sample.region_raw}")
        print(f"  Program: {sample.program_name}")
        print(f"  Raw Data: {sample.raw_data}")


if __name__ == "__main__":
    asyncio.run(test())