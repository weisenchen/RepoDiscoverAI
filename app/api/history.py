"""
Search History API

Track and manage user search history.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path
import sqlite3
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class SearchHistoryItem(BaseModel):
    """Search history item model."""
    id: Optional[int] = None
    query: str
    filters: Optional[Dict] = None
    results_count: int = 0
    clicked_repo_id: Optional[int] = None
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SearchHistoryResponse(BaseModel):
    """Search history response."""
    items: List[SearchHistoryItem]
    total: int
    limit: int
    offset: int


class SearchHistoryDB:
    """Search history database operations."""
    
    def __init__(self, db_path: str = "data/search_history.db"):
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self):
        """Initialize database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                filters TEXT,
                results_count INTEGER DEFAULT 0,
                clicked_repo_id INTEGER,
                user_id TEXT,
                session_id TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_query ON search_history(query)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_user ON search_history(user_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created ON search_history(created_at)
        ''')
        
        conn.commit()
        conn.close()
    
    def add_search(
        self,
        query: str,
        filters: Dict = None,
        results_count: int = 0,
        user_id: str = None,
        session_id: str = None,
        ip_address: str = None
    ) -> int:
        """Add search to history."""
        import json
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO search_history 
            (query, filters, results_count, user_id, session_id, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            query,
            json.dumps(filters) if filters else None,
            results_count,
            user_id,
            session_id,
            ip_address
        ))
        
        search_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return search_id
    
    def record_click(self, search_id: int, repo_id: int):
        """Record repo click from search."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE search_history 
            SET clicked_repo_id = ?
            WHERE id = ?
        ''', (repo_id, search_id))
        
        conn.commit()
        conn.close()
    
    def get_history(
        self,
        user_id: str = None,
        session_id: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """Get search history."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute('''
                SELECT * FROM search_history 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (user_id, limit, offset))
        elif session_id:
            cursor.execute('''
                SELECT * FROM search_history 
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (session_id, limit, offset))
        else:
            cursor.execute('''
                SELECT * FROM search_history 
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_popular_searches(self, limit: int = 20) -> List[Dict]:
        """Get popular searches."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT query, COUNT(*) as count, AVG(results_count) as avg_results
            FROM search_history
            WHERE created_at > datetime('now', '-7 days')
            GROUP BY query
            ORDER BY count DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_suggestions(self, prefix: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on prefix."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT query FROM search_history
            WHERE query LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (f"{prefix}%", limit))
        
        suggestions = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return suggestions
    
    def clear_history(self, user_id: str = None, session_id: str = None):
        """Clear search history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute(
                "DELETE FROM search_history WHERE user_id = ?",
                (user_id,)
            )
        elif session_id:
            cursor.execute(
                "DELETE FROM search_history WHERE session_id = ?",
                (session_id,)
            )
        else:
            cursor.execute("DELETE FROM search_history")
        
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict:
        """Get search statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total searches
        cursor.execute("SELECT COUNT(*) FROM search_history")
        total = cursor.fetchone()[0]
        
        # Searches today
        cursor.execute('''
            SELECT COUNT(*) FROM search_history 
            WHERE date(created_at) = date('now')
        ''')
        today = cursor.fetchone()[0]
        
        # Unique queries
        cursor.execute("SELECT COUNT(DISTINCT query) FROM search_history")
        unique_queries = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_searches": total,
            "searches_today": today,
            "unique_queries": unique_queries
        }


# Global database instance
_db: Optional[SearchHistoryDB] = None


def get_db() -> SearchHistoryDB:
    """Get or create database instance."""
    global _db
    if _db is None:
        _db = SearchHistoryDB()
    return _db


@router.get("", response_model=SearchHistoryResponse)
async def get_search_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: Optional[str] = Query(None)
):
    """Get user's search history."""
    db = get_db()
    
    items = db.get_history(user_id=user_id, limit=limit, offset=offset)
    total = len(items)
    
    return SearchHistoryResponse(
        items=[SearchHistoryItem(**item) for item in items],
        total=total,
        limit=limit,
        offset=offset
    )


@router.post("")
async def record_search(
    query: str = Query(..., min_length=1),
    filters: Optional[Dict] = None,
    results_count: int = Query(0),
    user_id: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    ip_address: Optional[str] = Query(None)
):
    """Record a search."""
    db = get_db()
    
    search_id = db.add_search(
        query=query,
        filters=filters,
        results_count=results_count,
        user_id=user_id,
        session_id=session_id,
        ip_address=ip_address
    )
    
    return {
        "id": search_id,
        "message": "Search recorded"
    }


@router.post("/click")
async def record_click(
    search_id: int = Query(...),
    repo_id: int = Query(...)
):
    """Record a repo click from search results."""
    db = get_db()
    db.record_click(search_id, repo_id)
    
    return {"message": "Click recorded"}


@router.get("/popular")
async def get_popular_searches(
    limit: int = Query(20, ge=1, le=50)
):
    """Get popular searches."""
    db = get_db()
    popular = db.get_popular_searches(limit=limit)
    
    return {
        "searches": popular,
        "period": "last_7_days"
    }


@router.get("/suggestions")
async def get_suggestions(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=20)
):
    """Get search suggestions."""
    db = get_db()
    suggestions = db.get_suggestions(q, limit=limit)
    
    return {
        "query": q,
        "suggestions": suggestions
    }


@router.delete("")
async def clear_search_history(
    user_id: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None)
):
    """Clear search history."""
    db = get_db()
    db.clear_history(user_id=user_id, session_id=session_id)
    
    return {"message": "History cleared"}


@router.get("/stats")
async def get_search_stats():
    """Get search statistics."""
    db = get_db()
    stats = db.get_stats()
    
    return stats
