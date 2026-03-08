"""
Trend Analysis Module

Provides algorithms for analyzing repository trends, growth rates,
and predicting future popularity.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import math


class TrendAnalyzer:
    """Analyze repository trends and growth patterns."""
    
    def __init__(self):
        pass
    
    def calculate_growth_rate(
        self, 
        current_stars: int, 
        previous_stars: int, 
        days: int = 7
    ) -> float:
        """
        Calculate star growth rate over a period.
        
        Args:
            current_stars: Current star count
            previous_stars: Star count at start of period
            days: Number of days in the period
            
        Returns:
            Daily growth rate as percentage
        """
        if previous_stars == 0:
            return 0.0
        
        total_growth = ((current_stars - previous_stars) / previous_stars) * 100
        daily_rate = total_growth / days if days > 0 else 0
        return round(daily_rate, 2)
    
    def calculate_momentum(
        self,
        star_history: List[Tuple[datetime, int]],
        window_size: int = 7
    ) -> float:
        """
        Calculate momentum score based on recent star activity.
        
        Uses exponential moving average to weight recent activity higher.
        
        Args:
            star_history: List of (timestamp, star_count) tuples
            window_size: Number of days to consider
            
        Returns:
            Momentum score (0-100)
        """
        if len(star_history) < 2:
            return 0.0
        
        # Sort by timestamp
        sorted_history = sorted(star_history, key=lambda x: x[0])
        
        # Calculate daily changes
        daily_changes = []
        for i in range(1, len(sorted_history)):
            prev_time, prev_stars = sorted_history[i - 1]
            curr_time, curr_stars = sorted_history[i]
            
            days_diff = (curr_time - prev_time).total_seconds() / 86400
            if days_diff > 0:
                daily_change = (curr_stars - prev_stars) / days_diff
                daily_changes.append((curr_time, daily_change))
        
        if not daily_changes:
            return 0.0
        
        # Apply exponential decay (more recent = higher weight)
        now = datetime.now()
        weighted_sum = 0.0
        weight_total = 0.0
        
        for time, change in daily_changes[-window_size:]:
            days_ago = (now - time).days
            weight = math.exp(-days_ago / window_size)
            weighted_sum += change * weight
            weight_total += weight
        
        if weight_total == 0:
            return 0.0
        
        # Normalize to 0-100 scale
        momentum = (weighted_sum / weight_total) * 10
        return max(0, min(100, momentum))  # Clamp to 0-100
    
    def predict_stars(
        self,
        current_stars: int,
        daily_growth_rate: float,
        days_ahead: int = 30
    ) -> int:
        """
        Predict future star count based on current growth rate.
        
        Args:
            current_stars: Current star count
            daily_growth_rate: Daily growth percentage
            days_ahead: Days to predict
            
        Returns:
            Predicted star count
        """
        if daily_growth_rate <= 0:
            return current_stars
        
        # Compound growth formula
        rate = daily_growth_rate / 100
        predicted = current_stars * ((1 + rate) ** days_ahead)
        return int(predicted)
    
    def calculate_heat_score(
        self,
        stars: int,
        forks: int,
        recent_growth: float,
        watchers: int = 0
    ) -> float:
        """
        Calculate repository heat/popularity score.
        
        Combines multiple factors:
        - Star count (base popularity)
        - Fork ratio (engagement)
        - Recent growth (momentum)
        - Watchers (active interest)
        
        Args:
            stars: Total stars
            forks: Total forks
            recent_growth: Recent growth rate (percentage)
            watchers: Watcher count
            
        Returns:
            Heat score (0-100)
        """
        # Star score (logarithmic to handle large numbers)
        star_score = min(40, math.log10(max(1, stars)) * 8)
        
        # Fork ratio score (forks/stars ratio indicates engagement)
        fork_ratio = forks / max(1, stars)
        fork_score = min(20, fork_ratio * 100)
        
        # Growth score
        growth_score = min(30, max(0, recent_growth * 3))
        
        # Watcher score
        watcher_ratio = watchers / max(1, stars)
        watcher_score = min(10, watcher_ratio * 200)
        
        total = star_score + fork_score + growth_score + watcher_score
        return round(min(100, total), 2)
    
    def detect_trending_repos(
        self,
        repos: List[Dict],
        min_stars: int = 100,
        top_n: int = 10
    ) -> List[Dict]:
        """
        Detect trending repositories from a list.
        
        Args:
            repos: List of repository dicts with stars, forks, etc.
            min_stars: Minimum star threshold
            top_n: Number of trending repos to return
            
        Returns:
            List of trending repos with heat scores
        """
        scored_repos = []
        
        for repo in repos:
            if repo.get("stars", 0) < min_stars:
                continue
            
            # Calculate heat score
            heat = self.calculate_heat_score(
                stars=repo.get("stars", 0),
                forks=repo.get("forks", 0),
                recent_growth=repo.get("growth_rate", 0),
                watchers=repo.get("watchers", 0)
            )
            
            scored_repos.append({
                **repo,
                "heat_score": heat
            })
        
        # Sort by heat score
        scored_repos.sort(key=lambda x: x["heat_score"], reverse=True)
        
        return scored_repos[:top_n]
    
    def compare_growth(
        self,
        repo_a: Dict,
        repo_b: Dict,
        period_days: int = 7
    ) -> Dict:
        """
        Compare growth between two repositories.
        
        Args:
            repo_a: First repository data
            repo_b: Second repository data
            period_days: Comparison period in days
            
        Returns:
            Comparison results
        """
        growth_a = repo_a.get("growth_rate", 0)
        growth_b = repo_b.get("growth_rate", 0)
        
        diff = growth_a - growth_b
        relative_diff = (diff / max(0.01, abs(growth_b))) * 100 if growth_b != 0 else 0
        
        return {
            "repo_a": {
                "name": repo_a.get("full_name", "Unknown"),
                "growth_rate": growth_a,
                "stars": repo_a.get("stars", 0)
            },
            "repo_b": {
                "name": repo_b.get("full_name", "Unknown"),
                "growth_rate": growth_b,
                "stars": repo_b.get("stars", 0)
            },
            "difference": round(diff, 2),
            "relative_difference": round(relative_diff, 2),
            "faster_growing": repo_a.get("full_name") if diff > 0 else repo_b.get("full_name")
        }


# Singleton instance
_analyzer = TrendAnalyzer()


def get_analyzer() -> TrendAnalyzer:
    """Get the trend analyzer instance."""
    return _analyzer
