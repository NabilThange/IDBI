"""
Cache utility for storing AI-generated responses.
Implements file-based caching to avoid redundant LLM calls.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from app.config import CACHE_DIR


class Cache:
    """File-based cache for AI responses"""
    
    def __init__(self, base_dir: Path = CACHE_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, profile_id: str, endpoint: str) -> Path:
        """
        Get the cache file path for a profile and endpoint.
        
        Args:
            profile_id: Customer profile identifier
            endpoint: API endpoint name (e.g., 'financial_health')
            
        Returns:
            Path to cache file
        """
        profile_cache_dir = self.base_dir / profile_id
        profile_cache_dir.mkdir(parents=True, exist_ok=True)
        return profile_cache_dir / f"{endpoint}.json"
    
    def get(self, profile_id: str, endpoint: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached response for a profile and endpoint.
        
        Args:
            profile_id: Customer profile identifier
            endpoint: API endpoint name
            
        Returns:
            Cached data or None if not found
        """
        cache_path = self._get_cache_path(profile_id, endpoint)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except Exception as e:
            print(f"Error reading cache for {profile_id}/{endpoint}: {e}")
            return None
    
    def set(self, profile_id: str, endpoint: str, data: Dict[str, Any]) -> bool:
        """
        Store response in cache.
        
        Args:
            profile_id: Customer profile identifier
            endpoint: API endpoint name
            data: Data to cache
            
        Returns:
            True if successful, False otherwise
        """
        cache_path = self._get_cache_path(profile_id, endpoint)
        
        try:
            # Add metadata
            cache_data = {
                "cached_at": datetime.now().isoformat(),
                "profile_id": profile_id,
                "endpoint": endpoint,
                "data": data
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error writing cache for {profile_id}/{endpoint}: {e}")
            return False
    
    def invalidate(self, profile_id: str, endpoint: Optional[str] = None) -> bool:
        """
        Invalidate cache for a profile.
        
        Args:
            profile_id: Customer profile identifier
            endpoint: Optional specific endpoint to invalidate (if None, clears all)
            
        Returns:
            True if successful
        """
        if endpoint:
            # Clear specific endpoint cache
            cache_path = self._get_cache_path(profile_id, endpoint)
            if cache_path.exists():
                cache_path.unlink()
        else:
            # Clear all caches for this profile
            profile_cache_dir = self.base_dir / profile_id
            if profile_cache_dir.exists():
                for cache_file in profile_cache_dir.glob("*.json"):
                    cache_file.unlink()
        
        return True
    
    def exists(self, profile_id: str, endpoint: str) -> bool:
        """Check if cache exists for a profile and endpoint"""
        cache_path = self._get_cache_path(profile_id, endpoint)
        return cache_path.exists()


# Global cache instance
cache = Cache()
