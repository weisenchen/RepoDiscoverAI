"""
GitHub API Client for RepoDiscoverAI

Provides deep integration with GitHub API for fetching detailed repository information.

Features:
- Repository details and metadata
- Contributor statistics
- Release information
- Issue tracking
- Rate limit management
"""

import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import requests


class GitHubClient:
    """Client for GitHub API with rate limit handling."""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub client.
        
        Args:
            token: GitHub personal access token (optional but recommended)
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.session = requests.Session()
        
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "RepoDiscoverAI/1.0"
        }
        
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
        
        self.session.headers.update(self.headers)
        
        # Rate limiting tracking
        self.rate_limit = {
            "core": {"remaining": 5000, "reset": 0},
            "search": {"remaining": 30, "reset": 0}
        }
        
        # Cache for frequently accessed data
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: Dict[str, datetime] = {}
    
    def _check_rate_limit(self, resource: str = "core") -> bool:
        """Check if we have rate limit remaining."""
        try:
            response = self.session.get(f"{self.BASE_URL}/rate_limit")
            if response.status_code == 200:
                data = response.json()
                resources = data.get("resources", {})
                
                for key in ["core", "search"]:
                    if key in resources:
                        self.rate_limit[key] = {
                            "remaining": resources[key].get("remaining", 0),
                            "reset": resources[key].get("reset", 0)
                        }
                
                remaining = self.rate_limit.get(resource, {}).get("remaining", 0)
                if remaining < 10:
                    print(f"Warning: Low rate limit for {resource}: {remaining}")
                    return False
                return True
        except Exception as e:
            print(f"Error checking rate limit: {e}")
        
        return True
    
    def _wait_for_rate_limit(self, resource: str = "core"):
        """Wait if rate limit is exhausted."""
        limit_info = self.rate_limit.get(resource, {})
        reset_time = limit_info.get("reset", 0)
        
        if reset_time:
            reset_datetime = datetime.fromtimestamp(reset_time)
            wait_until = reset_datetime + timedelta(seconds=5)
            now = datetime.now()
            
            if wait_until > now:
                wait_seconds = (wait_until - now).total_seconds()
                print(f"Rate limit exhausted. Waiting {wait_seconds:.0f}s...")
                time.sleep(wait_seconds)
    
    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                 use_search_limit: bool = False) -> Optional[Dict]:
        """Make a GitHub API request with rate limit handling."""
        resource = "search" if use_search_limit else "core"
        
        # Check rate limit
        if not self._check_rate_limit(resource):
            self._wait_for_rate_limit(resource)
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self.session.request(method, url, params=params)
            
            # Update rate limit info from headers
            remaining = response.headers.get("X-RateLimit-Remaining")
            reset = response.headers.get("X-RateLimit-Reset")
            
            if remaining and reset:
                self.rate_limit[resource] = {
                    "remaining": int(remaining),
                    "reset": int(reset)
                }
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                # Rate limited
                print(f"Rate limited on {endpoint}")
                self._wait_for_rate_limit(resource)
                return self._request(method, endpoint, params, use_search_limit)
            elif response.status_code == 404:
                return None
            else:
                print(f"GitHub API error {response.status_code}: {endpoint}")
                return None
                
        except Exception as e:
            print(f"Request error for {endpoint}: {e}")
            return None
    
    def get_repository(self, full_name: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Get detailed repository information.
        
        Args:
            full_name: Repository full name (e.g., 'owner/repo')
            use_cache: Whether to use cached data if available
        
        Returns:
            Repository data dictionary or None
        """
        # Check cache
        if use_cache and full_name in self._cache:
            if datetime.now() < self._cache_ttl.get(full_name, datetime.now()):
                return self._cache[full_name]
        
        endpoint = f"/repos/{full_name}"
        data = self._request("GET", endpoint)
        
        if data:
            # Cache for 1 hour
            self._cache[full_name] = data
            self._cache_ttl[full_name] = datetime.now() + timedelta(hours=1)
            
            return self._normalize_repo_data(data)
        
        return None
    
    def _normalize_repo_data(self, data: Dict) -> Dict:
        """Normalize repository data to our schema."""
        return {
            "full_name": data.get("full_name"),
            "name": data.get("name"),
            "owner": data.get("owner", {}).get("login"),
            "owner_type": data.get("owner", {}).get("type"),  # User or Organization
            "description": data.get("description", ""),
            "html_url": data.get("html_url"),
            "homepage": data.get("homepage", ""),
            "stargazers_count": data.get("stargazers_count", 0),
            "forks_count": data.get("forks_count", 0),
            "watchers_count": data.get("watchers_count", 0),
            "open_issues_count": data.get("open_issues_count", 0),
            "language": data.get("language"),
            "topics": data.get("topics", []),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "pushed_at": data.get("pushed_at"),
            "license": data.get("license", {}).get("spdx_id") if data.get("license") else None,
            "is_fork": data.get("fork", False),
            "is_archived": data.get("archived", False),
            "is_disabled": data.get("disabled", False),
            "default_branch": data.get("default_branch", "main"),
            "size": data.get("size", 0),  # KB
            "has_issues": data.get("has_issues", True),
            "has_projects": data.get("has_projects", True),
            "has_wiki": data.get("has_wiki", True),
            "has_pages": data.get("has_pages", False),
            "has_downloads": data.get("has_downloads", True),
            "forks": data.get("forks", 0),
            "open_issues": data.get("open_issues", 0),
            "watchers": data.get("watchers", 0),
            "source": "github_api"
        }
    
    def get_repository_contributors(self, full_name: str, 
                                    per_page: int = 100) -> List[Dict]:
        """Get repository contributors."""
        endpoint = f"/repos/{full_name}/contributors"
        params = {"per_page": per_page}
        data = self._request("GET", endpoint, params)
        return data or []
    
    def get_repository_languages(self, full_name: str) -> Dict[str, int]:
        """Get repository language statistics."""
        endpoint = f"/repos/{full_name}/languages"
        return self._request("GET", endpoint) or {}
    
    def get_repository_releases(self, full_name: str, 
                                per_page: int = 30) -> List[Dict]:
        """Get repository releases."""
        endpoint = f"/repos/{full_name}/releases"
        params = {"per_page": per_page}
        return self._request("GET", endpoint, params) or []
    
    def get_repository_issues(self, full_name: str, 
                              state: str = "open",
                              per_page: int = 100) -> List[Dict]:
        """Get repository issues."""
        endpoint = f"/repos/{full_name}/issues"
        params = {"state": state, "per_page": per_page}
        return self._request("GET", endpoint, params) or []
    
    def search_repositories(self, query: str, 
                           sort: str = "stars",
                           order: str = "desc",
                           per_page: int = 100,
                           page: int = 1) -> Dict:
        """
        Search repositories.
        
        Args:
            query: Search query (e.g., 'machine learning language:Python')
            sort: Sort field (stars, forks, updated)
            order: Sort order (asc, desc)
            per_page: Results per page (max 100)
            page: Page number
        
        Returns:
            Search results with total_count and items
        """
        endpoint = "/search/repositories"
        params = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": min(per_page, 100),
            "page": page
        }
        
        result = self._request("GET", endpoint, params, use_search_limit=True)
        
        if result:
            # Normalize search results
            normalized_items = []
            for item in result.get("items", []):
                normalized = self._normalize_repo_data(item)
                normalized_items.append(normalized)
            
            return {
                "total_count": result.get("total_count", 0),
                "incomplete_results": result.get("incomplete_results", False),
                "items": normalized_items
            }
        
        return {"total_count": 0, "incomplete_results": False, "items": []}
    
    def get_trending_repositories(self, since: str = "daily",
                                  language: Optional[str] = None,
                                  limit: int = 25) -> List[Dict]:
        """
        Get trending repositories (simulated via search API).
        
        Args:
            since: Time period (daily, weekly, monthly)
            language: Filter by language
            limit: Maximum results
        
        Returns:
            List of trending repositories
        """
        # Build search query for recently popular repos
        query_parts = ["stars:>100"]
        
        if language:
            query_parts.append(f"language:{language}")
        
        # For "daily" trending, look for recently updated repos
        if since == "daily":
            # Search for repos with many recent stars (approximation)
            query = " ".join(query_parts) + " sort:updated"
        elif since == "weekly":
            query = " ".join(query_parts) + " sort:stars"
        else:  # monthly
            query = " ".join(query_parts) + " sort:stars"
        
        result = self.search_repositories(query, sort="stars", 
                                         order="desc", per_page=limit)
        
        return result.get("items", [])
    
    def get_user_repositories(self, username: str, 
                             type: str = "owner",
                             sort: str = "updated",
                             per_page: int = 100) -> List[Dict]:
        """Get user's repositories."""
        endpoint = f"/users/{username}/repos"
        params = {
            "type": type,
            "sort": sort,
            "per_page": per_page
        }
        
        data = self._request("GET", endpoint, params)
        repos = []
        
        if data:
            for repo in data:
                repos.append(self._normalize_repo_data(repo))
        
        return repos
    
    def get_organization_repositories(self, org_name: str,
                                      type: str = "public",
                                      sort: str = "updated",
                                      per_page: int = 100) -> List[Dict]:
        """Get organization's repositories."""
        endpoint = f"/orgs/{org_name}/repos"
        params = {
            "type": type,
            "sort": sort,
            "per_page": per_page
        }
        
        data = self._request("GET", endpoint, params)
        repos = []
        
        if data:
            for repo in data:
                repos.append(self._normalize_repo_data(repo))
        
        return repos
    
    def get_good_first_issues(self, language: Optional[str] = None,
                              limit: int = 50) -> List[Dict]:
        """
        Get issues labeled as 'good first issue'.
        
        Args:
            language: Filter by repository language
            limit: Maximum results
        
        Returns:
            List of good first issues
        """
        query = "is:issue is:open label:\"good first issue\""
        
        if language:
            query += f" language:{language}"
        
        endpoint = "/search/issues"
        params = {
            "q": query,
            "sort": "created",
            "order": "desc",
            "per_page": min(limit, 100)
        }
        
        result = self._request("GET", endpoint, params, use_search_limit=True)
        return result.get("items", []) if result else []
    
    def clear_cache(self):
        """Clear the internal cache."""
        self._cache.clear()
        self._cache_ttl.clear()
    
    def get_rate_limit_status(self) -> Dict:
        """Get current rate limit status."""
        self._check_rate_limit()
        return self.rate_limit


# Convenience function for quick access
def get_github_client(token: Optional[str] = None) -> GitHubClient:
    """Get a GitHub client instance."""
    return GitHubClient(token=token)


if __name__ == "__main__":
    # Test the client
    client = GitHubClient()
    
    print("Testing GitHub Client...")
    print(f"Rate limit: {client.get_rate_limit_status()}")
    
    # Test repository fetch
    repo = client.get_repository("public-apis/public-apis")
    if repo:
        print(f"\nRepository: {repo['full_name']}")
        print(f"Stars: {repo['stargazers_count']}")
        print(f"Language: {repo['language']}")
        print(f"Description: {repo['description'][:100]}...")
    
    # Test search
    print("\nSearching for 'machine learning'...")
    results = client.search_repositories("machine learning language:Python", 
                                        sort="stars", limit=5)
    print(f"Found {results['total_count']} repositories")
    for repo in results['items'][:5]:
        print(f"  - {repo['full_name']} ({repo['stargazers_count']} stars)")
