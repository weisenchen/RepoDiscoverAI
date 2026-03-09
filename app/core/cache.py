"""
Redis Caching Layer

Improve performance with multi-level caching strategy.
"""

import json
import hashlib
import logging
from typing import Optional, Any, Dict, List
from datetime import timedelta
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)


class CacheConfig:
    """Cache configuration."""
    
    # TTL settings (in seconds)
    TTL_SEARCH_RESULTS = 300  # 5 minutes
    TTL_TRENDING = 600  # 10 minutes
    TTL_REPO_DETAILS = 3600  # 1 hour
    TTL_USER_DATA = 1800  # 30 minutes
    
    # Cache keys prefix
    PREFIX_SEARCH = "search:"
    PREFIX_TRENDING = "trending:"
    PREFIX_REPO = "repo:"
    PREFIX_USER = "user:"
    PREFIX_COLLECTION = "collection:"


class MemoryCache:
    """In-memory cache (L1 cache)."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._access_order: List[str] = []
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self._cache:
            # Move to end (most recently used)
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = None):
        """Set value in cache."""
        import time
        
        # Evict if at max size
        if len(self._cache) >= self.max_size and key not in self._cache:
            # Remove least recently used
            if self._access_order:
                lru_key = self._access_order.pop(0)
                self._cache.pop(lru_key, None)
                self._timestamps.pop(lru_key, None)
        
        self._cache[key] = value
        self._timestamps[key] = time.time()
        if key not in self._access_order:
            self._access_order.append(key)
    
    def delete(self, key: str):
        """Delete key from cache."""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
        if key in self._access_order:
            self._access_order.remove(key)
    
    def clear(self):
        """Clear all cache."""
        self._cache.clear()
        self._timestamps.clear()
        self._access_order.clear()
    
    def stats(self) -> Dict:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "keys": list(self._cache.keys())[:10]  # First 10 keys
        }


class RedisCache:
    """Redis cache (L2 cache)."""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.host = host
        self.port = port
        self.db = db
        self._redis = None
    
    async def connect(self):
        """Connect to Redis."""
        try:
            import redis.asyncio as redis
            self._redis = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True
            )
            logger.info(f"✅ Connected to Redis at {self.host}:{self.port}")
        except ImportError:
            logger.warning("Redis not available, using memory cache only")
            self._redis = None
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self._redis = None
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis."""
        if not self._redis:
            return None
        
        try:
            value = await self._redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = None):
        """Set value in Redis."""
        if not self._redis:
            return
        
        try:
            serialized = json.dumps(value)
            if ttl:
                await self._redis.setex(key, ttl, serialized)
            else:
                await self._redis.set(key, serialized)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
    
    async def delete(self, key: str):
        """Delete key from Redis."""
        if not self._redis:
            return
        
        try:
            await self._redis.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
    
    async def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern."""
        if not self._redis:
            return
        
        try:
            keys = await self._redis.keys(pattern)
            if keys:
                await self._redis.delete(*keys)
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
    
    async def stats(self) -> Dict:
        """Get Redis statistics."""
        if not self._redis:
            return {"available": False}
        
        try:
            info = await self._redis.info("stats")
            return {
                "available": True,
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "N/A"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            return {"available": False, "error": str(e)}


class CacheManager:
    """Two-level cache manager."""
    
    def __init__(self, use_redis: bool = True):
        self.use_redis = use_redis
        self.l1_cache = MemoryCache(max_size=1000)
        self.l2_cache = RedisCache()
        self._connected = False
    
    async def connect(self):
        """Connect to Redis if enabled."""
        if self.use_redis:
            await self.l2_cache.connect()
            self._connected = True
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self._connected:
            await self.l2_cache.disconnect()
            self._connected = False
    
    def _make_key(self, prefix: str, *args) -> str:
        """Generate cache key from arguments."""
        key_parts = [prefix] + [str(a) for a in args]
        key_string = ":".join(key_parts)
        # Hash long keys
        if len(key_string) > 200:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()[:16]
            return f"{prefix}:{key_hash}"
        return key_string
    
    async def get(self, prefix: str, *args) -> Optional[Any]:
        """Get value from cache (L1 → L2)."""
        key = self._make_key(prefix, *args)
        
        # Try L1 (memory) cache first
        value = self.l1_cache.get(key)
        if value is not None:
            logger.debug(f"Cache L1 hit: {key}")
            return value
        
        # Try L2 (Redis) cache
        if self.use_redis and self._connected:
            value = await self.l2_cache.get(key)
            if value is not None:
                logger.debug(f"Cache L2 hit: {key}")
                # Populate L1
                self.l1_cache.set(key, value)
                return value
        
        logger.debug(f"Cache miss: {key}")
        return None
    
    async def set(self, prefix: str, value: Any, ttl: int = None, *args):
        """Set value in cache (L1 + L2)."""
        key = self._make_key(prefix, *args)
        
        # Set in L1
        self.l1_cache.set(key, value, ttl)
        
        # Set in L2
        if self.use_redis and self._connected:
            await self.l2_cache.set(key, value, ttl)
    
    async def delete(self, prefix: str, *args):
        """Delete value from cache."""
        key = self._make_key(prefix, *args)
        self.l1_cache.delete(key)
        
        if self.use_redis and self._connected:
            await self.l2_cache.delete(key)
    
    async def clear_prefix(self, prefix: str):
        """Clear all keys with prefix."""
        # Clear L1
        keys_to_delete = [
            k for k in self.l1_cache._cache.keys()
            if k.startswith(prefix)
        ]
        for key in keys_to_delete:
            self.l1_cache.delete(key)
        
        # Clear L2
        if self.use_redis and self._connected:
            await self.l2_cache.clear_pattern(f"{prefix}*")
    
    # Convenience methods for common cache operations
    
    async def get_search(self, query: str, filters: Dict = None) -> Optional[List]:
        """Get cached search results."""
        filters_key = json.dumps(filters, sort_keys=True) if filters else ""
        return await self.get(CacheConfig.PREFIX_SEARCH, query, filters_key)
    
    async def set_search(self, query: str, results: List, filters: Dict = None):
        """Cache search results."""
        filters_key = json.dumps(filters, sort_keys=True) if filters else ""
        await self.set(
            CacheConfig.PREFIX_SEARCH,
            results,
            CacheConfig.TTL_SEARCH_RESULTS,
            query,
            filters_key
        )
    
    async def get_trending(self, language: str = None, since: str = "daily") -> Optional[List]:
        """Get cached trending repos."""
        return await self.get(CacheConfig.PREFIX_TRENDING, language or "all", since)
    
    async def set_trending(self, repos: List, language: str = None, since: str = "daily"):
        """Cache trending repos."""
        await self.set(
            CacheConfig.PREFIX_TRENDING,
            repos,
            CacheConfig.TTL_TRENDING,
            language or "all",
            since
        )
    
    async def get_repo(self, repo_id: int) -> Optional[Dict]:
        """Get cached repo details."""
        return await self.get(CacheConfig.PREFIX_REPO, repo_id)
    
    async def set_repo(self, repo_id: int, data: Dict):
        """Cache repo details."""
        await self.set(
            CacheConfig.PREFIX_REPO,
            data,
            CacheConfig.TTL_REPO_DETAILS,
            repo_id
        )
    
    async def stats(self) -> Dict:
        """Get cache statistics."""
        return {
            "l1": self.l1_cache.stats(),
            "l2": await self.l2_cache.stats() if self._connected else {"available": False}
        }


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get or create cache manager."""
    global _cache_manager
    
    if _cache_manager is None:
        import os
        use_redis = os.getenv("USE_REDIS", "false").lower() == "true"
        _cache_manager = CacheManager(use_redis=use_redis)
    
    return _cache_manager


async def init_cache():
    """Initialize cache system."""
    cache = get_cache_manager()
    await cache.connect()
    logger.info("✅ Cache system initialized")
    return cache


async def shutdown_cache():
    """Shutdown cache system."""
    cache = get_cache_manager()
    await cache.disconnect()
    logger.info("👋 Cache system shutdown")


# Cache decorator for async functions
def cached(prefix: str, ttl: int = None):
    """Decorator to cache function results."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # Generate cache key
            key_args = args[1:] if args and hasattr(args[0], '__class__') else args
            cache_key = f"{prefix}:{func.__name__}:{hash(str(key_args) + str(kwargs))}"
            
            # Try cache
            cached_result = await cache.get(prefix, cache_key)
            if cached_result is not None:
                return cached_result
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            await cache.set(prefix, result, ttl, cache_key)
            
            return result
        return wrapper
    return decorator
