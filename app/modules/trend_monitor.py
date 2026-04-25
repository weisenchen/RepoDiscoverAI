"""
RepoDiscoverAI v3.0 - GitHub Trending Monitor

Monitors GitHub trending repositories and calculates trend scores
based on multiple signals (stars, forks, issues, PRs, social mentions).
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class RepoMetrics:
    """Repository metrics for trend calculation."""
    name: str
    owner: str
    description: str
    language: str
    stars: int = 0
    forks: int = 0
    stars_today: int = 0
    forks_today: int = 0
    issues_opened_7d: int = 0
    issues_closed_7d: int = 0
    prs_merged_7d: int = 0
    total_prs: int = 0
    last_updated: str = ""
    url: str = ""
    social_mentions: int = 0
    trend_score: float = 0.0


class TrendMonitor:
    """Monitor GitHub trending repositories and calculate trend scores."""
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "RepoDiscoverAI/3.0"
        }
        if github_token:
            self.headers["Authorization"] = f"token {github_token}"
        
        self.client = httpx.AsyncClient(
            headers=self.headers,
            timeout=30.0
        )
    
    async def fetch_github_trending(self, period: str = "daily") -> List[RepoMetrics]:
        """
        Fetch trending repositories from GitHub.
        Period: daily, weekly, monthly
        """
        url = f"https://github.com/trending?since={period}"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            repos = []
            for article in soup.select("article.Box-row"):
                try:
                    repo_link = article.select_one("h2 a")
                    if not repo_link:
                        continue
                    
                    full_name = repo_link.get("href", "").strip("/")
                    owner, name = full_name.split("/") if "/" in full_name else ("", full_name)
                    
                    description = article.select_one("p")
                    desc_text = description.get_text(strip=True) if description else ""
                    
                    language = article.select_one("span[itemprop='programmingLanguage']")
                    lang = language.get_text(strip=True) if language else ""
                    
                    stars_text = article.select_one("a.Link--muted")
                    stars = 0
                    if stars_text:
                        stars_str = stars_text.get_text(strip=True).replace(",", "")
                        try:
                            stars = int(stars_str)
                        except ValueError:
                            stars = 0
                    
                    # Calculate stars today (approximation from trending page)
                    stars_today = article.select_one("span.d-inline-block.float-sm-right")
                    stars_today_val = 0
                    if stars_today:
                        try:
                            stars_today_val = int(stars_today.get_text(strip=True).replace("stars today", "").strip())
                        except ValueError:
                            stars_today_val = 0
                    
                    repo = RepoMetrics(
                        name=name,
                        owner=owner,
                        description=desc_text,
                        language=lang,
                        stars=stars,
                        stars_today=stars_today_val,
                        last_updated=datetime.now().isoformat(),
                        url=f"https://github.com/{full_name}"
                    )
                    repos.append(repo)
                except Exception as e:
                    logger.warning(f"Error parsing repo: {e}")
                    continue
            
            logger.info(f"Fetched {len(repos)} trending repos from GitHub")
            return repos[:25]  # Top 25
            
        except Exception as e:
            logger.error(f"Error fetching GitHub trending: {e}")
            return []
    
    async def fetch_github_api_data(self, owner: str, repo: str) -> Dict:
        """Fetch detailed metrics from GitHub API."""
        try:
            # Fetch repo details
            repo_url = f"https://api.github.com/repos/{owner}/{repo}"
            repo_resp = await self.client.get(repo_url)
            repo_data = repo_resp.json() if repo_resp.status_code == 200 else {}
            
            # Fetch issues (last 7 days)
            issues_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
            since = (datetime.now() - timedelta(days=7)).isoformat()
            issues_resp = await self.client.get(issues_url, params={"since": since, "state": "all"})
            issues_data = issues_resp.json() if issues_resp.status_code == 200 else []
            
            # Fetch PRs (last 7 days)
            prs_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
            prs_resp = await self.client.get(prs_url, params={"since": since, "state": "closed"})
            prs_data = prs_resp.json() if prs_resp.status_code == 200 else []
            
            return {
                "stars": repo_data.get("stargazers_count", 0),
                "forks": repo_data.get("forks_count", 0),
                "issues_opened_7d": len([i for i in issues_data if i.get("state") == "open"]),
                "issues_closed_7d": len([i for i in issues_data if i.get("state") == "closed"]),
                "prs_merged_7d": len(prs_data),
                "total_prs": repo_data.get("open_issues_count", 0),
                "language": repo_data.get("language", ""),
                "last_updated": repo_data.get("updated_at", "")
            }
        except Exception as e:
            logger.error(f"Error fetching API data for {owner}/{repo}: {e}")
            return {}
    
    def calculate_trend_score(self, repo: RepoMetrics) -> float:
        """
        Calculate trend score based on multiple signals.
        
        Trend Score = (Star Velocity × 0.3) + 
                     (Fork Velocity × 0.2) + 
                     (Issue Activity × 0.15) + 
                     (PR Merge Rate × 0.15) + 
                     (Social Mentions × 0.2)
        """
        star_velocity = repo.stars_today / max(repo.stars, 1)
        fork_velocity = repo.forks_today / max(repo.forks, 1)
        issue_activity = (repo.issues_opened_7d + repo.issues_closed_7d) / 10.0
        pr_merge_rate = repo.prs_merged_7d / max(repo.total_prs, 1)
        social_mentions = repo.social_mentions / 10.0
        
        score = (
            star_velocity * 0.3 +
            fork_velocity * 0.2 +
            issue_activity * 0.15 +
            pr_merge_rate * 0.15 +
            social_mentions * 0.2
        )
        
        return round(score, 4)
    
    async def monitor_trends(self, period: str = "daily") -> List[RepoMetrics]:
        """
        Main monitoring method.
        Fetches trending repos, enriches with API data, calculates scores.
        """
        logger.info(f"Starting trend monitoring for period: {period}")
        
        # Step 1: Fetch trending repos
        repos = await self.fetch_github_trending(period)
        
        # Step 2: Enrich with API data and calculate scores
        for repo in repos:
            api_data = await self.fetch_github_api_data(repo.owner, repo.name)
            if api_data:
                repo.stars = api_data.get("stars", repo.stars)
                repo.forks = api_data.get("forks", repo.forks)
                repo.issues_opened_7d = api_data.get("issues_opened_7d", 0)
                repo.issues_closed_7d = api_data.get("issues_closed_7d", 0)
                repo.prs_merged_7d = api_data.get("prs_merged_7d", 0)
                repo.total_prs = api_data.get("total_prs", 0)
                repo.language = api_data.get("language", repo.language)
                repo.last_updated = api_data.get("last_updated", repo.last_updated)
            
            # Calculate trend score
            repo.trend_score = self.calculate_trend_score(repo)
        
        # Step 3: Sort by trend score
        repos.sort(key=lambda r: r.trend_score, reverse=True)
        
        logger.info(f"Monitoring complete. Top repo: {repos[0].name if repos else 'None'}")
        return repos
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
