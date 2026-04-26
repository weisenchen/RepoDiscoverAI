"""
RepoDiscoverAI v3.0 - Cache Management

Provides caching layer for API responses and generated content.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CacheManager:
    """Simple file-based cache with TTL support."""
    
    def __init__(self, cache_dir: str = "./cache", default_ttl: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self.memory_cache: dict = {}
        self.memory_ttl: dict = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        # Check memory cache first
        if key in self.memory_cache:
            if datetime.now() < self.memory_ttl[key]:
                return self.memory_cache[key]
            else:
                del self.memory_cache[key]
                del self.memory_ttl[key]
        
        # Check file cache
        file_path = self.cache_dir / f"{self._hash_key(key)}.json"
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Check TTL
                if datetime.fromisoformat(data['expires_at']) > datetime.now():
                    # Load to memory cache
                    self.memory_cache[key] = data['value']
                    self.memory_ttl[key] = datetime.fromisoformat(data['expires_at'])
                    return data['value']
                else:
                    file_path.unlink()
            except Exception as e:
                logger.warning(f"Cache read error for {key}: {e}")
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache."""
        ttl = ttl or self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        # Store in memory
        self.memory_cache[key] = value
        self.memory_ttl[key] = expires_at
        
        # Store in file
        file_path = self.cache_dir / f"{self._hash_key(key)}.json"
        try:
            with open(file_path, 'w') as f:
                json.dump({
                    'key': key,
                    'value': value,
                    'created_at': datetime.now().isoformat(),
                    'expires_at': expires_at.isoformat()
                }, f)
        except Exception as e:
            logger.warning(f"Cache write error for {key}: {e}")
    
    async def invalidate(self, key: str):
        """Invalidate cache entry."""
        if key in self.memory_cache:
            del self.memory_cache[key]
            del self.memory_ttl[key]
        
        file_path = self.cache_dir / f"{self._hash_key(key)}.json"
        if file_path.exists():
            file_path.unlink()
    
    async def clear(self):
        """Clear all cache."""
        self.memory_cache.clear()
        self.memory_ttl.clear()
        
        for file in self.cache_dir.glob("*.json"):
            file.unlink()
    
    def _hash_key(self, key: str) -> str:
        """Hash cache key for file storage."""
        return hashlib.md5(key.encode()).hexdigest()


# Global cache instance
cache_manager: Optional[CacheManager] = None


async def init_cache(cache_dir: str = "./cache", default_ttl: int = 3600):
    """Initialize global cache manager."""
    global cache_manager
    cache_manager = CacheManager(cache_dir, default_ttl)
    logger.info(f"Cache initialized: {cache_dir}")


async def get_cache() -> CacheManager:
    """Get global cache manager."""
    global cache_manager
    if cache_manager is None:
        await init_cache()
    return cache_manager
