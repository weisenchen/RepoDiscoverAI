"""
Health Check Endpoints for RepoDiscoverAI
Provides /health, /ready, and /live endpoints for Kubernetes/Docker health checks
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any

import asyncpg
import redis.asyncio as redis

from app.core.config import settings


class HealthChecker:
    """Centralized health check management"""
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.last_db_check = None
        self.last_redis_check = None
        self.db_healthy = False
        self.redis_healthy = False
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and health"""
        try:
            conn = await asyncpg.connect(settings.database_url)
            
            # Check basic connectivity
            version = await conn.fetchval("SELECT version()")
            
            # Check connection pool
            pool_size = await conn.fetchval("SHOW max_connections")
            active_connections = await conn.fetchval("SELECT count(*) FROM pg_stat_activity")
            
            # Check database size
            db_size = await conn.fetchval("SELECT pg_database_size(current_database())")
            
            await conn.close()
            
            self.last_db_check = datetime.utcnow()
            self.db_healthy = True
            
            return {
                "status": "healthy",
                "version": version.split(",")[0].strip(),
                "pool_size": pool_size,
                "active_connections": active_connections,
                "database_size_bytes": db_size,
                "response_time_ms": (datetime.utcnow() - self.last_db_check).total_seconds() * 1000
            }
        
        except Exception as e:
            self.db_healthy = False
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and health"""
        try:
            client = redis.from_url(settings.redis_url)
            
            # Check connectivity
            ping_response = await client.ping()
            
            # Get info
            info = await client.info("memory")
            
            # Check memory usage
            used_memory = info.get("used_memory", 0)
            max_memory = info.get("maxmemory", 0)
            
            await client.close()
            
            self.last_redis_check = datetime.utcnow()
            self.redis_healthy = True
            
            return {
                "status": "healthy",
                "ping": ping_response,
                "used_memory_bytes": used_memory,
                "max_memory_bytes": max_memory,
                "memory_usage_percent": (used_memory / max_memory * 100) if max_memory > 0 else 0,
                "response_time_ms": (datetime.utcnow() - self.last_redis_check).total_seconds() * 1000
            }
        
        except Exception as e:
            self.redis_healthy = False
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def get_full_health(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        db_health = await self.check_database()
        redis_health = await self.check_redis()
        
        overall_healthy = (
            db_health["status"] == "healthy" and
            redis_health["status"] == "healthy"
        )
        
        uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": uptime_seconds,
            "uptime_human": self._format_uptime(uptime_seconds),
            "version": settings.app_version,
            "environment": settings.environment,
            "checks": {
                "database": db_health,
                "cache": redis_health
            },
            "healthy": overall_healthy
        }
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        
        return " ".join(parts) if parts else "< 1m"


# Global health checker instance
health_checker = HealthChecker()


async def health_check() -> Dict[str, Any]:
    """
    GET /health
    
    Full health check including all dependencies.
    Use for load balancer health checks.
    """
    return await health_checker.get_full_health()


async def ready_check() -> Dict[str, Any]:
    """
    GET /ready
    
    Readiness probe - is the service ready to accept traffic?
    Returns unhealthy if dependencies aren't ready yet.
    """
    db_healthy = health_checker.db_healthy
    redis_healthy = health_checker.redis_healthy
    
    is_ready = db_healthy and redis_healthy
    
    return {
        "status": "ready" if is_ready else "not_ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": "ready" if db_healthy else "not_ready",
            "cache": "ready" if redis_healthy else "not_ready"
        },
        "ready": is_ready
    }


async def live_check() -> Dict[str, Any]:
    """
    GET /live
    
    Liveness probe - is the service alive?
    Simple check that just verifies the process is running.
    Use for Kubernetes liveness probes.
    """
    uptime_seconds = (datetime.utcnow() - health_checker.start_time).total_seconds()
    
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": uptime_seconds,
        "pid": asyncio.current_task() is not None
    }


# Prometheus metrics endpoint
def get_metrics() -> str:
    """
    GET /metrics
    
    Prometheus-compatible metrics endpoint.
    """
    uptime = (datetime.utcnow() - health_checker.start_time).total_seconds()
    
    metrics = [
        "# HELP repodiscover_uptime_seconds Service uptime in seconds",
        "# TYPE repodiscover_uptime_seconds counter",
        f"repodiscover_uptime_seconds {uptime}",
        "",
        "# HELP repodiscover_database_healthy Database health status (1=healthy, 0=unhealthy)",
        "# TYPE repodiscover_database_healthy gauge",
        f"repodiscover_database_healthy {1 if health_checker.db_healthy else 0}",
        "",
        "# HELP repodiscover_redis_healthy Redis health status (1=healthy, 0=unhealthy)",
        "# TYPE repodiscover_redis_healthy gauge",
        f"repodiscover_redis_healthy {1 if health_checker.redis_healthy else 0}",
        "",
        "# HELP repodiscover_info Service information",
        "# TYPE repodiscover_info gauge",
        f'repodiscover_info{{version="{settings.app_version}",environment="{settings.environment}"}} 1',
    ]
    
    return "\n".join(metrics)
