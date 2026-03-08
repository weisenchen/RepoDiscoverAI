#!/usr/bin/env python3
"""
Data Quality Check for RepoDiscoverAI

Analyzes the database for data completeness, accuracy, and consistency.
Generates a detailed quality report.

Usage:
    python scripts/data_quality.py
"""

import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.sqlite import get_db_connection


class DataQualityChecker:
    """Checks data quality in the database."""
    
    def __init__(self):
        self.conn = get_db_connection()
        self.conn.row_factory = sqlite3.Row
        self.report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "completeness": {},
            "accuracy": {},
            "consistency": {},
            "recommendations": []
        }
    
    def check_table_stats(self) -> Dict:
        """Get basic statistics for each table."""
        cursor = self.conn.cursor()
        
        tables = ["repositories", "awesome_lists", "learning_paths", "saved_searches"]
        stats = {}
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                row = cursor.fetchone()
                if row:
                    stats[table] = {"count": row["count"]}
            except Exception as e:
                stats[table] = {"count": 0, "error": str(e)}
        
        return stats
    
    def check_completeness(self) -> Dict:
        """Check data completeness for repositories."""
        cursor = self.conn.cursor()
        
        completeness = {}
        
        # Total repositories
        cursor.execute("SELECT COUNT(*) as total FROM repositories")
        total = cursor.fetchone()["total"]
        
        if total == 0:
            return {"error": "No repositories in database"}
        
        # Check required fields
        fields = [
            ("full_name", "Full Name"),
            ("name", "Name"),
            ("owner", "Owner"),
            ("description", "Description"),
            ("html_url", "URL"),
            ("stargazers_count", "Stars"),
            ("language", "Language"),
            ("updated_at", "Updated At")
        ]
        
        for field, field_name in fields:
            cursor.execute(f"""
                SELECT COUNT(*) as count 
                FROM repositories 
                WHERE {field} IS NOT NULL AND {field} != ''
            """)
            count = cursor.fetchone()["count"]
            percentage = (count / total * 100) if total > 0 else 0
            
            completeness[field] = {
                "name": field_name,
                "count": count,
                "total": total,
                "percentage": round(percentage, 2),
                "status": "good" if percentage >= 95 else "warning" if percentage >= 80 else "critical"
            }
        
        return {
            "total_repos": total,
            "fields": completeness,
            "overall_score": self._calculate_completeness_score(completeness)
        }
    
    def _calculate_completeness_score(self, completeness: Dict) -> float:
        """Calculate overall completeness score (0-100)."""
        if "error" in completeness:
            return 0.0
        
        scores = []
        for field, data in completeness.items():
            if isinstance(data, dict) and "percentage" in data:
                scores.append(data["percentage"])
        
        return round(sum(scores) / len(scores), 2) if scores else 0.0
    
    def check_accuracy(self) -> Dict:
        """Check data accuracy."""
        cursor = self.conn.cursor()
        accuracy = {}
        
        # Check for invalid star counts (negative)
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM repositories 
            WHERE stargazers_count < 0
        """)
        invalid_stars = cursor.fetchone()["count"]
        
        # Check for invalid URLs
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM repositories 
            WHERE html_url NOT LIKE 'https://github.com/%'
            AND html_url IS NOT NULL AND html_url != ''
        """)
        invalid_urls = cursor.fetchone()["count"]
        
        # Check for future dates
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM repositories 
            WHERE updated_at > datetime('now')
        """)
        future_dates = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as total FROM repositories")
        total = cursor.fetchone()["total"]
        
        accuracy = {
            "invalid_stars": {
                "count": invalid_stars,
                "percentage": round(invalid_stars / total * 100, 4) if total > 0 else 0,
                "status": "good" if invalid_stars == 0 else "critical"
            },
            "invalid_urls": {
                "count": invalid_urls,
                "percentage": round(invalid_urls / total * 100, 4) if total > 0 else 0,
                "status": "good" if invalid_urls == 0 else "warning"
            },
            "future_dates": {
                "count": future_dates,
                "percentage": round(future_dates / total * 100, 4) if total > 0 else 0,
                "status": "good" if future_dates == 0 else "warning"
            },
            "overall_score": 100.0 - ((invalid_stars + invalid_urls + future_dates) / total * 100) if total > 0 else 0
        }
        
        return accuracy
    
    def check_consistency(self) -> Dict:
        """Check data consistency."""
        cursor = self.conn.cursor()
        consistency = {}
        
        # Check for duplicate full_names
        cursor.execute("""
            SELECT full_name, COUNT(*) as count 
            FROM repositories 
            GROUP BY full_name 
            HAVING count > 1
        """)
        duplicates = cursor.fetchall()
        
        # Check language distribution
        cursor.execute("""
            SELECT language, COUNT(*) as count 
            FROM repositories 
            WHERE language IS NOT NULL 
            GROUP BY language 
            ORDER BY count DESC 
            LIMIT 10
        """)
        languages = cursor.fetchall()
        
        # Check source distribution
        cursor.execute("""
            SELECT source, COUNT(*) as count 
            FROM repositories 
            WHERE source IS NOT NULL 
            GROUP BY source
        """)
        sources = cursor.fetchall()
        
        consistency = {
            "duplicates": {
                "count": len(duplicates),
                "items": [dict(row) for row in duplicates[:10]],
                "status": "good" if len(duplicates) == 0 else "warning"
            },
            "language_distribution": [dict(row) for row in languages],
            "source_distribution": [dict(row) for row in sources],
            "status": "good" if len(duplicates) == 0 else "warning"
        }
        
        return consistency
    
    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on quality checks."""
        recommendations = []
        
        completeness = self.report["completeness"]
        accuracy = self.report["accuracy"]
        consistency = self.report["consistency"]
        
        # Completeness recommendations
        if isinstance(completeness, dict) and "fields" in completeness:
            for field, data in completeness["fields"].items():
                if isinstance(data, dict) and data.get("status") == "critical":
                    recommendations.append(
                        f"Critical: {data['name']} field is only {data['percentage']}% complete. "
                        f"Consider re-importing data or fixing missing values."
                    )
        
        # Accuracy recommendations
        if isinstance(accuracy, dict):
            if accuracy.get("invalid_stars", {}).get("count", 0) > 0:
                recommendations.append(
                    f"Found {accuracy['invalid_stars']['count']} repositories with invalid star counts. "
                    f"Review and correct these entries."
                )
            
            if accuracy.get("invalid_urls", {}).get("count", 0) > 0:
                recommendations.append(
                    f"Found {accuracy['invalid_urls']['count']} repositories with invalid URLs. "
                    f"Verify URL format."
                )
        
        # Consistency recommendations
        if isinstance(consistency, dict) and consistency.get("duplicates", {}).get("count", 0) > 0:
            recommendations.append(
                f"Found {consistency['duplicates']['count']} duplicate repositories. "
                f"Consider running data deduplication."
            )
        
        # General recommendations
        total_repos = completeness.get("total_repos", 0) if isinstance(completeness, dict) else 0
        if total_repos < 100:
            recommendations.append(
                f"Database has only {total_repos} repositories. "
                f"Run awesome_aggregator.py to import more data."
            )
        
        if not recommendations:
            recommendations.append("Data quality is excellent! No immediate actions required.")
        
        return recommendations
    
    def run(self) -> Dict:
        """Run all quality checks and generate report."""
        print("=" * 60)
        print("Data Quality Check")
        print("=" * 60)
        
        # Table statistics
        print("\n[1/4] Checking table statistics...")
        self.report["summary"] = self.check_table_stats()
        for table, stats in self.report["summary"].items():
            print(f"  {table}: {stats.get('count', 0)} records")
        
        # Completeness
        print("\n[2/4] Checking data completeness...")
        self.report["completeness"] = self.check_completeness()
        if "overall_score" in self.report["completeness"]:
            print(f"  Completeness score: {self.report['completeness']['overall_score']}%")
        
        # Accuracy
        print("\n[3/4] Checking data accuracy...")
        self.report["accuracy"] = self.check_accuracy()
        if "overall_score" in self.report["accuracy"]:
            print(f"  Accuracy score: {self.report['accuracy']['overall_score']:.2f}%")
        
        # Consistency
        print("\n[4/4] Checking data consistency...")
        self.report["consistency"] = self.check_consistency()
        print(f"  Duplicates found: {self.report['consistency'].get('duplicates', {}).get('count', 0)}")
        
        # Recommendations
        print("\nGenerating recommendations...")
        self.report["recommendations"] = self.generate_recommendations()
        
        # Print recommendations
        print("\n" + "=" * 60)
        print("Recommendations:")
        print("=" * 60)
        for i, rec in enumerate(self.report["recommendations"], 1):
            print(f"{i}. {rec}")
        
        # Save report
        output_dir = Path(__file__).parent.parent / "data"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report_path = output_dir / "data_quality_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=2, default=str)
        
        print(f"\nReport saved to: {report_path}")
        print("=" * 60)
        
        self.conn.close()
        
        return self.report


def main():
    """Main entry point."""
    import sqlite3  # Import here for row_factory
    
    checker = DataQualityChecker()
    report = checker.run()
    
    # Exit with error code if critical issues
    completeness = report.get("completeness", {})
    if isinstance(completeness, dict):
        score = completeness.get("overall_score", 100)
        if score < 50:
            sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
