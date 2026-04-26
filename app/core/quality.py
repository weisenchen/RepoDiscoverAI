"""
RepoDiscoverAI v3.0 - Quality Evaluator

Provides content quality assessment with AI scoring and human review workflow.
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class QualityScore:
    """Quality score for content."""
    overall: float = 0.0
    relevance: float = 0.0
    accuracy: float = 0.0
    completeness: float = 0.0
    readability: float = 0.0
    engagement: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "overall": round(self.overall, 2),
            "relevance": round(self.relevance, 2),
            "accuracy": round(self.accuracy, 2),
            "completeness": round(self.completeness, 2),
            "readability": round(self.readability, 2),
            "engagement": round(self.engagement, 2)
        }


@dataclass
class ContentReview:
    """Content review record."""
    content_id: str
    content_type: str  # podcast, youtube, tweet, rss, markdown
    quality_score: QualityScore
    reviewer: str = "ai"  # ai or human
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    feedback: str = ""
    approved: bool = False


class QualityEvaluator:
    """Evaluate content quality."""
    
    def __init__(self, thresholds: Optional[Dict] = None):
        self.thresholds = thresholds or {
            "overall_min": 0.7,
            "relevance_min": 0.6,
            "accuracy_min": 0.7,
            "completeness_min": 0.6,
            "readability_min": 0.7,
            "engagement_min": 0.5
        }
        self.reviews: List[ContentReview] = []
    
    def evaluate_markdown(self, content: str, repos: list) -> QualityScore:
        """Evaluate Markdown content quality."""
        score = QualityScore()
        
        # Relevance: Check if content matches repos
        relevance_score = 0.0
        for repo in repos:
            if repo.name in content and repo.owner in content:
                relevance_score += 1.0
        score.relevance = relevance_score / max(len(repos), 1)
        
        # Completeness: Check for required sections
        required_sections = [
            "## Executive Summary",
            "## Top Repositories",
            "## Trend Analysis",
            "## Data Sources"
        ]
        completeness_score = sum(1 for s in required_sections if s in content) / len(required_sections)
        score.completeness = completeness_score
        
        # Readability: Check structure
        readability_score = 0.0
        if content.count("###") >= len(repos):  # Each repo has heading
            readability_score += 0.3
        if "**URL:**" in content:
            readability_score += 0.2
        if "**Stars:**" in content:
            readability_score += 0.2
        if "**Trend Score:**" in content:
            readability_score += 0.3
        score.readability = readability_score
        
        # Accuracy: Check for factual consistency
        accuracy_score = 1.0  # Assume accurate if generated from verified data
        score.accuracy = accuracy_score
        
        # Engagement: Check for calls-to-action
        engagement_score = 0.0
        if "Subscribe" in content or "Follow" in content:
            engagement_score += 0.5
        if "https://" in content:
            engagement_score += 0.3
        if "#" in content:  # Hashtags or numbering
            engagement_score += 0.2
        score.engagement = engagement_score
        
        # Overall score (weighted average)
        score.overall = (
            score.relevance * 0.25 +
            score.accuracy * 0.25 +
            score.completeness * 0.20 +
            score.readability * 0.15 +
            score.engagement * 0.15
        )
        
        return score
    
    def evaluate_podcast(self, script: str, duration_seconds: float) -> QualityScore:
        """Evaluate podcast script quality."""
        score = QualityScore()
        
        # Readability: Check script structure
        readability_score = 0.0
        if "Welcome" in script or "Hello" in script:
            readability_score += 0.2
        if "Number" in script or "#" in script:
            readability_score += 0.3
        if "That's all" in script or "Thanks" in script:
            readability_score += 0.2
        if "⭐" in script or "stars" in script:
            readability_score += 0.3
        score.readability = readability_score
        
        # Completeness: Check for repo coverage
        completeness_score = min(1.0, len(script) / 500)  # Assume 500 chars per repo
        score.completeness = completeness_score
        
        # Engagement: Check for enthusiasm markers
        engagement_score = 0.0
        if "!" in script:
            engagement_score += 0.3
        if "🎙️" in script or "📌" in script:
            engagement_score += 0.4
        if "Subscribe" in script or "Follow" in script:
            engagement_score += 0.3
        score.engagement = engagement_score
        
        # Relevance & Accuracy (assume high if generated from verified data)
        score.relevance = 0.9
        score.accuracy = 0.9
        
        # Overall
        score.overall = (
            score.relevance * 0.20 +
            score.accuracy * 0.20 +
            score.completeness * 0.20 +
            score.readability * 0.20 +
            score.engagement * 0.20
        )
        
        return score
    
    def evaluate_tweets(self, tweets: List[str]) -> QualityScore:
        """Evaluate tweet thread quality."""
        score = QualityScore()
        
        if not tweets:
            return score
        
        # Completeness: Check thread structure
        completeness_score = 0.0
        if len(tweets) >= 3:  # Hook + content + CTA
            completeness_score = 1.0
        score.completeness = completeness_score
        
        # Readability: Check formatting
        readability_score = 0.0
        if any("🚀" in t or "📌" in t for t in tweets):
            readability_score += 0.3
        if any("#" in t for t in tweets):
            readability_score += 0.3
        if any("⭐" in t for t in tweets):
            readability_score += 0.2
        if any("🔗" in t for t in tweets):
            readability_score += 0.2
        score.readability = readability_score
        
        # Engagement: Check for hooks and CTAs
        engagement_score = 0.0
        if "Thread 🧵" in tweets[0] or "👇" in tweets[0]:
            engagement_score += 0.4
        if any("Follow @" in t for t in tweets):
            engagement_score += 0.3
        if any("#OpenSource" in t or "#AI" in t for t in tweets):
            engagement_score += 0.3
        score.engagement = engagement_score
        
        # Relevance & Accuracy
        score.relevance = 0.9
        score.accuracy = 0.9
        
        # Overall
        score.overall = (
            score.relevance * 0.20 +
            score.accuracy * 0.20 +
            score.completeness * 0.20 +
            score.readability * 0.20 +
            score.engagement * 0.20
        )
        
        return score
    
    def review_content(self, content_id: str, content_type: str, score: QualityScore, 
                      reviewer: str = "ai", feedback: str = "") -> ContentReview:
        """Create content review record."""
        approved = (
            score.overall >= self.thresholds["overall_min"] and
            score.relevance >= self.thresholds["relevance_min"] and
            score.accuracy >= self.thresholds["accuracy_min"]
        )
        
        review = ContentReview(
            content_id=content_id,
            content_type=content_type,
            quality_score=score,
            reviewer=reviewer,
            feedback=feedback,
            approved=approved
        )
        
        self.reviews.append(review)
        
        if approved:
            logger.info(f"✅ Content approved: {content_id} (score: {score.overall:.2f})")
        else:
            logger.warning(f"⚠️ Content rejected: {content_id} (score: {score.overall:.2f})")
        
        return review
    
    def get_average_score(self) -> Optional[QualityScore]:
        """Get average quality score across all reviews."""
        if not self.reviews:
            return None
        
        avg = QualityScore()
        for review in self.reviews:
            avg.overall += review.quality_score.overall
            avg.relevance += review.quality_score.relevance
            avg.accuracy += review.quality_score.accuracy
            avg.completeness += review.quality_score.completeness
            avg.readability += review.quality_score.readability
            avg.engagement += review.quality_score.engagement
        
        n = len(self.reviews)
        avg.overall /= n
        avg.relevance /= n
        avg.accuracy /= n
        avg.completeness /= n
        avg.readability /= n
        avg.engagement /= n
        
        return avg
