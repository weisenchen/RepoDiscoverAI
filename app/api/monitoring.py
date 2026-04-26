"""
RepoDiscoverAI v3.0 - Monitoring API

Provides monitoring endpoints for performance, cost, and quality metrics.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List
from datetime import datetime

from app.core.performance import perf_monitor
from app.core.cost_optimizer import cost_optimizer
from app.core.quality import QualityEvaluator

router = APIRouter()

# Global quality evaluator
quality_evaluator = QualityEvaluator()


@router.get("/metrics")
async def get_metrics() -> Dict:
    """Get application metrics."""
    return {
        "performance": perf_monitor.get_metrics(),
        "uptime_seconds": perf_monitor.get_uptime_seconds(),
        "cost": cost_optimizer.get_cost_summary(),
        "quality": {
            "total_reviews": len(quality_evaluator.reviews),
            "average_score": quality_evaluator.get_average_score().to_dict() if quality_evaluator.get_average_score() else None,
            "approval_rate": sum(1 for r in quality_evaluator.reviews if r.approved) / max(len(quality_evaluator.reviews), 1)
        }
    }


@router.get("/metrics/performance")
async def get_performance_metrics() -> Dict:
    """Get performance metrics only."""
    return perf_monitor.get_metrics()


@router.get("/metrics/cost")
async def get_cost_metrics() -> Dict:
    """Get cost metrics only."""
    return cost_optimizer.get_cost_summary()


@router.get("/metrics/quality")
async def get_quality_metrics() -> Dict:
    """Get quality metrics only."""
    avg_score = quality_evaluator.get_average_score()
    return {
        "total_reviews": len(quality_evaluator.reviews),
        "average_score": avg_score.to_dict() if avg_score else None,
        "approval_rate": sum(1 for r in quality_evaluator.reviews if r.approved) / max(len(quality_evaluator.reviews), 1),
        "recent_reviews": [
            {
                "content_id": r.content_id,
                "content_type": r.content_type,
                "score": r.quality_score.to_dict(),
                "approved": r.approved,
                "timestamp": r.timestamp
            }
            for r in quality_evaluator.reviews[-10:]  # Last 10 reviews
        ]
    }


@router.post("/quality/review")
async def submit_quality_review(content_id: str, score: Dict, approved: bool, reviewer: str = "human", feedback: str = "") -> Dict:
    """Submit manual quality review."""
    from app.core.quality import QualityScore, ContentReview
    
    quality_score = QualityScore(**score)
    review = ContentReview(
        content_id=content_id,
        content_type="manual",
        quality_score=quality_score,
        reviewer=reviewer,
        feedback=feedback,
        approved=approved
    )
    
    quality_evaluator.reviews.append(review)
    
    return {
        "status": "success",
        "review": {
            "content_id": content_id,
            "approved": approved,
            "score": quality_score.to_dict()
        }
    }


@router.post("/cost/reset")
async def reset_cost_tracker() -> Dict:
    """Reset daily cost tracker."""
    cost_optimizer.reset_daily()
    return {"status": "success", "message": "Daily cost tracker reset"}
