"""
Database client for Supabase PostgreSQL
All database operations must go through this client
"""
import os
from typing import Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """
    Create and return Supabase client using dependency injection pattern
    Never instantiate Supabase client inline - always use this function
    """
    # Load .env from backend root if present (local); Railway/production use process env
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    load_dotenv(env_path)
    load_dotenv()  # also load from current working directory

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url:
        raise ValueError(
            "SUPABASE_URL is not set. "
            "Local: add SUPABASE_URL to backend/.env. "
            "Railway: add SUPABASE_URL in your service → Variables."
        )
    if not supabase_service_key:
        raise ValueError(
            "SUPABASE_SERVICE_KEY is not set. "
            "Local: add to backend/.env. "
            "Railway: add SUPABASE_SERVICE_KEY in your service → Variables."
        )
    
    # Create client without custom options to avoid compatibility issues
    return create_client(supabase_url, supabase_service_key)
