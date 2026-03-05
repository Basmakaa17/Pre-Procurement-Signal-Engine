"""
CSV File Adapter for processing grant records from CSV files
"""
import asyncio
import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.models.raw_grant import RawGrantRecord

logger = logging.getLogger(__name__)

class CSVFileAdapter:
    """
    Adapter for processing grant records from CSV files
    """
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    async def fetch_all(self, year_filter: Optional[int] = None) -> List[RawGrantRecord]:
        """
        Process the CSV file and return a list of RawGrantRecord objects
        
        Args:
            year_filter: Optional filter to only include grants from a specific year
            
        Returns:
            List of RawGrantRecord objects
        """
        logger.info(f"Processing CSV file: {self.file_path}")
        
        try:
            # Try UTF-8 first, fallback to latin-1
            try:
                df = pd.read_csv(self.file_path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(self.file_path, encoding="latin-1")
            
            logger.info(f"Loaded {len(df)} rows from CSV")
            
            # Apply year filter if specified
            if year_filter:
                # Check which column contains year information
                year_col = None
                if 'Calendar Year' in df.columns:
                    year_col = 'Calendar Year'
                elif 'Agreement Start Date' in df.columns:
                    # Extract year from date
                    df['Year'] = pd.to_datetime(df['Agreement Start Date'], errors='coerce').dt.year
                    year_col = 'Year'
                
                if year_col:
                    original_count = len(df)
                    df = df[df[year_col] == year_filter]
                    logger.info(f"Filtered to {len(df)} records for year {year_filter} (skipped {original_count - len(df)})")
                else:
                    logger.warning(f"Year filter specified but no suitable column found for filtering")
            
            # Process each row
            records = []
            for _, row in df.iterrows():
                record = self._parse_record(row.to_dict())
                if record:
                    records.append(record)
            
            logger.info(f"Successfully processed {len(records)} valid records from CSV")
            return records
            
        except Exception as e:
            logger.error(f"Error processing CSV file: {e}", exc_info=True)
            return []
    
    def _parse_record(self, row: Dict[str, Any]) -> Optional[RawGrantRecord]:
        """
        Parse a row from the CSV into a RawGrantRecord
        
        Args:
            row: Dictionary representing a row from the CSV
            
        Returns:
            RawGrantRecord object or None if parsing failed
        """
        try:
            # Extract recipient name, handling potential French translation
            recipient_name = str(row.get('Recipient Legal Name (English|French)', ''))
            if recipient_name and '|' in recipient_name:
                recipient_name = recipient_name.split('|')[0].strip()
            
            # Extract issuer name
            issuer_raw = str(row.get('Organization', ''))
            
            # Extract amount
            amount_raw = str(row.get('Agreement Value in CAD', ''))
            amount_cad = None
            try:
                if pd.notna(row.get('Agreement Value in CAD')):
                    amount_cad = float(row['Agreement Value in CAD'])
            except (ValueError, TypeError):
                pass
            
            # Extract date
            award_date_raw = None
            if pd.notna(row.get('Agreement Start Date')):
                award_date_raw = str(row['Agreement Start Date'])
            
            # Extract description
            description = None
            if pd.notna(row.get('Description (English)')):
                description = str(row['Description (English)'])
            
            # Extract region
            region_raw = None
            if pd.notna(row.get('Recipient Province or Territory')):
                region_raw = str(row['Recipient Province or Territory'])
            
            # Extract program name
            program_name = None
            if pd.notna(row.get('Program Name (English)')):
                program_name = str(row['Program Name (English)'])
            
            # Generate a source record ID
            source_record_id = None
            if pd.notna(row.get('Reference Number')):
                source_record_id = str(row['Reference Number'])
            
            # Store additional raw data
            raw_data = {
                # Store original columns that might be useful later
                'recipient_type': str(row.get('Recipient Type', '')) if pd.notna(row.get('Recipient Type')) else None,
                'fiscal_year': str(row.get('fiscal_year', '')) if pd.notna(row.get('fiscal_year')) else None,
                'agreement_number': str(row.get('Agreement Number', '')) if pd.notna(row.get('Agreement Number')) else None,
                'calendar_year': str(row.get('Calendar Year', '')) if pd.notna(row.get('Calendar Year')) else None,
                'recipient_business_number': str(row.get('Recipient Business Number', '')) if pd.notna(row.get('Recipient Business Number')) else None,
                'recipient_city': str(row.get('Recipient City (English|French)', '')) if pd.notna(row.get('Recipient City (English|French)')) else None,
            }

            # Basic validation for essential fields
            if not recipient_name or not issuer_raw or amount_cad is None:
                logger.warning(f"Skipping record due to missing essential data: Recipient='{recipient_name}', Issuer='{issuer_raw}', Amount='{amount_cad}'")
                return None

            return RawGrantRecord(
                source="csv_file",
                source_record_id=source_record_id,
                issuer_raw=issuer_raw,
                recipient_name=recipient_name,
                amount_raw=amount_raw,
                amount_cad=amount_cad,
                award_date_raw=award_date_raw,
                description=description,
                region_raw=region_raw,
                program_name=program_name,
                raw_data=raw_data,
                fetch_errors=[]
            )
            
        except Exception as e:
            logger.error(f"Error parsing record: {e}")
            return None

