#!/usr/bin/env python3
"""
Data Migration Script

Migrates existing scraper data from legacy JSON files to the new SQLite database.

Usage:
    python scripts/migrate_data.py
"""

import json
import asyncio
from pathlib import Path
import aiosqlite
from datetime import datetime

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
LEGACY_DATA_DIR = PROJECT_ROOT / "legacy_backup" / "data"
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "repos.db"


async def migrate():
    """Migrate data from JSON files to SQLite."""
    if not DB_PATH.exists():
        print("❌ Database not found. Please start the app first to initialize.")
        print("   Run: docker-compose up -d")
        return
    
    # Find all JSON files from both legacy and current data directories
    json_files = []
    
    if LEGACY_DATA_DIR.exists():
        json_files.extend(list(LEGACY_DATA_DIR.glob("*.json")))
    
    if DATA_DIR.exists():
        # Exclude the database file and only get JSON files
        json_files.extend([f for f in DATA_DIR.glob("*.json") if f not in json_files])
    
    if not json_files:
        print("⚠️  No JSON files found.")
        print(f"   Checked: {LEGACY_DATA_DIR} and {DATA_DIR}")
        return
    
    if not json_files:
        print("⚠️  No JSON files found in legacy data directory.")
        return
    
    print(f"📂 Found {len(json_files)} JSON files to migrate")
    print()
    
    migrated = 0
    errors = 0
    skipped = 0
    
    async with aiosqlite.connect(DB_PATH) as db:
        for json_file in json_files:
            print(f"Processing {json_file.name}...")
            
            try:
                with open(json_file) as f:
                    data = json.load(f)
                
                repos = data.get("repos", [])
                
                if not repos:
                    print(f"  ⚠️  No repos found in {json_file.name}")
                    continue
                
                file_migrated = 0
                file_errors = 0
                
                for repo in repos:
                    try:
                        full_name = repo.get("full_name")
                        if not full_name:
                            file_errors += 1
                            continue
                        
                        await db.execute("""
                            INSERT OR REPLACE INTO repos 
                            (full_name, owner, name, description, language, 
                             stars, forks, url, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            full_name,
                            repo.get("owner", ""),
                            repo.get("name", ""),
                            repo.get("description", ""),
                            repo.get("language"),
                            repo.get("stars", 0),
                            repo.get("forks", 0),
                            repo.get("url", ""),
                            repo.get("scraped_at", datetime.now().isoformat())
                        ))
                        file_migrated += 1
                        
                    except Exception as e:
                        file_errors += 1
                        if file_errors <= 3:  # Only show first few errors
                            print(f"  Error migrating {repo.get('full_name', 'unknown')}: {e}")
                
                await db.commit()
                
                migrated += file_migrated
                errors += file_errors
                
                print(f"  ✅ Migrated {file_migrated} repos, {file_errors} errors")
                
            except Exception as e:
                errors += 1
                print(f"  ❌ Error processing {json_file.name}: {e}")
    
    print()
    print("=" * 50)
    print(f"✅ Migration complete!")
    print(f"   Total migrated: {migrated} repositories")
    print(f"   Total errors: {errors}")
    print()
    
    # Show summary
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM repos") as cursor:
            total = (await cursor.fetchone())[0]
        print(f"📊 Total repos in database: {total}")
        
        async with db.execute("SELECT COUNT(DISTINCT language) FROM repos WHERE language IS NOT NULL") as cursor:
            languages = (await cursor.fetchone())[0]
        print(f"📊 Languages: {languages}")
        
        async with db.execute("SELECT MAX(stars) FROM repos") as cursor:
            max_stars = (await cursor.fetchone())[0]
        print(f"📊 Max stars: {max_stars:,}")


if __name__ == "__main__":
    asyncio.run(migrate())
