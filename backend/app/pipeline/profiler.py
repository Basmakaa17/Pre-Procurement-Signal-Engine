"""
Data Profiler for Pipeline
Analyzes raw grant records before cleaning to provide data quality insights
"""
import logging
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
from app.models.raw_grant import RawGrantRecord

logger = logging.getLogger(__name__)


async def profile_raw(records: list[RawGrantRecord]) -> dict:
    """
    Profile raw grant records before cleaning
    
    Args:
        records: List of RawGrantRecord objects
    
    Returns:
        Dictionary with profiling statistics
    """
    if not records:
        logger.warning("No records to profile")
        return {
            "record_count": 0,
            "fields": {},
            "summary": "No records to profile"
        }
    
    logger.info(f"Profiling {len(records)} raw grant records")
    
    # Convert to DataFrame for easier analysis
    data = []
    for record in records:
        data.append({
            "source": record.source,
            "source_record_id": record.source_record_id,
            "issuer_raw": record.issuer_raw,
            "recipient_name": record.recipient_name,
            "amount_raw": record.amount_raw,
            "amount_cad": record.amount_cad,
            "award_date_raw": record.award_date_raw,
            "description": record.description,
            "region_raw": record.region_raw,
            "program_name": record.program_name
        })
    
    df = pd.DataFrame(data)
    
    # Basic stats
    record_count = len(df)
    field_count = len(df.columns)
    
    # Calculate null rates per column
    null_counts = df.isna().sum().to_dict()
    null_rates = {col: count / record_count for col, count in null_counts.items()}
    
    # Sort null rates by descending rate
    sorted_null_rates = dict(sorted(null_rates.items(), key=lambda x: x[1], reverse=True))
    
    # Unique value counts for categorical fields
    categorical_fields = ["source", "issuer_raw", "region_raw", "program_name"]
    unique_values = {}
    for field in categorical_fields:
        if field in df.columns:
            # Get top 10 most common values
            value_counts = df[field].value_counts().head(10).to_dict()
            unique_values[field] = value_counts
    
    # Sample raw values for amount and date fields
    amount_samples = df["amount_raw"].dropna().sample(min(5, df["amount_raw"].count())).tolist()
    date_samples = df["award_date_raw"].dropna().sample(min(5, df["award_date_raw"].count())).tolist()
    
    # Build profiling report
    report = {
        "record_count": record_count,
        "field_count": field_count,
        "null_rates": sorted_null_rates,
        "categorical_fields": unique_values,
        "amount_samples": amount_samples,
        "date_samples": date_samples
    }
    
    # Generate human-readable summary
    summary_lines = [
        f"Data Profiling Report for {len(records)} Records",
        f"--------------------------------",
        f"Record Count: {record_count}",
        f"Field Count: {field_count}",
        f"",
        f"Null Rates (Descending):",
    ]
    
    for field, rate in sorted_null_rates.items():
        summary_lines.append(f"  {field}: {rate:.2%}")
    
    summary_lines.append("")
    summary_lines.append("Categorical Field Value Counts:")
    
    for field, counts in unique_values.items():
        summary_lines.append(f"  {field}:")
        for value, count in counts.items():
            summary_lines.append(f"    {value}: {count}")
    
    summary_lines.append("")
    summary_lines.append("Amount Format Samples:")
    for sample in amount_samples:
        summary_lines.append(f"  {sample}")
    
    summary_lines.append("")
    summary_lines.append("Date Format Samples:")
    for sample in date_samples:
        summary_lines.append(f"  {sample}")
    
    report["summary"] = "\n".join(summary_lines)
    
    # Print summary to console
    print(report["summary"])
    
    return report


def print_profiling_report(report: dict) -> None:
    """Print a profiling report in a formatted way"""
    if "summary" in report:
        print(report["summary"])
    else:
        print("No summary available in profiling report")