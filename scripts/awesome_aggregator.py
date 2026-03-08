#!/usr/bin/env python3
"""
Awesome Lists Aggregator for RepoDiscoverAI

Fetches awesome-lists from GitHub and imports them into the database.
Target: 50+ awesome lists, 5000+ repositories

Usage:
    python scripts/awesome_aggregator.py
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.sqlite import get_db_connection, init_db

# Configuration
GITHUB_API_BASE = "https://api.github.com"
AWESOME_LIST_OWNER = "sindresorhus"
AWESOME_LIST_REPO = "awesome"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "awesome_lists"

class AwesomeAggregator:
    """Aggregates awesome lists from GitHub."""
    
    def __init__(self, github_token: Optional[str] = None):
        self.session = requests.Session()
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "RepoDiscoverAI-Awesome-Aggregator"
        }
        if github_token:
            self.headers["Authorization"] = f"token {github_token}"
        self.session.headers.update(self.headers)
        
        # Rate limiting
        self.requests_made = 0
        self.rate_limit_remaining = 5000
        
        # Statistics
        self.stats = {
            "lists_found": 0,
            "lists_processed": 0,
            "repos_imported": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
    
    def check_rate_limit(self) -> bool:
        """Check GitHub API rate limit."""
        try:
            response = self.session.get(f"{GITHUB_API_BASE}/rate_limit")
            if response.status_code == 200:
                data = response.json()
                core = data["resources"]["core"]
                self.rate_limit_remaining = core["remaining"]
                print(f"Rate limit remaining: {self.rate_limit_remaining}")
                return self.rate_limit_remaining > 100
        except Exception as e:
            print(f"Error checking rate limit: {e}")
        return True
    
    def fetch_awesome_readme(self) -> Optional[str]:
        """Fetch the main awesome README.md content."""
        url = f"{GITHUB_API_BASE}/repos/{AWESOME_LIST_OWNER}/{AWESOME_LIST_REPO}/readme"
        try:
            response = self.session.get(url)
            if response.status_code == 200:
                import base64
                data = response.json()
                content = base64.b64decode(data["content"]).decode("utf-8")
                return content
        except Exception as e:
            print(f"Error fetching awesome README: {e}")
        return None
    
    def parse_awesome_lists(self, content: str) -> List[Dict]:
        """Parse awesome lists from the README content."""
        lists = []
        current_category = "General"
        
        for line in content.split("\n"):
            line = line.strip()
            
            # Category header (## Category Name)
            if line.startswith("## "):
                current_category = line.replace("## ", "").strip()
                continue
            
            # List item (- [List Name](url) - Description)
            if line.startswith("- [") and "](" in line:
                try:
                    # Extract name and URL
                    name_start = line.index("[") + 1
                    name_end = line.index("]")
                    url_start = line.index("(") + 1
                    url_end = line.index(")")
                    
                    name = line[name_start:name_end]
                    url = line[url_start:url_end]
                    
                    # Extract description if present
                    description = ""
                    if " - " in line[url_end:]:
                        description = line[url_end+2:].strip()
                        if description.startswith(" - "):
                            description = description[3:]
                    
                    # Only include GitHub repository lists
                    if "github.com" in url:
                        lists.append({
                            "name": name,
                            "url": url,
                            "description": description,
                            "category": current_category
                        })
                except (ValueError, IndexError):
                    continue
        
        return lists
    
    def fetch_list_repos(self, list_url: str) -> List[Dict]:
        """Fetch repositories from an awesome list README."""
        repos = []
        
        # Extract owner/repo from URL
        try:
            # URL format: https://github.com/owner/repo
            parts = list_url.rstrip("/").split("/")
            if len(parts) >= 5 and "github.com" in list_url:
                owner = parts[-2]
                repo = parts[-1]
                
                # Fetch the README
                readme_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/readme"
                response = self.session.get(readme_url)
                
                if response.status_code == 200:
                    import base64
                    import re
                    
                    data = response.json()
                    content = base64.b64decode(data["content"]).decode("utf-8")
                    
                    # Parse repository links from README
                    # Pattern: [repo-name](https://github.com/owner/repo) or [owner/repo](url)
                    github_pattern = r'\[([^\]]+)\]\(https://github\.com/([^/]+)/([^/\)]+)\)'
                    matches = re.findall(github_pattern, content)
                    
                    for match in matches:
                        repo_name = match[0]
                        repo_owner = match[1]
                        repo_path = match[2]
                        
                        repos.append({
                            "name": repo_name,
                            "full_name": f"{repo_owner}/{repo_path}",
                            "owner": repo_owner,
                            "repo": repo_path,
                            "source_list": f"{owner}/{repo}",
                            "url": f"https://github.com/{repo_owner}/{repo_path}"
                        })
                    
                    self.stats["lists_processed"] += 1
                    
        except Exception as e:
            print(f"Error fetching list {list_url}: {e}")
            self.stats["errors"] += 1
        
        return repos
    
    def fetch_repo_details(self, full_name: str) -> Optional[Dict]:
        """Fetch detailed repository information from GitHub API."""
        try:
            url = f"{GITHUB_API_BASE}/repos/{full_name}"
            response = self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "full_name": data.get("full_name"),
                    "name": data.get("name"),
                    "owner": data.get("owner", {}).get("login"),
                    "description": data.get("description", ""),
                    "html_url": data.get("html_url"),
                    "stargazers_count": data.get("stargazers_count", 0),
                    "forks_count": data.get("forks_count", 0),
                    "watchers_count": data.get("watchers_count", 0),
                    "language": data.get("language"),
                    "topics": data.get("topics", []),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "homepage": data.get("homepage", ""),
                    "license": data.get("license", {}).get("spdx_id") if data.get("license") else None,
                    "is_fork": data.get("fork", False),
                    "is_archived": data.get("archived", False),
                    "source": "awesome_list"
                }
            elif response.status_code == 404:
                print(f"  Repo not found: {full_name}")
            elif response.status_code == 403:
                print(f"  Rate limited, waiting...")
                time.sleep(60)
                
        except Exception as e:
            print(f"Error fetching repo {full_name}: {e}")
            self.stats["errors"] += 1
        
        return None
    
    def save_to_database(self, repos: List[Dict]):
        """Save repositories to SQLite database."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create awesome_lists table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS awesome_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                url TEXT,
                description TEXT,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert awesome list
        for repo in repos:
            try:
                # Check if repo already exists
                cursor.execute(
                    "SELECT id FROM repositories WHERE full_name = ?",
                    (repo.get("full_name"),)
                )
                if cursor.fetchone():
                    continue  # Skip duplicate
                
                # Insert repository
                cursor.execute("""
                    INSERT INTO repositories (
                        full_name, name, owner, description, html_url,
                        stargazers_count, forks_count, watchers_count,
                        language, topics, created_at, updated_at,
                        homepage, license, is_fork, is_archived, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    repo.get("full_name"),
                    repo.get("name"),
                    repo.get("owner"),
                    repo.get("description", ""),
                    repo.get("html_url"),
                    repo.get("stargazers_count", 0),
                    repo.get("forks_count", 0),
                    repo.get("watchers_count", 0),
                    repo.get("language"),
                    json.dumps(repo.get("topics", [])),
                    repo.get("created_at"),
                    repo.get("updated_at"),
                    repo.get("homepage", ""),
                    repo.get("license"),
                    1 if repo.get("is_fork") else 0,
                    1 if repo.get("is_archived") else 0,
                    repo.get("source", "awesome_list")
                ))
                
                self.stats["repos_imported"] += 1
                
            except Exception as e:
                print(f"Error saving repo {repo.get('full_name')}: {e}")
                self.stats["errors"] += 1
        
        conn.commit()
        conn.close()
    
    def save_to_json(self, data: Dict, filename: str):
        """Save data to JSON file."""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filepath = OUTPUT_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved to {filepath}")
    
    def run(self, max_lists: int = 50, max_repos_per_list: int = 100):
        """Run the aggregation process."""
        print("=" * 60)
        print("Awesome Lists Aggregator")
        print("=" * 60)
        
        self.stats["start_time"] = datetime.now()
        
        # Check rate limit
        if not self.check_rate_limit():
            print("Rate limit too low, aborting.")
            return
        
        # Fetch main awesome README
        print("\n[1/4] Fetching main awesome README...")
        readme_content = self.fetch_awesome_readme()
        if not readme_content:
            print("Failed to fetch awesome README.")
            return
        
        # Parse awesome lists
        print("\n[2/4] Parsing awesome lists...")
        awesome_lists = self.parse_awesome_lists(readme_content)
        self.stats["lists_found"] = len(awesome_lists)
        print(f"Found {len(awesome_lists)} awesome lists")
        
        # Save parsed lists to JSON
        self.save_to_json({
            "lists": awesome_lists,
            "total": len(awesome_lists),
            "fetched_at": datetime.now().isoformat()
        }, "awesome_lists_index.json")
        
        # Process lists and fetch repos
        print(f"\n[3/4] Fetching repositories from awesome lists (max: {max_lists})...")
        all_repos = []
        processed_lists = 0
        
        for i, awesome_list in enumerate(awesome_lists[:max_lists]):
            if not self.check_rate_limit():
                print("Rate limit reached, stopping.")
                break
            
            print(f"\n  Processing [{i+1}/{min(max_lists, len(awesome_lists))}]: {awesome_list['name']}")
            print(f"    URL: {awesome_list['url']}")
            
            # Fetch repos from this list
            list_repos = self.fetch_list_repos(awesome_list['url'])
            
            if list_repos:
                print(f"    Found {len(list_repos)} repositories in list")
                
                # Fetch detailed info for each repo (limit per list)
                for j, repo in enumerate(list_repos[:max_repos_per_list]):
                    if not self.check_rate_limit():
                        break
                    
                    print(f"      [{j+1}/{min(max_repos_per_list, len(list_repos))}] {repo['full_name']}", end="")
                    
                    details = self.fetch_repo_details(repo['full_name'])
                    if details:
                        all_repos.append(details)
                        print(f" ★{details.get('stargazers_count', 0)}", end="")
                    
                    print()  # Newline
                    
                    # Rate limiting: wait between requests
                    time.sleep(0.5)
                
                processed_lists += 1
        
        print(f"\n[4/4] Saving {len(all_repos)} repositories to database...")
        self.save_to_database(all_repos)
        
        # Save summary
        self.stats["end_time"] = datetime.now()
        self.stats["duration"] = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        summary = {
            "stats": self.stats,
            "repos": all_repos,
            "processed_lists": processed_lists
        }
        self.save_to_json(summary, "awesome_aggregation_summary.json")
        
        # Print summary
        print("\n" + "=" * 60)
        print("Aggregation Complete!")
        print("=" * 60)
        print(f"Lists found:     {self.stats['lists_found']}")
        print(f"Lists processed: {self.stats['lists_processed']}")
        print(f"Repos imported:  {self.stats['repos_imported']}")
        print(f"Errors:          {self.stats['errors']}")
        print(f"Duration:        {self.stats['duration']:.2f}s")
        print("=" * 60)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Aggregate awesome lists from GitHub")
    parser.add_argument("--token", help="GitHub API token (optional, increases rate limit)")
    parser.add_argument("--max-lists", type=int, default=50, help="Maximum lists to process")
    parser.add_argument("--max-repos", type=int, default=100, help="Maximum repos per list")
    
    args = parser.parse_args()
    
    # Get GitHub token from environment or argument
    github_token = args.token or os.getenv("GITHUB_TOKEN")
    
    aggregator = AwesomeAggregator(github_token=github_token)
    aggregator.run(max_lists=args.max_lists, max_repos_per_list=args.max_repos)


if __name__ == "__main__":
    main()
