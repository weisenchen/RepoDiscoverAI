"""
Data Deduplication for RepoDiscoverAI

Detects and merges duplicate repository records in the database.

Usage:
    python -m app.core.data_dedup
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class DataDeduplicator:
    """Detects and merges duplicate repositories."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "repodiscover.db"
        self.db_path = str(db_path)
        
        self.stats = {
            "total_repos": 0,
            "duplicates_found": 0,
            "duplicates_merged": 0,
            "errors": 0
        }
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def find_duplicates_by_full_name(self) -> List[List[Dict]]:
        """Find duplicate repositories by full_name."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Find duplicate full_names
        cursor.execute("""
            SELECT full_name, COUNT(*) as count
            FROM repositories
            WHERE full_name IS NOT NULL
            GROUP BY full_name
            HAVING count > 1
        """)
        
        duplicates = []
        for row in cursor.fetchall():
            full_name = row["full_name"]
            
            # Get all repos with this full_name
            cursor.execute("""
                SELECT * FROM repositories
                WHERE full_name = ?
                ORDER BY created_at DESC
            """, (full_name,))
            
            repos = [dict(r) for r in cursor.fetchall()]
            if len(repos) > 1:
                duplicates.append(repos)
        
        conn.close()
        self.stats["duplicates_found"] = len(duplicates)
        
        return duplicates
    
    def find_duplicates_by_url(self) -> List[List[Dict]]:
        """Find duplicate repositories by URL."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Find duplicate URLs
        cursor.execute("""
            SELECT html_url, COUNT(*) as count
            FROM repositories
            WHERE html_url IS NOT NULL
            GROUP BY html_url
            HAVING count > 1
        """)
        
        duplicates = []
        for row in cursor.fetchall():
            url = row["html_url"]
            
            cursor.execute("""
                SELECT * FROM repositories
                WHERE html_url = ?
                ORDER BY created_at DESC
            """, (url,))
            
            repos = [dict(r) for r in cursor.fetchall()]
            if len(repos) > 1:
                duplicates.append(repos)
        
        conn.close()
        
        return duplicates
    
    def calculate_similarity(self, repo1: Dict, repo2: Dict) -> float:
        """Calculate similarity score between two repos (0-1)."""
        score = 0.0
        weights = 0.0
        
        # Name similarity (40%)
        if repo1.get("name") and repo2.get("name"):
            weights += 0.4
            if repo1["name"].lower() == repo2["name"].lower():
                score += 0.4
        
        # Owner similarity (30%)
        if repo1.get("owner") and repo2.get("owner"):
            weights += 0.3
            if repo1["owner"].lower() == repo2["owner"].lower():
                score += 0.3
        
        # Description similarity (20%)
        if repo1.get("description") and repo2.get("description"):
            weights += 0.2
            desc1 = repo1["description"].lower().strip()
            desc2 = repo2["description"].lower().strip()
            if desc1 == desc2:
                score += 0.2
            elif desc1 in desc2 or desc2 in desc1:
                score += 0.1
        
        # Stars similarity (10%)
        if repo1.get("stargazers_count") is not None and repo2.get("stargazers_count") is not None:
            weights += 0.1
            if repo1["stargazers_count"] == repo2["stargazers_count"]:
                score += 0.1
        
        return score / weights if weights > 0 else 0.0
    
    def merge_repositories(self, repos: List[Dict]) -> Dict:
        """Merge multiple duplicate repos into one canonical record."""
        if not repos:
            return {}
        
        # Sort by data quality (prefer more complete records)
        def quality_score(repo):
            score = 0
            if repo.get("description"): score += 1
            if repo.get("language"): score += 1
            if repo.get("topics"): score += 1
            if repo.get("stargazers_count", 0) > 0: score += 1
            if repo.get("updated_at"): score += 1
            return score
        
        repos_sorted = sorted(repos, key=quality_score, reverse=True)
        canonical = repos_sorted[0].copy()
        
        # Merge data from other records
        for repo in repos_sorted[1:]:
            # Fill in missing fields
            for field in ["description", "language", "homepage", "license"]:
                if not canonical.get(field) and repo.get(field):
                    canonical[field] = repo[field]
            
            # Merge topics
            if repo.get("topics"):
                existing_topics = set()
                if canonical.get("topics"):
                    try:
                        existing_topics = set(json.loads(canonical["topics"]))
                    except:
                        pass
                
                try:
                    new_topics = set(json.loads(repo["topics"]))
                    existing_topics.update(new_topics)
                    canonical["topics"] = json.dumps(list(existing_topics))
                except:
                    pass
            
            # Take max star count
            if repo.get("stargazers_count", 0) > canonical.get("stargazers_count", 0):
                canonical["stargazers_count"] = repo["stargazers_count"]
                canonical["forks_count"] = repo.get("forks_count", 0)
                canonical["watchers_count"] = repo.get("watchers_count", 0)
            
            # Take most recent update
            if repo.get("updated_at", "") > canonical.get("updated_at", ""):
                canonical["updated_at"] = repo["updated_at"]
        
        return canonical
    
    def save_merged_repo(self, canonical: Dict, duplicate_ids: List[int]):
        """Update canonical record and delete duplicates."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Update canonical record
            cursor.execute("""
                UPDATE repositories SET
                    description = ?,
                    language = ?,
                    homepage = ?,
                    license = ?,
                    topics = ?,
                    stargazers_count = ?,
                    forks_count = ?,
                    watchers_count = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                canonical.get("description"),
                canonical.get("language"),
                canonical.get("homepage"),
                canonical.get("license"),
                canonical.get("topics"),
                canonical.get("stargazers_count", 0),
                canonical.get("forks_count", 0),
                canonical.get("watchers_count", 0),
                canonical.get("updated_at"),
                canonical["id"]
            ))
            
            # Delete duplicate records
            for dup_id in duplicate_ids:
                cursor.execute("DELETE FROM repositories WHERE id = ?", (dup_id,))
            
            conn.commit()
            self.stats["duplicates_merged"] += 1
            
        except Exception as e:
            print(f"Error merging duplicates: {e}")
            self.stats["errors"] += 1
            conn.rollback()
        
        conn.close()
    
    def run(self, dry_run: bool = False) -> Dict:
        """Run deduplication process."""
        print("=" * 60)
        print("Data Deduplication")
        print("=" * 60)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get total repos
        cursor.execute("SELECT COUNT(*) as count FROM repositories")
        self.stats["total_repos"] = cursor.fetchone()["count"]
        
        print(f"\nTotal repositories: {self.stats['total_repos']}")
        
        # Find duplicates by full_name
        print("\n[1/2] Finding duplicates by full_name...")
        name_duplicates = self.find_duplicates_by_full_name()
        print(f"Found {len(name_duplicates)} duplicate groups")
        
        # Find duplicates by URL
        print("\n[2/2] Finding duplicates by URL...")
        url_duplicates = self.find_duplicates_by_url()
        print(f"Found {len(url_duplicates)} duplicate groups")
        
        # Merge duplicates
        all_duplicates = name_duplicates + url_duplicates
        
        # Remove overlapping duplicates
        seen_ids = set()
        unique_duplicates = []
        for dup_group in all_duplicates:
            ids = {r["id"] for r in dup_group}
            if not ids & seen_ids:
                unique_duplicates.append(dup_group)
                seen_ids.update(ids)
        
        print(f"\nMerging {len(unique_duplicates)} duplicate groups...")
        
        for i, dup_group in enumerate(unique_duplicates):
            if len(dup_group) < 2:
                continue
            
            print(f"\n  [{i+1}/{len(unique_duplicates)}] Merging {len(dup_group)} duplicates:")
            for repo in dup_group:
                print(f"    - {repo.get('full_name', 'N/A')} (ID: {repo['id']})")
            
            # Merge
            canonical = self.merge_repositories(dup_group)
            
            if canonical:
                duplicate_ids = [r["id"] for r in dup_group if r["id"] != canonical["id"]]
                
                if dry_run:
                    print(f"    [DRY RUN] Would update ID {canonical['id']}, delete {duplicate_ids}")
                else:
                    self.save_merged_repo(canonical, duplicate_ids)
                    print(f"    ✓ Merged into ID {canonical['id']}")
        
        conn.close()
        
        # Print summary
        print("\n" + "=" * 60)
        print("Deduplication Complete!")
        print("=" * 60)
        print(f"Total repos:        {self.stats['total_repos']}")
        print(f"Duplicates found:   {self.stats['duplicates_found']}")
        print(f"Duplicates merged:  {self.stats['duplicates_merged']}")
        print(f"Errors:             {self.stats['errors']}")
        print("=" * 60)
        
        return self.stats


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deduplicate repository data")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    
    args = parser.parse_args()
    
    deduplicator = DataDeduplicator()
    deduplicator.run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
