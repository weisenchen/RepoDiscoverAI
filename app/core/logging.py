"""
RepoDiscoverAI v3.0 - Structured Logging

Provides structured logging with Prometheus metrics integration.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = True
) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        json_format: Whether to use JSON format
    """
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer() if json_format else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )
    
    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        logging.getLogger().addHandler(file_handler)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class MetricsCollector:
    """Collect and expose Prometheus metrics."""
    
    def __init__(self, namespace: str = "repodiscover"):
        self.namespace = namespace
        self.metrics = {}
    
    def increment_counter(self, name: str, labels: Optional[dict] = None):
        """Increment a counter metric."""
        key = f"{self.namespace}_{name}"
        if key not in self.metrics:
            self.metrics[key] = {"type": "counter", "value": 0, "labels": labels or {}}
        self.metrics[key]["value"] += 1
        get_logger("metrics").info(f"counter_increment", metric=key, value=self.metrics[key]["value"])
    
    def set_gauge(self, name: str, value: float, labels: Optional[dict] = None):
        """Set a gauge metric."""
        key = f"{self.namespace}_{name}"
        self.metrics[key] = {"type": "gauge", "value": value, "labels": labels or {}}
        get_logger("metrics").info(f"gauge_set", metric=key, value=value)
    
    def observe_histogram(self, name: str, value: float, labels: Optional[dict] = None):
        """Observe a histogram value."""
        key = f"{self.namespace}_{name}"
        if key not in self.metrics:
            self.metrics[key] = {"type": "histogram", "values": [], "labels": labels or {}}
        self.metrics[key]["values"].append(value)
        get_logger("metrics").info(f"histogram_observe", metric=key, value=value)
    
    def get_metrics(self) -> dict:
        """Get all metrics."""
        return self.metrics
