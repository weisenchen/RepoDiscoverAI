#!/usr/bin/env python3
"""
Good First Issue Aggregator for RepoDiscoverAI

Fetches beginner-friendly issues from GitHub for new contributors.

Usage:
    python scripts/gfi_scraper.py
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.sqlite import get_db_connection

# Configuration
GITHUB_API_BASE = "https://api.github.com"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "good_first_issues"


class GFIScraper:
    """Aggregates Good First Issues from GitHub."""
    
    def __init__(self, github_token: Optional[str] = None):
        self.session = requests.Session()
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "RepoDiscoverAI-GFI-Scraper"
        }
        
        if github_token:
            self.headers["Authorization"] = f"token {github_token}"
        
        self.session.headers.update(self.headers)
        
        self.stats = {
            "issues_found": 0,
            "issues_imported": 0,
            "languages_processed": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
    
    def fetch_good_first_issues(self, language: Optional[str] = None,
                                limit: int = 100) -> List[Dict]:
        """Fetch issues labeled as 'good first issue'."""
        issues = []
        
        # Build search query
        query = "is:issue is:open label:\"good first issue\""
        
        if language:
            query += f" language:{language}"
        
        # Exclude very old issues
        query += " created:>2024-01-01"
        
        try:
            # GitHub Search API
            url = f"{GITHUB_API_BASE}/search/issues"
            params = {
                "q": query,
                "sort": "created",
                "order": "desc",
                "per_page": min(limit, 100)
            }
            
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                issues = data.get("items", [])
            elif response.status_code == 403:
                print(f"  Rate limited, waiting...")
                import time
                time.sleep(60)
                return self.fetch_good_first_issues(language, limit)
                
        except Exception as e:
            print(f"Error fetching GFI for {language}: {e}")
            self.stats["errors"] += 1
        
        return issues
    
    def normalize_issue(self, issue: Dict) -> Dict:
        """Normalize issue data to our schema."""
        repo = issue.get("repository_url", "").split("/")[-2:]
        if len(repo) < 2:
            repo = ["unknown", "unknown"]
        
        return {
            "github_id": issue.get("id"),
            "number": issue.get("number"),
            "title": issue.get("title", ""),
            "description": issue.get("body", "")[:500] if issue.get("body") else "",
            "state": issue.get("state", "open"),
            "url": issue.get("html_url", ""),
            "repository_full_name": f"{repo[0]}/{repo[1]}",
            "repository_owner": repo[0],
            "repository_name": repo[1],
            "labels": [l.get("name", "") for l in issue.get("labels", [])],
            "created_at": issue.get("created_at"),
            "updated_at": issue.get("updated_at"),
            "author": issue.get("user", {}).get("login", ""),
            "assignee": issue.get("assignee", {}).get("login", "") if issue.get("assignee") else None,
            "comments_count": issue.get("comments", 0),
            "language": self._detect_language(issue),
            "difficulty": "beginner",
            "source": "github_gfi"
        }
    
    def _detect_language(self, issue: Dict) -> Optional[str]:
        """Detect programming language from issue."""
        # Try to get from labels
        labels = [l.get("name", "").lower() for l in issue.get("labels", [])]
        
        language_labels = {
            "python": "Python",
            "javascript": "JavaScript",
            "java": "Java",
            "rust": "Rust",
            "go": "Go",
            "typescript": "TypeScript",
            "c++": "C++",
            "cpp": "C++",
            "ruby": "Ruby",
            "php": "PHP"
        }
        
        for label, lang in language_labels.items():
            if label in labels:
                return lang
        
        return None
    
    def save_to_database(self, issues: List[Dict]):
        """Save issues to SQLite database."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create good_first_issues table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS good_first_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                github_id INTEGER UNIQUE,
                number INTEGER,
                title TEXT,
                description TEXT,
                state TEXT,
                url TEXT,
                repository_full_name TEXT,
                repository_owner TEXT,
                repository_name TEXT,
                labels_json TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                author TEXT,
                assignee TEXT,
                comments_count INTEGER,
                language TEXT,
                difficulty TEXT,
                source TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_gfi_language 
            ON good_first_issues(language)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_gfi_repo 
            ON good_first_issues(repository_full_name)
        """)
        
        imported = 0
        for issue in issues:
            try:
                # Check if issue already exists
                cursor.execute(
                    "SELECT id FROM good_first_issues WHERE github_id = ?",
                    (issue.get("github_id"),)
                )
                if cursor.fetchone():
                    continue  # Skip duplicate
                
                # Insert issue
                cursor.execute("""
                    INSERT INTO good_first_issues (
                        github_id, number, title, description, state, url,
                        repository_full_name, repository_owner, repository_name,
                        labels_json, created_at, updated_at, author, assignee,
                        comments_count, language, difficulty, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    issue.get("github_id"),
                    issue.get("number"),
                    issue.get("title"),
                    issue.get("description", ""),
                    issue.get("state", "open"),
                    issue.get("url"),
                    issue.get("repository_full_name"),
                    issue.get("repository_owner"),
                    issue.get("repository_name"),
                    json.dumps(issue.get("labels", [])),
                    issue.get("created_at"),
                    issue.get("updated_at"),
                    issue.get("author"),
                    issue.get("assignee"),
                    issue.get("comments_count", 0),
                    issue.get("language"),
                    issue.get("difficulty", "beginner"),
                    issue.get("source", "github_gfi")
                ))
                
                imported += 1
                
            except Exception as e:
                print(f"Error saving issue {issue.get('title')}: {e}")
                self.stats["errors"] += 1
        
        conn.commit()
        conn.close()
        
        self.stats["issues_imported"] += imported
    
    def save_to_json(self, data: Dict, filename: str):
        """Save data to JSON file."""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filepath = OUTPUT_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved to {filepath}")
    
    def run(self, languages: List[str] = None, limit_per_language: int = 50):
        """Run the GFI aggregation process."""
        print("=" * 60)
        print("Good First Issue Aggregator")
        print("=" * 60)
        
        self.stats["start_time"] = datetime.now()
        
        # Default languages
        if languages is None:
            languages = [
                "Python", "JavaScript", "TypeScript", "Java", "Go",
                "Rust", "Ruby", "PHP", "C++", "Swift"
            ]
        
        all_issues = []
        
        # Fetch issues for each language
        print(f"\nFetching issues for {len(languages)} languages...")
        for i, lang in enumerate(languages):
            print(f"\n[{i+1}/{len(languages)}] {lang}...")
            
            issues = self.fetch_good_first_issues(language=lang, limit=limit_per_language)
            print(f"  Found {len(issues)} issues")
            
            if issues:
                self.stats["languages_processed"] += 1
                
                # Normalize
                normalized = [self.normalize_issue(i) for i in issues]
                all_issues.extend(normalized)
                
                # Save to database
                self.save_to_database(normalized)
        
        self.stats["issues_found"] = len(all_issues)
        
        # Save summary
        self.stats["end_time"] = datetime.now()
        self.stats["duration"] = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        # Group by language
        by_language = {}
        for issue in all_issues:
            lang = issue.get("language", "Unknown")
            if lang not in by_language:
                by_language[lang] = []
            by_language[lang].append(issue)
        
        self.save_to_json({
            "stats": self.stats,
            "by_language": {k: len(v) for k, v in by_language.items()},
            "total_issues": len(all_issues),
            "fetched_at": datetime.now().isoformat()
        }, "gfi_summary.json")
        
        # Print summary
        print("\n" + "=" * 60)
        print("GFI Aggregation Complete!")
        print("=" * 60)
        print(f"Languages processed: {self.stats['languages_processed']}")
        print(f"Issues found:        {self.stats['issues_found']}")
        print(f"Issues imported:     {self.stats['issues_imported']}")
        print(f"Errors:              {self.stats['errors']}")
        print(f"Duration:            {self.stats['duration']:.2f}s")
        print("\nBy Language:")
        for lang, count in sorted(by_language.items(), key=lambda x: -x[1]):
            print(f"  {lang}: {count}")
        print("=" * 60)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Aggregate Good First Issues from GitHub")
    parser.add_argument("--token", help="GitHub API token")
    parser.add_argument("--languages", nargs="+", help="Languages to fetch")
    parser.add_argument("--limit", type=int, default=50, help="Limit per language")
    
    args = parser.parse_args()
    
    github_token = args.token or os.getenv("GITHUB_TOKEN")
    
    scraper = GFIScraper(github_token=github_token)
    scraper.run(languages=args.languages, limit_per_language=args.limit)


if __name__ == "__main__":
    main()
