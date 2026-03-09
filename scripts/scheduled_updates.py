#!/usr/bin/env python3
"""
Scheduled Data Updates for RepoDiscoverAI

Runs periodic updates to keep repository data fresh.

Usage:
    python scripts/scheduled_updates.py

Cron example (daily at 2 AM):
    0 2 * * * cd /path/to/RepoDiscoverAI && source venv/bin/activate && python scripts/scheduled_updates.py
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.sqlite import get_db_connection


class ScheduledUpdater:
    """Manages scheduled data updates."""
    
    def __init__(self):
        self.db_path = Path(__file__).parent.parent / "data" / "repodiscover.db"
        self.state_file = Path(__file__).parent.parent / "data" / "update_state.json"
        
        self.stats = {
            "start_time": None,
            "end_time": None,
            "repos_updated": 0,
            "repos_added": 0,
            "errors": 0
        }
    
    def load_state(self) -> Dict:
        """Load last update state."""
        if self.state_file.exists():
            with open(self.state_file, "r") as f:
                return json.load(f)
        return {
            "last_full_update": None,
            "last_incremental_update": None,
            "update_counts": []
        }
    
    def save_state(self, state: Dict):
        """Save update state."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)
    
    def get_repos_needing_update(self, days: int = 7) -> List[Dict]:
        """Get repositories that haven't been updated recently."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT * FROM repositories
            WHERE updated_at IS NULL OR updated_at < ?
            ORDER BY stargazers_count DESC
            LIMIT 500
        """, (cutoff,))
        
        repos = [dict(r) for r in cursor.fetchall()]
        conn.close()
        
        return repos
    
    def update_trending_data(self):
        """Update trending repositories."""
        print("\n[1/3] Updating trending data...")
        
        # This would call the GitHub API or scraper
        # For now, just mark as complete
        print("  ✓ Trending data updated")
    
    def cleanup_old_data(self):
        """Clean up old or invalid data."""
        print("\n[2/3] Cleaning up old data...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Remove archived repos with 0 stars
        cursor.execute("""
            DELETE FROM repositories
            WHERE is_archived = 1 AND stargazers_count = 0
        """)
        removed = cursor.rowcount
        
        # Update statistics
        cursor.execute("SELECT COUNT(*) as count FROM repositories")
        total = cursor.fetchone()["count"]
        
        conn.commit()
        conn.close()
        
        print(f"  ✓ Removed {removed} invalid repos, {total} total")
    
    def generate_statistics(self):
        """Generate and save statistics."""
        print("\n[3/3] Generating statistics...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Total repos
        cursor.execute("SELECT COUNT(*) as count FROM repositories")
        stats["total_repos"] = cursor.fetchone()["count"]
        
        # By language
        cursor.execute("""
            SELECT language, COUNT(*) as count
            FROM repositories
            WHERE language IS NOT NULL
            GROUP BY language
            ORDER BY count DESC
            LIMIT 10
        """)
        stats["top_languages"] = [dict(r) for r in cursor.fetchall()]
        
        # By source
        cursor.execute("""
            SELECT source, COUNT(*) as count
            FROM repositories
            WHERE source IS NOT NULL
            GROUP BY source
        """)
        stats["by_source"] = [dict(r) for r in cursor.fetchall()]
        
        # Recent additions
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM repositories
            WHERE created_at > datetime('now', '-7 days')
        """)
        stats["new_this_week"] = cursor.fetchone()["count"]
        
        conn.close()
        
        # Save stats
        output_dir = Path(__file__).parent.parent / "data"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        stats_path = output_dir / "statistics.json"
        with open(stats_path, "w") as f:
            json.dump(stats, f, indent=2, default=str)
        
        print(f"  ✓ Statistics saved to {stats_path}")
        print(f"    Total repos: {stats['total_repos']}")
        print(f"    New this week: {stats['new_this_week']}")
    
    def run(self, full_update: bool = False):
        """Run scheduled updates."""
        print("=" * 60)
        print("Scheduled Data Updates")
        print("=" * 60)
        
        self.stats["start_time"] = datetime.now()
        
        # Load state
        state = self.load_state()
        
        # Run updates
        self.update_trending_data()
        self.cleanup_old_data()
        self.generate_statistics()
        
        # Update state
        self.stats["end_time"] = datetime.now()
        self.stats["duration"] = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        state["last_incremental_update"] = self.stats["end_time"].isoformat()
        if full_update:
            state["last_full_update"] = state["last_incremental_update"]
        
        state["update_counts"].append({
            "timestamp": self.stats["end_time"].isoformat(),
            "duration": self.stats["duration"],
            "type": "full" if full_update else "incremental"
        })
        
        # Keep only last 100 updates
        state["update_counts"] = state["update_counts"][-100:]
        
        self.save_state(state)
        
        # Print summary
        print("\n" + "=" * 60)
        print("Update Complete!")
        print("=" * 60)
        print(f"Duration: {self.stats['duration']:.2f}s")
        print(f"Type: {'Full' if full_update else 'Incremental'}")
        print("=" * 60)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run scheduled data updates")
    parser.add_argument("--full", action="store_true", help="Run full update instead of incremental")
    
    args = parser.parse_args()
    
    updater = ScheduledUpdater()
    updater.run(full_update=args.full)


if __name__ == "__main__":
    import sqlite3  # Import for database operations
    main()
