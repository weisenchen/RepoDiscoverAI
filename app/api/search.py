"""
Search API - Repository Search Endpoints

Provides intelligent search for GitHub repositories with filtering,
sorting, and pagination.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from app.db.sqlite import get_db, execute_query

router = APIRouter()


@router.get("")
async def search_repos(
    q: str = Query(..., min_length=1, description="Search query (repository name, description, or owner)"),
    language: Optional[str] = Query(None, description="Filter by programming language"),
    min_stars: Optional[int] = Query(None, description="Minimum star count"),
    max_stars: Optional[int] = Query(None, description="Maximum star count"),
    min_forks: Optional[int] = Query(None, description="Minimum fork count"),
    sort_by: str = Query("stars", enum=["stars", "forks", "updated", "name"], description="Sort field"),
    order: str = Query("desc", enum=["asc", "desc"], description="Sort order"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    Search repositories by query with optional filters.
    
    **Examples:**
    - `?q=machine+learning&language=Python&min_stars=1000`
    - `?q=web&sort_by=stars&order=desc&limit=50`
    """
    async for db in get_db():
        # Build query
        query = "SELECT * FROM repos WHERE 1=1"
        params = []
        
        # Search query (name, description, or full_name)
        if q:
            query += " AND (name LIKE ? OR description LIKE ? OR full_name LIKE ? OR owner LIKE ?)"
            search_term = f"%{q}%"
            params.extend([search_term, search_term, search_term, search_term])
        
        # Language filter
        if language:
            query += " AND language = ?"
            params.append(language)
        
        # Star filters
        if min_stars is not None:
            query += " AND stars >= ?"
            params.append(min_stars)
        
        if max_stars is not None:
            query += " AND stars <= ?"
            params.append(max_stars)
        
        # Fork filter
        if min_forks is not None:
            query += " AND forks >= ?"
            params.append(min_forks)
        
        # Sorting
        query += f" ORDER BY {sort_by} {order.upper()}"
        
        # Pagination
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # Execute query
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            repos = [dict(row) for row in rows]
        
        # Get total count
        count_query = "SELECT COUNT(*) FROM repos WHERE 1=1"
        count_params = []
        
        if q:
            count_query += " AND (name LIKE ? OR description LIKE ? OR full_name LIKE ? OR owner LIKE ?)"
            count_params.extend([f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"])
        
        if language:
            count_query += " AND language = ?"
            count_params.append(language)
        
        if min_stars is not None:
            count_query += " AND stars >= ?"
            count_params.append(min_stars)
        
        if max_stars is not None:
            count_query += " AND stars <= ?"
            count_params.append(max_stars)
        
        if min_forks is not None:
            count_query += " AND forks >= ?"
            count_params.append(min_forks)
        
        async with db.execute(count_query, count_params) as cursor:
            row = await cursor.fetchone()
            total = row[0] if row else 0
        
        return {
            "query": q,
            "filters": {
                "language": language,
                "min_stars": min_stars,
                "max_stars": max_stars,
                "min_forks": min_forks
            },
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total,
                "has_more": offset + len(repos) < total
            },
            "repos": repos
        }


@router.get("/suggestions")
async def search_suggestions(
    q: str = Query(..., min_length=2, description="Partial query for suggestions"),
    type: str = Query("all", enum=["all", "language", "topic", "owner"], description="Suggestion type")
):
    """
    Get search suggestions for auto-complete.
    
    **Example:** `?q=mac` returns ["machine-learning", "macos", "markdown"]
    """
    async for db in get_db():
        suggestions = set()
        
        if type in ["all", "language"]:
            async with db.execute(
                "SELECT DISTINCT language FROM repos WHERE language LIKE ? AND language IS NOT NULL LIMIT 10",
                (f"{q}%",)
            ) as cursor:
                rows = await cursor.fetchall()
                suggestions.update([row["language"] for row in rows])
        
        if type in ["all", "owner"]:
            async with db.execute(
                "SELECT DISTINCT owner FROM repos WHERE owner LIKE ? LIMIT 10",
                (f"{q}%",)
            ) as cursor:
                rows = await cursor.fetchall()
                suggestions.update([row["owner"] for row in rows])
        
        return {
            "query": q,
            "suggestions": sorted(list(suggestions))
        }


@router.get("/languages")
async def get_languages():
    """Get list of all programming languages in the database."""
    async for db in get_db():
        async with db.execute(
            """
            SELECT language, COUNT(*) as count 
            FROM repos 
            WHERE language IS NOT NULL 
            GROUP BY language 
            ORDER BY count DESC
            """
        ) as cursor:
            rows = await cursor.fetchall()
            return {
                "languages": [dict(row) for row in rows]
            }


@router.get("/stats")
async def get_search_stats():
    """Get search statistics."""
    async for db in get_db():
        async with db.execute("SELECT COUNT(*) as total FROM repos") as cursor:
            total = (await cursor.fetchone())["total"]
        
        async with db.execute(
            "SELECT COUNT(DISTINCT language) as languages FROM repos WHERE language IS NOT NULL"
        ) as cursor:
            languages = (await cursor.fetchone())["languages"]
        
        async with db.execute("SELECT MAX(stars) as max_stars FROM repos") as cursor:
            max_stars = (await cursor.fetchone())["max_stars"]
        
        return {
            "total_repos": total,
            "languages": languages,
            "max_stars": max_stars
        }
