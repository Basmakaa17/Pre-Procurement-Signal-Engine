"""
Database client for Supabase PostgreSQL
All database operations must go through this client
"""
import os
from typing import Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions


def get_supabase_client() -> Client:
    """
    Create and return Supabase client using dependency injection pattern
    Never instantiate Supabase client inline - always use this function
    """
    # Load environment variables
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    load_dotenv(env_path)
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not supabase_url:
        raise ValueError("SUPABASE_URL not found in .env file")
    if not supabase_service_key:
        raise ValueError("SUPABASE_SERVICE_KEY not found in .env file")
    
    # Create client without custom options to avoid compatibility issues
    return create_client(supabase_url, supabase_service_key)
