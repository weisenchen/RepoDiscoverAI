"""
RepoDiscoverAI v3.0 - Retry & Error Handling

Provides retry logic with exponential backoff for API calls.
"""

import asyncio
import logging
import random
from functools import wraps
from typing import Callable, Optional, Tuple, Type

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions


def retry_with_backoff(config: Optional[RetryConfig] = None):
    """
    Decorator for retrying async functions with exponential backoff.
    
    Usage:
        @retry_with_backoff(RetryConfig(max_retries=5))
        async def fetch_data():
            ...
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_retries:
                        logger.error(
                            f"Failed after {config.max_retries} retries: {func.__name__}",
                            exc_info=True
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    # Add jitter to prevent thundering herd
                    if config.jitter:
                        delay = delay * (0.5 + random.random() * 0.5)
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_retries} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator


# Predefined retry configurations for common services
GITHUB_RETRY_CONFIG = RetryConfig(
    max_retries=5,
    base_delay=2.0,
    max_delay=120.0,
    retryable_exceptions=(ConnectionError, TimeoutError, Exception)
)

ELEVENLABS_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=5.0,
    max_delay=60.0,
    retryable_exceptions=(ConnectionError, TimeoutError)
)

SHOTSTACK_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=3.0,
    max_delay=90.0,
    retryable_exceptions=(ConnectionError, TimeoutError)
)

TWITTER_RETRY_CONFIG = RetryConfig(
    max_retries=4,
    base_delay=2.0,
    max_delay=60.0,
    retryable_exceptions=(ConnectionError, TimeoutError)
)
