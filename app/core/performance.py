"""
RepoDiscoverAI v3.0 - Performance Optimizer

Provides concurrent fetching, caching strategies, and performance monitoring.
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Callable
from functools import wraps
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Track performance metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def average_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests
    
    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total
    
    def to_dict(self) -> Dict:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": round(self.success_rate, 4),
            "average_latency_ms": round(self.average_latency_ms, 2),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(self.cache_hit_rate, 4)
        }


class PerformanceMonitor:
    """Monitor and optimize performance."""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self._start_time = time.time()
    
    def record_request(self, success: bool, latency_ms: float):
        """Record a request."""
        self.metrics.total_requests += 1
        if success:
            self.metrics.successful_requests += 1
        else:
            self.metrics.failed_requests += 1
        self.metrics.total_latency_ms += latency_ms
    
    def record_cache_hit(self):
        """Record a cache hit."""
        self.metrics.cache_hits += 1
    
    def record_cache_miss(self):
        """Record a cache miss."""
        self.metrics.cache_misses += 1
    
    def get_metrics(self) -> Dict:
        """Get performance metrics."""
        return self.metrics.to_dict()
    
    def get_uptime_seconds(self) -> float:
        """Get uptime in seconds."""
        return time.time() - self._start_time


# Global performance monitor
perf_monitor = PerformanceMonitor()


def track_performance(func: Callable):
    """Decorator to track function performance."""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            latency_ms = (time.time() - start_time) * 1000
            perf_monitor.record_request(success=True, latency_ms=latency_ms)
            return result
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            perf_monitor.record_request(success=False, latency_ms=latency_ms)
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            latency_ms = (time.time() - start_time) * 1000
            perf_monitor.record_request(success=True, latency_ms=latency_ms)
            return result
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            perf_monitor.record_request(success=False, latency_ms=latency_ms)
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


class ConcurrentFetcher:
    """Fetch multiple resources concurrently with rate limiting."""
    
    def __init__(self, max_concurrent: int = 5, delay_between: float = 0.1):
        self.max_concurrent = max_concurrent
        self.delay_between = delay_between
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fetch_all(self, tasks: List[Callable]) -> List[Any]:
        """
        Fetch all tasks concurrently.
        
        Args:
            tasks: List of async functions to execute
            
        Returns:
            List of results (None for failed tasks)
        """
        async def bounded_task(task):
            async with self.semaphore:
                try:
                    return await task()
                except Exception as e:
                    logger.error(f"Task failed: {e}")
                    return None
        
        # Execute all tasks
        results = await asyncio.gather(*[bounded_task(t) for t in tasks])
        
        # Add small delay between batches
        await asyncio.sleep(self.delay_between)
        
        return list(results)
    
    async def fetch_with_retry(self, task: Callable, max_retries: int = 3) -> Any:
        """Fetch with retry logic."""
        for attempt in range(max_retries):
            try:
                async with self.semaphore:
                    return await task()
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Task failed after {max_retries} attempts: {e}")
                    return None
                await asyncio.sleep(2 ** attempt)  # Exponential backoff


class SmartCache:
    """Smart caching with TTL, size limits, and LRU eviction."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self._cache:
            entry = self._cache[key]
            if datetime.now() < entry["expires_at"]:
                perf_monitor.record_cache_hit()
                # Update access time for LRU
                entry["last_access"] = datetime.now()
                return entry["value"]
            else:
                # Expired
                del self._cache[key]
        
        perf_monitor.record_cache_miss()
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache."""
        ttl = ttl or self.default_ttl
        
        # Evict if cache is full (LRU)
        if len(self._cache) >= self.max_size:
            self._evict_lru()
        
        self._cache[key] = {
            "value": value,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(seconds=ttl),
            "last_access": datetime.now()
        }
    
    async def invalidate(self, key: str):
        """Invalidate cache entry."""
        if key in self._cache:
            del self._cache[key]
    
    async def clear(self):
        """Clear all cache."""
        self._cache.clear()
    
    def _evict_lru(self):
        """Evict least recently used entry."""
        if not self._cache:
            return
        
        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k]["last_access"])
        del self._cache[lru_key]
    
    @property
    def size(self) -> int:
        return len(self._cache)
    
    @property
    def hit_rate(self) -> float:
        return perf_monitor.metrics.cache_hit_rate
