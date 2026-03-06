"""
SQLite Database Configuration and Initialization

Handles database connections, schema creation, and migrations.
"""

import aiosqlite
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "data" / "repos.db"


async def init_db():
    """
    Initialize SQLite database with all required tables and indexes.
    
    Creates:
    - repos: Repository information
    - collections: User collections
    - collection_items: Collection-repo relationships
    - saved_searches: Saved search queries
    """
    # Ensure data directory exists
    DB_PATH.parent.mkdir(exist_ok=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Enable foreign keys
        await db.execute("PRAGMA foreign_keys = ON")
        
        # ===== Repos Table =====
        await db.execute("""
            CREATE TABLE IF NOT EXISTS repos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT UNIQUE NOT NULL,
                owner TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                language TEXT,
                stars INTEGER DEFAULT 0,
                forks INTEGER DEFAULT 0,
                url TEXT NOT NULL,
                topics TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("✅ Table 'repos' ready")
        
        # ===== Collections Table =====
        await db.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("✅ Table 'collections' ready")
        
        # ===== Collection Items Table =====
        await db.execute("""
            CREATE TABLE IF NOT EXISTS collection_items (
                collection_id INTEGER NOT NULL,
                repo_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (collection_id, repo_id),
                FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
                FOREIGN KEY (repo_id) REFERENCES repos(id) ON DELETE CASCADE
            )
        """)
        logger.info("✅ Table 'collection_items' ready")
        
        # ===== Saved Searches Table =====
        await db.execute("""
            CREATE TABLE IF NOT EXISTS saved_searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                query TEXT NOT NULL,
                filters TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("✅ Table 'saved_searches' ready")
        
        # ===== Create Indexes =====
        await db.execute("CREATE INDEX IF NOT EXISTS idx_stars ON repos(stars DESC)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_language ON repos(language)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_updated ON repos(updated_at DESC)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_full_name ON repos(full_name)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_topics ON repos(topics)")
        logger.info("✅ Indexes created")
        
        await db.commit()
    
    logger.info(f"📊 Database initialized at {DB_PATH}")


async def get_db():
    """
    Get a database connection with row factory enabled.
    
    Yields:
        aiosqlite.Connection: Database connection
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def execute_query(query: str, params: tuple = ()):
    """
    Execute a query and return results.
    
    Args:
        query: SQL query string
        params: Query parameters
        
    Returns:
        List of rows as dictionaries
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def insert_repo(repo_data: dict) -> int:
    """
    Insert or update a repository.
    
    Args:
        repo_data: Repository data dictionary
        
    Returns:
        Repository ID
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO repos 
            (full_name, owner, name, description, language, stars, forks, url, topics, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            repo_data.get("full_name"),
            repo_data.get("owner"),
            repo_data.get("name"),
            repo_data.get("description"),
            repo_data.get("language"),
            repo_data.get("stars", 0),
            repo_data.get("forks", 0),
            repo_data.get("url"),
            repo_data.get("topics"),
            repo_data.get("updated_at", datetime.now().isoformat())
        ))
        await db.commit()
        
        # Get the ID
        async with db.execute("SELECT id FROM repos WHERE full_name = ?", (repo_data.get("full_name"),)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def get_repo_count() -> int:
    """Get total number of repositories in database."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM repos") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
