"""
LLM Classification Engine
Supports multiple LLM providers: Anthropic Claude, Groq, OpenAI, Gemini
"""
import asyncio
import hashlib
import json
import logging
import os
from typing import Optional

from dotenv import load_dotenv

from app.database.client import get_supabase_client
from app.models.cleaned_grant import CleanedGrantRecord
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClassificationResult(BaseModel):
    """Result of LLM classification for a grant record"""
    
    grant_id: str
    funding_theme: str
    procurement_category: str
    sector_tags: list[str]
    confidence: float
    reasoning: str
    needs_review: bool
    classification_flags: list[str]


class GrantClassifier:
    """Classifies grant records using Anthropic Claude API"""
    
    def __init__(self):
        # Load environment
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        load_dotenv(env_path)
        
        # Determine which LLM provider to use
        self.provider = os.getenv("LLM_PROVIDER", "groq").lower()  # Default to Groq (free)
        
        # Initialize provider-specific client
        if self.provider == "groq":
            try:
                from groq import Groq
                api_key = os.getenv("GROQ_API_KEY")
                if not api_key:
                    raise ValueError("GROQ_API_KEY not found in .env file")
                self.client = Groq(api_key=api_key)
                self.model = "llama-3.1-8b-instant"  # Fast, free model (updated from deprecated model)
            except ImportError:
                raise ImportError("groq package not installed. Run: pip install groq")
        elif self.provider == "openai":
            try:
                from openai import OpenAI
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not found in .env file")
                self.client = OpenAI(api_key=api_key)
                self.model = "gpt-3.5-turbo"  # Cheaper model for demo
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        elif self.provider == "gemini":
            try:
                import google.generativeai as genai
                api_key = os.getenv("GEMINI_API_KEY")
                if not api_key:
                    raise ValueError("GEMINI_API_KEY not found in .env file")
                genai.configure(api_key=api_key)
                self.client = genai
                self.model = "gemini-pro"
            except ImportError:
                raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")
        elif self.provider == "anthropic":
            try:
                import anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY not found in .env file")
                self.client = anthropic.Anthropic(api_key=api_key)
                self.model = "claude-3-haiku-20240307"  # Cheaper Claude model
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}. Use: groq, openai, gemini, or anthropic")
        
        self.cache: dict[str, ClassificationResult] = {}
        
        # Load taxonomy from Supabase
        self._load_taxonomy()
        
        # Build valid themes and categories
        self.valid_themes = list(set(row["grant_theme"] for row in self.taxonomy_map.values()))
        self.valid_categories = list(set(row["procurement_category"] for row in self.taxonomy_map.values()))
        
        logger.info(f"[CLASSIFIER] Using LLM provider: {self.provider} with model: {self.model}")
    
    def _load_taxonomy(self):
        """Load procurement taxonomy from Supabase"""
        try:
            supabase = get_supabase_client()
            response = supabase.table("procurement_taxonomy").select("*").execute()
            
            # Build taxonomy map: grant_theme -> full taxonomy row
            self.taxonomy_map = {}
            for row in response.data:
                theme = row["grant_theme"]
                self.taxonomy_map[theme] = {
                    "grant_theme": row["grant_theme"],
                    "procurement_category": row["procurement_category"],
                    "lag_months_min": row["lag_months_min"],
                    "lag_months_max": row["lag_months_max"],
                    "confidence_base": float(row["confidence_base"]) if row["confidence_base"] else 0.75,
                    "notes": row.get("notes", ""),
                }
            
            logger.info(f"Loaded {len(self.taxonomy_map)} taxonomy entries")
            
        except Exception as e:
            logger.error(f"Failed to load taxonomy: {e}")
            raise
    
    def _cache_key(self, text: str) -> str:
        """Generate SHA256 hash cache key from text"""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    
    def _build_prompt(self, grants: list[dict]) -> str:
        """
        Build the classification prompt for Claude API
        
        Args:
            grants: List of grant dicts with index, issuer_canonical, description, amount_cad, region
            
        Returns:
            Formatted prompt string
        """
        system_prompt = f"""You are a Canadian government procurement intelligence analyst. Your job is to classify government grant records into standardized funding themes and procurement categories.

You must ONLY use themes and categories from the provided taxonomy. Never invent new ones.
Respond ONLY with a valid JSON array. No preamble, no explanation, no markdown.

TAXONOMY:
{json.dumps(self.taxonomy_map, indent=2)}
"""
        
        user_prompt = f"""Classify each of these {len(grants)} grant records. Return a JSON array where each element has:
- index: (the index number I gave you)
- funding_theme: (must be one of the valid themes)
- procurement_category: (must be the matching category from taxonomy)
- sector_tags: (array of 1-4 relevant sector strings like ["healthcare", "federal", "ontario"])
- confidence: (float 0.0-1.0 — how confident you are in this classification)
- reasoning: (one sentence why)

Grants to classify:
{json.dumps(grants, indent=2)}
"""
        
        return system_prompt, user_prompt
    
    async def classify_batch(
        self,
        grants: list[CleanedGrantRecord],
        batch_size: int = 25
    ) -> list[ClassificationResult]:
        """
        Classify a batch of grants using Claude API
        
        Args:
            grants: List of cleaned grant records to classify
            batch_size: Number of grants to classify per API call
            
        Returns:
            List of ClassificationResult objects
        """
        all_results = []
        total_batches = (len(grants) + batch_size - 1) // batch_size
        
        for batch_idx in range(0, len(grants), batch_size):
            batch = grants[batch_idx:batch_idx + batch_size]
            batch_num = (batch_idx // batch_size) + 1
            
            # Check cache for each grant
            uncached_grants = []
            cached_results = []
            
            for grant in batch:
                cache_key = self._cache_key(grant.description or "")
                if cache_key in self.cache:
                    cached_result = self.cache[cache_key]
                    # Update grant_id to match current grant
                    cached_result.grant_id = grant.id
                    cached_results.append(cached_result)
                else:
                    uncached_grants.append(grant)
            
            # If all cached, skip API call
            if not uncached_grants:
                all_results.extend(cached_results)
                logger.info(
                    f"[CLASSIFIER] Batch {batch_num}/{total_batches}: "
                    f"classified {len(batch)} grants (all cached)"
                )
                continue
            
            # Build prompt for uncached grants
            grant_dicts = []
            for i, grant in enumerate(uncached_grants):
                grant_dicts.append({
                    "index": i,
                    "issuer_canonical": grant.issuer_canonical,
                    "description": (grant.description or "")[:300],  # Truncate to 300 chars
                    "amount": grant.amount_cad,
                    "region": grant.region,
                })
            
            system_prompt, user_prompt = self._build_prompt(grant_dicts)
            
            # Call LLM API (wrap sync call in asyncio.to_thread)
            try:
                def _call_api():
                    if self.provider == "groq":
                        return self.client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            temperature=0,
                            max_tokens=2000,
                        )
                    elif self.provider == "openai":
                        return self.client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            temperature=0,
                            max_tokens=2000,
                        )
                    elif self.provider == "gemini":
                        model = self.client.GenerativeModel(self.model)
                        full_prompt = f"{system_prompt}\n\n{user_prompt}"
                        return model.generate_content(full_prompt)
                    elif self.provider == "anthropic":
                        return self.client.messages.create(
                            model=self.model,
                            max_tokens=2000,
                            temperature=0,
                            system=system_prompt,
                            messages=[
                                {"role": "user", "content": user_prompt},
                            ],
                        )
                    else:
                        raise ValueError(f"Unsupported provider: {self.provider}")
                
                message = await asyncio.to_thread(_call_api)
                
                # Extract text from response (handle different provider formats)
                response_text = ""
                if self.provider in ["groq", "openai"]:
                    # OpenAI/Groq format
                    response_text = message.choices[0].message.content
                elif self.provider == "gemini":
                    # Gemini format
                    response_text = message.text
                elif self.provider == "anthropic":
                    # Anthropic format
                    if message.content:
                        for content_block in message.content:
                            if hasattr(content_block, "text"):
                                response_text += content_block.text
                            elif isinstance(content_block, dict) and "text" in content_block:
                                response_text += content_block["text"]
                
                # Parse JSON response
                try:
                    # Remove markdown code blocks if present
                    if response_text.startswith("```"):
                        lines = response_text.split("\n")
                        response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
                    
                    classifications = json.loads(response_text)
                    if not isinstance(classifications, list):
                        classifications = [classifications]
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.error(f"Response text: {response_text[:500]}")
                    # Create fallback results
                    classifications = []
                    for grant in uncached_grants:
                        classifications.append({
                            "index": uncached_grants.index(grant),
                            "funding_theme": "Unknown",
                            "procurement_category": "Unknown",
                            "sector_tags": [],
                            "confidence": 0.1,
                            "reasoning": "JSON parse error",
                        })
                
            except Exception as e:
                logger.error(f"API call failed: {e}")
                # Create fallback results
                classifications = []
                for grant in uncached_grants:
                    classifications.append({
                        "index": uncached_grants.index(grant),
                        "funding_theme": "Unknown",
                        "procurement_category": "Unknown",
                        "sector_tags": [],
                        "confidence": 0.1,
                        "reasoning": f"API error: {str(e)}",
                    })
            
            # Validate and process results
            batch_results = []
            low_confidence_count = 0
            
            for i, classification in enumerate(classifications):
                if i >= len(uncached_grants):
                    break
                
                grant = uncached_grants[i]
                cache_key = self._cache_key(grant.description or "")
                
                # Validate funding_theme
                funding_theme = classification.get("funding_theme", "Unknown")
                if funding_theme not in self.valid_themes:
                    funding_theme = "Unknown"
                    classification["classification_flags"] = classification.get("classification_flags", [])
                    classification["classification_flags"].append("invalid_theme")
                    classification["confidence"] = 0.1
                
                # Validate procurement_category
                procurement_category = classification.get("procurement_category", "Unknown")
                if procurement_category not in self.valid_categories:
                    # Try to find matching category from taxonomy
                    if funding_theme in self.taxonomy_map:
                        procurement_category = self.taxonomy_map[funding_theme]["procurement_category"]
                    else:
                        procurement_category = "Unknown"
                        classification["classification_flags"] = classification.get("classification_flags", [])
                        classification["classification_flags"].append("invalid_category")
                        classification["confidence"] = 0.1
                
                # Validate confidence
                confidence = classification.get("confidence", 0.5)
                try:
                    confidence = float(confidence)
                    confidence = max(0.0, min(1.0, confidence))  # Clamp to 0.0-1.0
                except (ValueError, TypeError):
                    confidence = 0.5
                
                # Check for low confidence
                needs_review = confidence < 0.70
                if needs_review:
                    low_confidence_count += 1
                
                # Build result
                result = ClassificationResult(
                    grant_id=grant.id,
                    funding_theme=funding_theme,
                    procurement_category=procurement_category,
                    sector_tags=classification.get("sector_tags", []),
                    confidence=confidence,
                    reasoning=classification.get("reasoning", ""),
                    needs_review=needs_review,
                    classification_flags=classification.get("classification_flags", []),
                )
                
                # Store in cache
                self.cache[cache_key] = result
                
                batch_results.append(result)
            
            all_results.extend(cached_results)
            all_results.extend(batch_results)
            
            logger.info(
                f"[CLASSIFIER] Batch {batch_num}/{total_batches}: "
                f"classified {len(batch)} grants, {low_confidence_count} low-confidence, "
                f"{len(cached_results)} cache hits"
            )
        
        return all_results
