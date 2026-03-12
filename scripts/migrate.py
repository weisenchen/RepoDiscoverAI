#!/usr/bin/env python3
"""
Database Migration Script for RepoDiscoverAI
Usage: python scripts/migrate.py [command]

Commands:
    migrate     - Run all pending migrations
    rollback    - Rollback last migration
    status      - Show migration status
    seed        - Seed database with initial data
    reset       - Reset database (WARNING: deletes all data)
"""

import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import asyncpg
except ImportError:
    print("Installing required dependencies...")
    os.system("pip install asyncpg")
    import asyncpg


class DatabaseMigrator:
    def __init__(self):
        self.db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://repodiscover:changeme@localhost:5432/repodiscover"
        )
        self.migrations_dir = Path(__file__).parent.parent / "migrations"
        self.migrations_dir.mkdir(exist_ok=True)
    
    async def connect(self):
        """Establish database connection"""
        self.conn = await asyncpg.connect(self.db_url)
        print(f"✅ Connected to database")
    
    async def disconnect(self):
        """Close database connection"""
        await self.conn.close()
        print(f"🔌 Disconnected from database")
    
    async def ensure_migrations_table(self):
        """Create migrations tracking table if not exists"""
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id SERIAL PRIMARY KEY,
                version VARCHAR(50) UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """)
        print("✅ Migrations table ready")
    
    async def get_applied_migrations(self):
        """Get list of already applied migrations"""
        rows = await self.conn.fetch(
            "SELECT version FROM _migrations ORDER BY id"
        )
        return {row['version'] for row in rows}
    
    async def apply_migration(self, version: str, sql: str, description: str):
        """Apply a single migration"""
        async with self.conn.transaction():
            # Execute migration SQL
            await self.conn.execute(sql)
            
            # Record migration
            await self.conn.execute(
                "INSERT INTO _migrations (version, description) VALUES ($1, $2)",
                version, description
            )
        
        print(f"✅ Applied migration: {version} - {description}")
    
    async def migrate(self):
        """Run all pending migrations"""
        await self.ensure_migrations_table()
        applied = await self.get_applied_migrations()
        
        # Define migrations
        migrations = [
            {
                "version": "001_initial",
                "description": "Initial schema setup",
                "sql": """
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE TABLE IF NOT EXISTS repositories (
                        id SERIAL PRIMARY KEY,
                        github_id BIGINT UNIQUE NOT NULL,
                        full_name VARCHAR(255) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        owner VARCHAR(255) NOT NULL,
                        description TEXT,
                        html_url VARCHAR(511),
                        language VARCHAR(100),
                        stargazers_count INTEGER DEFAULT 0,
                        forks_count INTEGER DEFAULT 0,
                        watchers_count INTEGER DEFAULT 0,
                        open_issues_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP,
                        pushed_at TIMESTAMP,
                        is_trending BOOLEAN DEFAULT FALSE,
                        trending_score DECIMAL(10,2) DEFAULT 0,
                        last_indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE TABLE IF NOT EXISTS collections (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        is_public BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE TABLE IF NOT EXISTS collection_repos (
                        collection_id INTEGER REFERENCES collections(id) ON DELETE CASCADE,
                        repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (collection_id, repo_id)
                    );
                    
                    CREATE TABLE IF NOT EXISTS search_history (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        query TEXT NOT NULL,
                        filters JSONB,
                        results_count INTEGER,
                        searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE TABLE IF NOT EXISTS notifications (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        type VARCHAR(50) NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        message TEXT,
                        data JSONB,
                        is_read BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_repos_language ON repositories(language);
                    CREATE INDEX IF NOT EXISTS idx_repos_stars ON repositories(stargazers_count DESC);
                    CREATE INDEX IF NOT EXISTS idx_repos_trending ON repositories(is_trending) WHERE is_trending = TRUE;
                    CREATE INDEX IF NOT EXISTS idx_repos_updated ON repositories(updated_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_search_history_user ON search_history(user_id);
                    CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);
                """
            },
            {
                "version": "002_add_indexes",
                "description": "Add performance indexes",
                "sql": """
                    CREATE INDEX IF NOT EXISTS idx_repos_full_name ON repositories USING gin(to_tsvector('english', full_name));
                    CREATE INDEX IF NOT EXISTS idx_repos_description ON repositories USING gin(to_tsvector('english', coalesce(description, '')));
                    CREATE INDEX IF NOT EXISTS idx_repos_composite_trending ON repositories(is_trending, trending_score DESC) WHERE is_trending = TRUE;
                    CREATE INDEX IF NOT EXISTS idx_repos_language_stars ON repositories(language, stargazers_count DESC);
                """
            },
            {
                "version": "003_add_metrics",
                "description": "Add metrics tracking table",
                "sql": """
                    CREATE TABLE IF NOT EXISTS repo_metrics (
                        id SERIAL PRIMARY KEY,
                        repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
                        recorded_at DATE NOT NULL,
                        stargazers_count INTEGER,
                        forks_count INTEGER,
                        watchers_count INTEGER,
                        open_issues_count INTEGER,
                        contributors_count INTEGER,
                        commits_count INTEGER,
                        UNIQUE(repo_id, recorded_at)
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_metrics_repo_date ON repo_metrics(repo_id, recorded_at DESC);
                """
            },
            {
                "version": "004_add_api_keys",
                "description": "Add API keys table for authentication",
                "sql": """
                    CREATE TABLE IF NOT EXISTS api_keys (
                        id SERIAL PRIMARY KEY,
                        key_hash VARCHAR(255) UNIQUE NOT NULL,
                        user_id INTEGER REFERENCES users(id),
                        name VARCHAR(255),
                        permissions JSONB DEFAULT '{"read": true, "write": false}',
                        rate_limit INTEGER DEFAULT 1000,
                        expires_at TIMESTAMP,
                        last_used_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
                    CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
                """
            }
        ]
        
        # Apply pending migrations
        pending = [m for m in migrations if m["version"] not in applied]
        
        if not pending:
            print("✅ Database is up to date. No pending migrations.")
            return
        
        print(f"📋 Found {len(pending)} pending migration(s)")
        
        for migration in pending:
            await self.apply_migration(
                migration["version"],
                migration["sql"],
                migration["description"]
            )
        
        print(f"✅ All migrations applied successfully!")
    
    async def rollback(self):
        """Rollback last migration"""
        await self.ensure_migrations_table()
        
        last = await self.conn.fetchrow(
            "SELECT version FROM _migrations ORDER BY id DESC LIMIT 1"
        )
        
        if not last:
            print("⚠️  No migrations to rollback")
            return
        
        print(f"🔙 Rolling back migration: {last['version']}")
        # Note: In production, you'd have down migrations
        await self.conn.execute(
            "DELETE FROM _migrations WHERE version = $1",
            last['version']
        )
        print(f"✅ Rolled back: {last['version']}")
    
    async def status(self):
        """Show migration status"""
        await self.ensure_migrations_table()
        applied = await self.get_applied_migrations()
        
        migrations = [
            "001_initial",
            "002_add_indexes",
            "003_add_metrics",
            "004_add_api_keys"
        ]
        
        print("\n📊 Migration Status:\n")
        for m in migrations:
            status = "✅ Applied" if m in applied else "⏳ Pending"
            print(f"  {m}: {status}")
        print()
    
    async def seed(self):
        """Seed database with initial data"""
        print("🌱 Seeding database...")
        
        # Add sample data if needed
        await self.conn.execute("""
            INSERT INTO users (email) 
            VALUES ('admin@repodiscoverai.com')
            ON CONFLICT (email) DO NOTHING
        """)
        
        print("✅ Database seeded successfully!")
    
    async def reset(self):
        """Reset database (WARNING: deletes all data)"""
        confirm = input("⚠️  WARNING: This will delete ALL data. Type 'RESET' to confirm: ")
        
        if confirm != "RESET":
            print("❌ Reset cancelled")
            return
        
        print("🗑️  Dropping all tables...")
        
        tables = [
            "notifications",
            "search_history",
            "collection_repos",
            "collections",
            "repo_metrics",
            "api_keys",
            "repositories",
            "users",
            "_migrations"
        ]
        
        for table in tables:
            await self.conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        
        print("✅ Database reset complete!")
        print("📋 Run 'python scripts/migrate.py migrate' to recreate schema")


async def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "migrate"
    
    migrator = DatabaseMigrator()
    
    try:
        await migrator.connect()
        
        if command == "migrate":
            await migrator.migrate()
        elif command == "rollback":
            await migrator.rollback()
        elif command == "status":
            await migrator.status()
        elif command == "seed":
            await migrator.seed()
        elif command == "reset":
            await migrator.reset()
        else:
            print(f"❌ Unknown command: {command}")
            print(__doc__)
            sys.exit(1)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        await migrator.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
