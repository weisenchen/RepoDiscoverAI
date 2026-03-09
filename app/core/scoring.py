"""
Project Scoring Algorithm for RepoDiscoverAI

Calculates health, quality, and activity scores for repositories.

Usage:
    python -m app.core.scoring
"""

import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path


class ProjectScorer:
    """Calculates repository quality scores."""
    
    def __init__(self):
        # Weights for different metrics
        self.weights = {
            "popularity": 0.30,      # Stars, forks, watchers
            "activity": 0.25,        # Recent commits, updates
            "quality": 0.25,         # Documentation, issues handling
            "community": 0.20        # Contributors, issue responses
        }
    
    def calculate_health_score(self, repo: Dict) -> float:
        """
        Calculate overall health score (0-100).
        
        Factors:
        - Star to fork ratio
        - Open vs closed issues
        - Recent activity
        - Documentation presence
        """
        score = 0.0
        
        # Star/Fork ratio (25 points)
        stars = repo.get("stargazers_count", 0)
        forks = repo.get("forks_count", 0)
        if stars > 0:
            fork_ratio = forks / stars
            # Ideal ratio is around 0.1-0.3
            if 0.1 <= fork_ratio <= 0.3:
                score += 25
            elif 0.05 <= fork_ratio < 0.1 or 0.3 < fork_ratio <= 0.5:
                score += 20
            else:
                score += 10
        
        # Watcher engagement (15 points)
        watchers = repo.get("watchers_count", 0)
        if watchers > 0:
            watcher_ratio = watchers / max(stars, 1)
            score += min(15, watcher_ratio * 100)
        
        # Has documentation (20 points)
        if repo.get("description") and len(repo.get("description", "")) > 20:
            score += 10
        if repo.get("homepage"):
            score += 5
        if repo.get("license"):
            score += 5
        
        # Not archived (20 points)
        if not repo.get("is_archived", False):
            score += 20
        
        # Has topics (10 points)
        topics = repo.get("topics", [])
        if isinstance(topics, str):
            try:
                topics = json.loads(topics)
            except:
                topics = []
        if topics and len(topics) > 0:
            score += 10
        
        # Has language (10 points)
        if repo.get("language"):
            score += 10
        
        return min(100, max(0, score))
    
    def calculate_quality_score(self, repo: Dict) -> float:
        """
        Calculate code quality score (0-100).
        
        Factors:
        - Repository size
        - License presence
        - Issue/Pull Request handling
        - Release frequency
        """
        score = 0.0
        
        # Repository size (20 points)
        size = repo.get("size", 0)  # in KB
        if size > 10000:  # > 10MB
            score += 20
        elif size > 1000:  # > 1MB
            score += 15
        elif size > 100:  # > 100KB
            score += 10
        
        # Has license (20 points)
        if repo.get("license"):
            score += 20
        
        # Has issues enabled (15 points)
        if repo.get("has_issues", True):
            score += 15
        
        # Has wiki (10 points)
        if repo.get("has_wiki", False):
            score += 10
        
        # Has pages (10 points)
        if repo.get("has_pages", False):
            score += 10
        
        # Not a fork (15 points)
        if not repo.get("is_fork", False):
            score += 15
        
        # Has README (inferred from description quality) (10 points)
        desc = repo.get("description", "")
        if desc and len(desc) > 50:
            score += 10
        
        return min(100, max(0, score))
    
    def calculate_activity_score(self, repo: Dict) -> float:
        """
        Calculate activity score (0-100).
        
        Factors:
        - Last update recency
        - Push frequency
        - Recent commits
        """
        score = 0.0
        
        # Last update recency (50 points)
        updated_at = repo.get("updated_at")
        if updated_at:
            try:
                if isinstance(updated_at, str):
                    update_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                else:
                    update_date = updated_at
                
                days_since_update = (datetime.now() - update_date.replace(tzinfo=None)).days
                
                if days_since_update <= 7:
                    score += 50
                elif days_since_update <= 30:
                    score += 40
                elif days_since_update <= 90:
                    score += 30
                elif days_since_update <= 180:
                    score += 20
                elif days_since_update <= 365:
                    score += 10
            except:
                pass
        
        # Pushed at recency (30 points)
        pushed_at = repo.get("pushed_at")
        if pushed_at:
            try:
                if isinstance(pushed_at, str):
                    push_date = datetime.fromisoformat(pushed_at.replace('Z', '+00:00'))
                else:
                    push_date = pushed_at
                
                days_since_push = (datetime.now() - push_date.replace(tzinfo=None)).days
                
                if days_since_push <= 7:
                    score += 30
                elif days_since_push <= 30:
                    score += 25
                elif days_since_push <= 90:
                    score += 15
                elif days_since_push <= 180:
                    score += 10
            except:
                pass
        
        # Open issues activity (20 points)
        open_issues = repo.get("open_issues_count", 0)
        total_issues = open_issues  # Simplified
        if total_issues > 0:
            # Having some open issues is normal
            if open_issues < 10:
                score += 20
            elif open_issues < 50:
                score += 15
            elif open_issues < 100:
                score += 10
            else:
                score += 5
        else:
            score += 15  # No issues could mean good quality or no usage
        
        return min(100, max(0, score))
    
    def calculate_popularity_score(self, repo: Dict) -> float:
        """Calculate popularity score based on stars, forks, watchers."""
        stars = repo.get("stargazers_count", 0)
        forks = repo.get("forks_count", 0)
        watchers = repo.get("watchers_count", 0)
        
        # Logarithmic scaling for stars
        if stars > 0:
            star_score = min(50, math.log10(stars + 1) * 10)
        else:
            star_score = 0
        
        # Fork score
        if forks > 0:
            fork_score = min(30, math.log10(forks + 1) * 8)
        else:
            fork_score = 0
        
        # Watcher score
        if watchers > 0:
            watcher_score = min(20, math.log10(watchers + 1) * 10)
        else:
            watcher_score = 0
        
        return min(100, star_score + fork_score + watcher_score)
    
    def calculate_overall_score(self, repo: Dict) -> Dict:
        """Calculate all scores and return comprehensive result."""
        health = self.calculate_health_score(repo)
        quality = self.calculate_quality_score(repo)
        activity = self.calculate_activity_score(repo)
        popularity = self.calculate_popularity_score(repo)
        
        # Weighted overall score
        overall = (
            health * 0.30 +
            quality * 0.25 +
            activity * 0.25 +
            popularity * 0.20
        )
        
        # Determine grade
        if overall >= 90:
            grade = "S"
        elif overall >= 80:
            grade = "A"
        elif overall >= 70:
            grade = "B"
        elif overall >= 60:
            grade = "C"
        elif overall >= 50:
            grade = "D"
        else:
            grade = "F"
        
        return {
            "overall": round(overall, 2),
            "grade": grade,
            "health": round(health, 2),
            "quality": round(quality, 2),
            "activity": round(activity, 2),
            "popularity": round(popularity, 2),
            "breakdown": {
                "health_weight": 0.30,
                "quality_weight": 0.25,
                "activity_weight": 0.25,
                "popularity_weight": 0.20
            }
        }
    
    def score_repository(self, repo: Dict) -> Dict:
        """Score a single repository."""
        return self.calculate_overall_score(repo)
    
    def score_batch(self, repos: List[Dict]) -> List[Dict]:
        """Score multiple repositories."""
        results = []
        for repo in repos:
            scores = self.calculate_overall_score(repo)
            scores["full_name"] = repo.get("full_name", "")
            results.append(scores)
        
        # Sort by overall score
        results.sort(key=lambda x: x["overall"], reverse=True)
        
        return results


def main():
    """Test the scoring system."""
    # Test with sample repo
    test_repo = {
        "full_name": "test/repo",
        "stargazers_count": 1500,
        "forks_count": 300,
        "watchers_count": 50,
        "description": "A great project with lots of features",
        "language": "Python",
        "license": "MIT",
        "is_archived": False,
        "is_fork": False,
        "has_issues": True,
        "has_wiki": True,
        "has_pages": False,
        "size": 5000,
        "updated_at": datetime.now().isoformat(),
        "pushed_at": datetime.now().isoformat(),
        "open_issues_count": 25,
        "topics": ["machine-learning", "python", "ai"]
    }
    
    scorer = ProjectScorer()
    scores = scorer.score_repository(test_repo)
    
    print("=" * 60)
    print("Repository Score Report")
    print("=" * 60)
    print(f"Repository: {test_repo['full_name']}")
    print(f"Overall Score: {scores['overall']} (Grade: {scores['grade']})")
    print(f"  - Health:     {scores['health']}")
    print(f"  - Quality:    {scores['quality']}")
    print(f"  - Activity:   {scores['activity']}")
    print(f"  - Popularity: {scores['popularity']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
