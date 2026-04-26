"""
RepoDiscoverAI v3.0 - Cost Optimizer

Provides API budget tracking, rate limiting, and cost optimization.
"""

import logging
import time
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class APICallTracker:
    """Track API calls for budget management."""
    calls: Dict[str, int] = field(default_factory=dict)
    daily_budget: Dict[str, int] = field(default_factory=dict)
    
    def record_call(self, service: str, count: int = 1):
        """Record API call."""
        if service not in self.calls:
            self.calls[service] = 0
        self.calls[service] += count
    
    def get_calls(self, service: str) -> int:
        """Get call count for service."""
        return self.calls.get(service, 0)
    
    def get_total_calls(self) -> int:
        """Get total API calls."""
        return sum(self.calls.values())
    
    def set_budget(self, service: str, limit: int):
        """Set daily budget for service."""
        self.daily_budget[service] = limit
    
    def is_within_budget(self, budget: Dict[str, int]) -> bool:
        """Check if all services are within budget."""
        for service, limit in budget.items():
            if self.calls.get(service, 0) > limit:
                return False
        return True
    
    def get_remaining_budget(self, budget: Dict[str, int]) -> Dict[str, int]:
        """Get remaining budget for each service."""
        return {
            service: max(0, limit - self.calls.get(service, 0))
            for service, limit in budget.items()
        }
    
    def reset(self):
        """Reset all counters."""
        self.calls.clear()


@dataclass
class RateLimiter:
    """Token bucket rate limiter."""
    max_calls: int
    time_window: float  # seconds
    _calls: list = field(default_factory=list)
    
    def can_proceed(self) -> bool:
        """Check if request can proceed."""
        now = time.time()
        
        # Remove old calls outside window
        self._calls = [t for t in self._calls if now - t < self.time_window]
        
        if len(self._calls) < self.max_calls:
            self._calls.append(now)
            return True
        
        return False
    
    def wait_time(self) -> float:
        """Get wait time until next call allowed."""
        if not self._calls:
            return 0.0
        
        now = time.time()
        oldest = self._calls[0]
        wait = self.time_window - (now - oldest)
        return max(0, wait)


class CostOptimizer:
    """Optimize costs by managing API calls and caching."""
    
    def __init__(self):
        self.tracker = APICallTracker()
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.daily_costs: Dict[str, float] = {}
        
        # Default budgets (per day)
        self.default_budgets = {
            "github": 5000,
            "elevenlabs": 10000,  # characters
            "shotstack": 300,     # seconds
            "twitter": 300,
        }
        
        # Default rate limits
        self.default_rate_limits = {
            "github": RateLimiter(max_calls=100, time_window=3600),  # 100/hr
            "elevenlabs": RateLimiter(max_calls=50, time_window=3600),
            "shotstack": RateLimiter(max_calls=10, time_window=3600),
            "twitter": RateLimiter(max_calls=180, time_window=900),  # 180/15min
        }
        
        self.rate_limiters.update(self.default_rate_limits)
    
    def check_rate_limit(self, service: str) -> bool:
        """Check if service is within rate limit."""
        limiter = self.rate_limiters.get(service)
        if not limiter:
            return True
        
        return limiter.can_proceed()
    
    def get_wait_time(self, service: str) -> float:
        """Get wait time for service."""
        limiter = self.rate_limiters.get(service)
        if not limiter:
            return 0.0
        
        return limiter.wait_time()
    
    def record_api_call(self, service: str, cost: float = 0.0):
        """Record API call and cost."""
        self.tracker.record_call(service)
        
        if service not in self.daily_costs:
            self.daily_costs[service] = 0.0
        self.daily_costs[service] += cost
        
        logger.debug(f"API call recorded: {service}, cost: ${cost:.4f}")
    
    def get_cost_summary(self) -> Dict:
        """Get cost summary."""
        return {
            "total_calls": self.tracker.get_total_calls(),
            "calls_by_service": dict(self.tracker.calls),
            "daily_costs": dict(self.daily_costs),
            "total_cost": sum(self.daily_costs.values()),
            "remaining_budget": self.tracker.get_remaining_budget(self.default_budgets)
        }
    
    def optimize_content_generation(self, content_type: str) -> str:
        """
        Choose optimal generation method based on cost.
        
        Returns:
            Recommended service to use
        """
        if content_type == "podcast":
            # Check ElevenLabs budget
            if self.tracker.get_calls("elevenlabs") < self.default_budgets["elevenlabs"]:
                return "elevenlabs"
            else:
                logger.warning("ElevenLabs budget exceeded, falling back to local TTS")
                return "local_tts"
        
        elif content_type == "video":
            # Check Shotstack budget
            if self.tracker.get_calls("shotstack") < self.default_budgets["shotstack"]:
                return "shotstack"
            else:
                logger.warning("Shotstack budget exceeded, falling back to manual")
                return "manual"
        
        elif content_type == "social":
            # Check Twitter budget
            if self.tracker.get_calls("twitter") < self.default_budgets["twitter"]:
                return "twitter"
            else:
                logger.warning("Twitter budget exceeded, queuing for later")
                return "queue"
        
        return "default"
    
    def reset_daily(self):
        """Reset daily counters."""
        self.tracker.reset()
        self.daily_costs.clear()
        logger.info("Daily cost tracker reset")


# Global cost optimizer
cost_optimizer = CostOptimizer()
