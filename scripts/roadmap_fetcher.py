#!/usr/bin/env python3
"""
Roadmap.sh Integration for RepoDiscoverAI

Fetches career learning paths from roadmap.sh and imports them into the database.

Usage:
    python scripts/roadmap_fetcher.py
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.sqlite import get_db_connection

# Configuration
ROADMAP_API_BASE = "https://roadmap.sh"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "roadmaps"

class RoadmapFetcher:
    """Fetches learning paths from roadmap.sh"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "RepoDiscoverAI-Roadmap-Fetcher",
            "Accept": "text/html,application/json"
        })
        
        self.stats = {
            "roadmaps_found": 0,
            "roadmaps_processed": 0,
            "paths_imported": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
    
    def fetch_roadmap_list(self) -> List[Dict]:
        """Fetch the list of available roadmaps."""
        roadmaps = []
        
        try:
            # Fetch main roadmap page
            response = self.session.get(f"{ROADMAP_API_BASE}/roadmaps")
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all roadmap links
                for link in soup.select('a[href^="/roadmap/"]'):
                    href = link.get('href')
                    title = link.get_text(strip=True)
                    
                    if href and title:
                        roadmap_id = href.replace('/roadmap/', '').strip('/')
                        roadmaps.append({
                            "id": roadmap_id,
                            "title": title,
                            "url": f"{ROADMAP_API_BASE}{href}"
                        })
                
                self.stats["roadmaps_found"] = len(roadmaps)
                
        except Exception as e:
            print(f"Error fetching roadmap list: {e}")
            self.stats["errors"] += 1
        
        return roadmaps
    
    def fetch_roadmap_details(self, roadmap_id: str) -> Optional[Dict]:
        """Fetch detailed roadmap content."""
        try:
            # Try API endpoint first
            api_url = f"{ROADMAP_API_BASE}/api/roadmap/{roadmap_id}"
            response = self.session.get(api_url)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "id": roadmap_id,
                    "title": data.get("title", ""),
                    "description": data.get("description", ""),
                    "content": data.get("content", ""),
                    "nodes": data.get("nodes", []),
                    "tags": data.get("tags", []),
                    "source": "roadmap.sh"
                }
            
            # Fallback to HTML parsing
            response = self.session.get(f"{ROADMAP_API_BASE}/roadmap/{roadmap_id}")
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                title = soup.find('h1')
                title_text = title.get_text(strip=True) if title else roadmap_id
                
                description = soup.find('meta', attrs={'name': 'description'})
                desc_text = description.get('content', '') if description else ''
                
                return {
                    "id": roadmap_id,
                    "title": title_text,
                    "description": desc_text,
                    "content": "",
                    "nodes": [],
                    "tags": [],
                    "source": "roadmap.sh"
                }
                
        except Exception as e:
            print(f"Error fetching roadmap {roadmap_id}: {e}")
            self.stats["errors"] += 1
        
        return None
    
    def parse_roadmap_to_learning_path(self, roadmap: Dict) -> Dict:
        """Convert roadmap data to our learning path format."""
        # Extract stages from roadmap nodes
        stages = []
        
        nodes = roadmap.get("nodes", [])
        if nodes:
            # Group nodes into stages (simplified)
            stage_num = 1
            current_stage = {
                "stage_number": stage_num,
                "title": f"Stage {stage_num}",
                "description": "",
                "items": []
            }
            
            for node in nodes[:20]:  # Limit to first 20 nodes
                if isinstance(node, dict):
                    item = {
                        "title": node.get("label", node.get("title", "")),
                        "description": node.get("description", ""),
                        "type": "concept",
                        "order": node.get("order", 0)
                    }
                    current_stage["items"].append(item)
                    
                    # Create new stage every 5 items
                    if len(current_stage["items"]) >= 5:
                        stages.append(current_stage)
                        stage_num += 1
                        current_stage = {
                            "stage_number": stage_num,
                            "title": f"Stage {stage_num}",
                            "description": "",
                            "items": []
                        }
            
            if current_stage["items"]:
                stages.append(current_stage)
        
        return {
            "slug": roadmap["id"],
            "title": roadmap["title"],
            "description": roadmap.get("description", ""),
            "category": self._categorize_roadmap(roadmap["id"]),
            "difficulty": "beginner",
            "estimated_hours": len(stages) * 10,
            "stages": stages,
            "source": "roadmap.sh",
            "source_url": f"{ROADMAP_API_BASE}/roadmap/{roadmap['id']}"
        }
    
    def _categorize_roadmap(self, roadmap_id: str) -> str:
        """Categorize roadmap based on ID."""
        backend_ids = ["backend", "python", "java", "nodejs", "go", "rust", "php"]
        frontend_ids = ["frontend", "react", "vue", "angular", "css", "javascript"]
        data_ids = ["data-science", "machine-learning", "data-analyst"]
        devops_ids = ["devops", "kubernetes", "docker", "aws", "azure"]
        
        roadmap_id = roadmap_id.lower()
        
        if any(x in roadmap_id for x in backend_ids):
            return "backend"
        elif any(x in roadmap_id for x in frontend_ids):
            return "frontend"
        elif any(x in roadmap_id for x in data_ids):
            return "data"
        elif any(x in roadmap_id for x in devops_ids):
            return "devops"
        else:
            return "general"
    
    def save_to_database(self, learning_path: Dict):
        """Save learning path to SQLite database."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create learning_paths table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_paths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE,
                title TEXT,
                description TEXT,
                category TEXT,
                difficulty TEXT,
                estimated_hours INTEGER,
                stages_json TEXT,
                source TEXT,
                source_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create stages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_path_stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path_slug TEXT,
                stage_number INTEGER,
                title TEXT,
                description TEXT,
                items_json TEXT,
                FOREIGN KEY (path_slug) REFERENCES learning_paths(slug)
            )
        """)
        
        try:
            # Check if path already exists
            cursor.execute(
                "SELECT id FROM learning_paths WHERE slug = ?",
                (learning_path["slug"],)
            )
            if cursor.fetchone():
                print(f"  Path {learning_path['slug']} already exists, skipping")
                return
            
            # Insert learning path
            cursor.execute("""
                INSERT INTO learning_paths (
                    slug, title, description, category, difficulty,
                    estimated_hours, stages_json, source, source_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                learning_path["slug"],
                learning_path["title"],
                learning_path["description"],
                learning_path["category"],
                learning_path["difficulty"],
                learning_path["estimated_hours"],
                json.dumps(learning_path["stages"]),
                learning_path["source"],
                learning_path["source_url"]
            ))
            
            # Insert stages
            for stage in learning_path["stages"]:
                cursor.execute("""
                    INSERT INTO learning_path_stages (
                        path_slug, stage_number, title, description, items_json
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    learning_path["slug"],
                    stage["stage_number"],
                    stage["title"],
                    stage.get("description", ""),
                    json.dumps(stage["items"])
                ))
            
            self.stats["paths_imported"] += 1
            print(f"  ✓ Imported: {learning_path['title']}")
            
        except Exception as e:
            print(f"Error saving path {learning_path['slug']}: {e}")
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
    
    def run(self, max_roadmaps: int = 20):
        """Run the roadmap fetching process."""
        print("=" * 60)
        print("Roadmap.sh Fetcher")
        print("=" * 60)
        
        self.stats["start_time"] = datetime.now()
        
        # Fetch roadmap list
        print("\n[1/3] Fetching roadmap list...")
        roadmaps = self.fetch_roadmap_list()
        print(f"Found {len(roadmaps)} roadmaps")
        
        if not roadmaps:
            print("No roadmaps found, trying predefined list...")
            roadmaps = [
                {"id": "backend", "title": "Backend Developer", "url": f"{ROADMAP_API_BASE}/roadmap/backend"},
                {"id": "frontend", "title": "Frontend Developer", "url": f"{ROADMAP_API_BASE}/roadmap/frontend"},
                {"id": "devops", "title": "DevOps Engineer", "url": f"{ROADMAP_API_BASE}/roadmap/devops"},
                {"id": "python", "title": "Python Developer", "url": f"{ROADMAP_API_BASE}/roadmap/python"},
                {"id": "javascript", "title": "JavaScript Developer", "url": f"{ROADMAP_API_BASE}/roadmap/javascript"},
                {"id": "react", "title": "React Developer", "url": f"{ROADMAP_API_BASE}/roadmap/react"},
                {"id": "nodejs", "title": "Node.js Developer", "url": f"{ROADMAP_API_BASE}/roadmap/nodejs"},
                {"id": "go", "title": "Go Developer", "url": f"{ROADMAP_API_BASE}/roadmap/go"},
                {"id": "java", "title": "Java Developer", "url": f"{ROADMAP_API_BASE}/roadmap/java"},
                {"id": "rust", "title": "Rust Developer", "url": f"{ROADMAP_API_BASE}/roadmap/rust"},
                {"id": "data-science", "title": "Data Scientist", "url": f"{ROADMAP_API_BASE}/roadmap/data-science"},
                {"id": "machine-learning", "title": "Machine Learning", "url": f"{ROADMAP_API_BASE}/roadmap/machine-learning"},
                {"id": "data-analyst", "title": "Data Analyst", "url": f"{ROADMAP_API_BASE}/roadmap/data-analyst"},
                {"id": "kubernetes", "title": "Kubernetes", "url": f"{ROADMAP_API_BASE}/roadmap/kubernetes"},
                {"id": "docker", "title": "Docker", "url": f"{ROADMAP_API_BASE}/roadmap/docker"},
            ]
            self.stats["roadmaps_found"] = len(roadmaps)
        
        # Save roadmap list
        self.save_to_json({
            "roadmaps": roadmaps,
            "total": len(roadmaps),
            "fetched_at": datetime.now().isoformat()
        }, "roadmap_list.json")
        
        # Fetch and process roadmaps
        print(f"\n[2/3] Fetching roadmap details (max: {max_roadmaps})...")
        learning_paths = []
        
        for i, roadmap in enumerate(roadmaps[:max_roadmaps]):
            print(f"\n  [{i+1}/{min(max_roadmaps, len(roadmaps))}]: {roadmap['title']}")
            
            details = self.fetch_roadmap_details(roadmap["id"])
            if details:
                self.stats["roadmaps_processed"] += 1
                
                # Convert to learning path
                learning_path = self.parse_roadmap_to_learning_path(details)
                learning_paths.append(learning_path)
        
        # Save to database
        print(f"\n[3/3] Saving {len(learning_paths)} learning paths to database...")
        for path in learning_paths:
            self.save_to_database(path)
        
        # Save summary
        self.stats["end_time"] = datetime.now()
        self.stats["duration"] = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        self.save_to_json({
            "stats": self.stats,
            "learning_paths": learning_paths
        }, "roadmap_fetch_summary.json")
        
        # Print summary
        print("\n" + "=" * 60)
        print("Roadmap Fetch Complete!")
        print("=" * 60)
        print(f"Roadmaps found:     {self.stats['roadmaps_found']}")
        print(f"Roadmaps processed: {self.stats['roadmaps_processed']}")
        print(f"Paths imported:     {self.stats['paths_imported']}")
        print(f"Errors:             {self.stats['errors']}")
        print(f"Duration:           {self.stats['duration']:.2f}s")
        print("=" * 60)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch learning paths from roadmap.sh")
    parser.add_argument("--max", type=int, default=20, help="Maximum roadmaps to fetch")
    
    args = parser.parse_args()
    
    fetcher = RoadmapFetcher()
    fetcher.run(max_roadmaps=args.max)


if __name__ == "__main__":
    main()
