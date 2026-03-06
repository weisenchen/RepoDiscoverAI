"""
Search API - Repository Search Endpoints

Provides intelligent search for GitHub repositories with filtering,
sorting, pagination, and advanced search syntax.

Advanced Search Syntax:
- stars:>1000 - More than 1000 stars
- stars:<5000 - Less than 5000 stars
- forks:>100 - More than 100 forks
- language:Python - Specific language
- sort:stars - Sort by stars
- order:desc - Sort order (asc/desc)
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
import re
from app.db.sqlite import get_db, execute_query

router = APIRouter()


def parse_advanced_query(query: str) -> dict:
    """
    Parse advanced search syntax from query string.
    
    Supported syntax:
    - stars:>1000, stars:<5000, stars:1000..5000
    - forks:>100, forks:<500
    - language:Python
    - sort:stars, sort:forks, sort:updated
    - order:asc, order:desc
    
    Returns dict with extracted filters and cleaned query.
    """
    result = {
        "query": query,
        "min_stars": None,
        "max_stars": None,
        "min_forks": None,
        "max_forks": None,
        "language": None,
        "sort_by": None,
        "order": None,
    }
    
    # Pattern for stars:>1000, stars:<5000, stars:1000..5000
    stars_range = re.search(r'stars:(\d+)\.\.(\d+)', query)
    if stars_range:
        result["min_stars"] = int(stars_range.group(1))
        result["max_stars"] = int(stars_range.group(2))
        result["query"] = result["query"].replace(stars_range.group(0), '')
    else:
        stars_gt = re.search(r'stars:>(\d+)', query)
        if stars_gt:
            result["min_stars"] = int(stars_gt.group(1))
            result["query"] = result["query"].replace(stars_gt.group(0), '')
        
        stars_lt = re.search(r'stars:<(\d+)', query)
        if stars_lt:
            result["max_stars"] = int(stars_lt.group(1))
            result["query"] = result["query"].replace(stars_lt.group(0), '')
    
    # Pattern for forks:>100, forks:<500
    forks_gt = re.search(r'forks:>(\d+)', query)
    if forks_gt:
        result["min_forks"] = int(forks_gt.group(1))
        result["query"] = result["query"].replace(forks_gt.group(0), '')
    
    forks_lt = re.search(r'forks:<(\d+)', query)
    if forks_lt:
        result["max_forks"] = int(forks_lt.group(1))
        result["query"] = result["query"].replace(forks_lt.group(0), '')
    
    # Pattern for language:Python
    lang_match = re.search(r'language:(\w+)', query, re.IGNORECASE)
    if lang_match:
        result["language"] = lang_match.group(1)
        result["query"] = result["query"].replace(lang_match.group(0), '')
    
    # Pattern for sort:stars, sort:forks, sort:updated, sort:name
    sort_match = re.search(r'sort:(\w+)', query, re.IGNORECASE)
    if sort_match:
        sort_value = sort_match.group(1).lower()
        if sort_value in ["stars", "forks", "updated", "name"]:
            result["sort_by"] = sort_value
            result["query"] = result["query"].replace(sort_match.group(0), '')
    
    # Pattern for order:asc, order:desc
    order_match = re.search(r'order:(asc|desc)', query, re.IGNORECASE)
    if order_match:
        result["order"] = order_match.group(1).lower()
        result["query"] = result["query"].replace(order_match.group(0), '')
    
    # Clean up extra whitespace
    result["query"] = ' '.join(result["query"].split()).strip()
    
    return result


@router.get("")
async def search_repos(
    q: str = Query("", description="Search query (supports advanced syntax: stars:>1000, language:Python, sort:stars)"),
    language: Optional[str] = Query(None, description="Filter by programming language"),
    min_stars: Optional[int] = Query(None, description="Minimum star count"),
    max_stars: Optional[int] = Query(None, description="Maximum star count"),
    min_forks: Optional[int] = Query(None, description="Minimum fork count"),
    sort_by: str = Query("stars", enum=["stars", "forks", "updated", "name"], description="Sort field"),
    order: str = Query("desc", enum=["asc", "desc"], description="Sort order"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    advanced: bool = Query(False, description="Enable advanced query parsing")
):
    """
    Search repositories by query with optional filters.
    
    **Basic Examples:**
    - `?q=machine+learning&language=Python&min_stars=1000`
    - `?q=web&sort_by=stars&order=desc&limit=50`
    
    **Advanced Syntax (advanced=true):**
    - `?q=ml stars:>1000 language:Python&advanced=true`
    - `?q=web stars:1000..10000 sort:forks order:desc&advanced=true`
    """
    async for db in get_db():
        # Parse advanced query if enabled
        if advanced and q:
            parsed = parse_advanced_query(q)
            # Merge parsed filters with explicit parameters (explicit takes precedence)
            if language is None:
                language = parsed["language"]
            if min_stars is None:
                min_stars = parsed["min_stars"]
            if max_stars is None:
                max_stars = parsed["max_stars"]
            if min_forks is None:
                min_forks = parsed["min_forks"]
            if sort_by == "stars":  # Default
                sort_by = parsed["sort_by"] or sort_by
            if order == "desc":  # Default
                order = parsed["order"] or order
            q = parsed["query"]
        
        # Build query
        sql = "SELECT * FROM repos WHERE 1=1"
        params = []
        
        # Search query (name, description, or full_name)
        if q:
            sql += " AND (name LIKE ? OR description LIKE ? OR full_name LIKE ? OR owner LIKE ?)"
            search_term = f"%{q}%"
            params.extend([search_term, search_term, search_term, search_term])
        
        # Language filter
        if language:
            sql += " AND language = ?"
            params.append(language)
        
        # Star filters
        if min_stars is not None:
            sql += " AND stars >= ?"
            params.append(min_stars)
        
        if max_stars is not None:
            sql += " AND stars <= ?"
            params.append(max_stars)
        
        # Fork filter
        if min_forks is not None:
            sql += " AND forks >= ?"
            params.append(min_forks)
        
        # Sorting
        sql += f" ORDER BY {sort_by} {order.upper()}"
        
        # Pagination
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # Execute query
        async with db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            repos = [dict(row) for row in rows]
        
        # Get total count
        count_sql = "SELECT COUNT(*) FROM repos WHERE 1=1"
        count_params = []
        
        if q:
            count_sql += " AND (name LIKE ? OR description LIKE ? OR full_name LIKE ? OR owner LIKE ?)"
            count_params.extend([f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"])
        
        if language:
            count_sql += " AND language = ?"
            count_params.append(language)
        
        if min_stars is not None:
            count_sql += " AND stars >= ?"
            count_params.append(min_stars)
        
        if max_stars is not None:
            count_sql += " AND stars <= ?"
            count_params.append(max_stars)
        
        if min_forks is not None:
            count_sql += " AND forks >= ?"
            count_params.append(min_forks)
        
        async with db.execute(count_sql, count_params) as cursor:
            row = await cursor.fetchone()
            total = row[0] if row else 0
        
        return {
            "query": q,
            "filters": {
                "language": language,
                "min_stars": min_stars,
                "max_stars": max_stars,
                "min_forks": min_forks,
                "sort_by": sort_by,
                "order": order
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
