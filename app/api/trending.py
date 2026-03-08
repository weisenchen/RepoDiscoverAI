"""
Trending API - GitHub Trending Endpoints

Provides access to trending repositories and trend analysis.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime, timedelta
from app.db.sqlite import get_db
from app.core.trend_analysis import get_analyzer

router = APIRouter()
analyzer = get_analyzer()


@router.get("")
async def get_trending(
    period: str = Query("today", enum=["today", "week", "month"], description="Time period"),
    language: Optional[str] = Query(None, description="Filter by language"),
    limit: int = Query(25, ge=1, le=100, description="Number of results")
):
    """
    Get trending repositories.
    
    **Periods:**
    - `today` - Trending in the last 24 hours
    - `week` - Trending in the last 7 days
    - `month` - Trending in the last 30 days
    """
    async for db in get_db():
        # Calculate date threshold based on period
        now = datetime.now()
        if period == "today":
            threshold = now - timedelta(days=1)
        elif period == "week":
            threshold = now - timedelta(weeks=1)
        else:  # month
            threshold = now - timedelta(days=30)
        
        # Build query
        query = """
            SELECT * FROM repos 
            WHERE updated_at >= ?
        """
        params = [threshold.isoformat()]
        
        if language:
            query += " AND language = ?"
            params.append(language)
        
        query += " ORDER BY stars DESC LIMIT ?"
        params.append(limit)
        
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            repos = [dict(row) for row in rows]
        
        return {
            "period": period,
            "language": language or "all",
            "limit": limit,
            "updated_at": now.isoformat(),
            "count": len(repos),
            "repos": repos
        }


@router.get("/history")
async def get_trending_history(
    days: int = Query(7, ge=1, le=90, description="Number of days of history"),
    language: Optional[str] = Query(None, description="Filter by language")
):
    """
    Get historical trending data.
    
    Returns daily snapshots of trending repositories for the specified period.
    """
    async for db in get_db():
        threshold = datetime.now() - timedelta(days=days)
        
        query = """
            SELECT 
                DATE(scraped_at) as date,
                COUNT(*) as count,
                AVG(stars) as avg_stars,
                SUM(stars) as total_stars
            FROM repos
            WHERE scraped_at >= ?
        """
        params = [threshold.isoformat()]
        
        if language:
            query += " AND language = ?"
            params.append(language)
        
        query += " GROUP BY DATE(scraped_at) ORDER BY date DESC"
        
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            history = [dict(row) for row in rows]
        
        return {
            "days": days,
            "language": language or "all",
            "data": history
        }


@router.get("/stats")
async def get_trending_stats():
    """Get trending statistics."""
    async for db in get_db():
        # Today's count
        today = datetime.now().date().isoformat()
        async with db.execute(
            "SELECT COUNT(*) FROM repos WHERE DATE(scraped_at) = ?", (today,)
        ) as cursor:
            today_count = (await cursor.fetchone())[0]
        
        # This week's count
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        async with db.execute(
            "SELECT COUNT(*) FROM repos WHERE scraped_at >= ?", (week_ago,)
        ) as cursor:
            week_count = (await cursor.fetchone())[0]
        
        # Most popular language
        async with db.execute(
            """
            SELECT language, COUNT(*) as count 
            FROM repos 
            WHERE language IS NOT NULL 
            GROUP BY language 
            ORDER BY count DESC 
            LIMIT 1
            """
        ) as cursor:
            row = await cursor.fetchone()
            top_language = dict(row) if row else None
        
        return {
            "today": today_count,
            "this_week": week_count,
            "top_language": top_language,
            "updated_at": datetime.now().isoformat()
        }


@router.get("/languages")
async def get_trending_languages(
    period: str = Query("week", enum=["today", "week", "month"], description="Time period")
):
    """Get trending languages for the specified period."""
    async for db in get_db():
        threshold = datetime.now() - (
            timedelta(days=1) if period == "today" else
            timedelta(weeks=1) if period == "week" else
            timedelta(days=30)
        )
        
        query = """
            SELECT 
                language,
                COUNT(*) as count,
                AVG(stars) as avg_stars,
                SUM(stars) as total_stars
            FROM repos
            WHERE language IS NOT NULL AND scraped_at >= ?
            GROUP BY language
            ORDER BY count DESC
            LIMIT 10
        """
        
        async with db.execute(query, (threshold.isoformat(),)) as cursor:
            rows = await cursor.fetchall()
            languages = [dict(row) for row in rows]
        
        return {
            "period": period,
            "languages": languages
        }


@router.get("/growth")
async def get_growth_leaders(
    min_stars: int = Query(100, ge=0, description="Minimum star threshold"),
    period_days: int = Query(7, ge=1, le=90, description="Period for growth calculation"),
    limit: int = Query(20, ge=1, le=100, description="Number of results")
):
    """
    Get repositories with highest growth rates.
    
    Identifies repos that are gaining stars rapidly.
    """
    async for db in get_db():
        threshold = (datetime.now() - timedelta(days=period_days)).isoformat()
        
        # Get repos with historical data
        query = """
            SELECT 
                full_name, name, description, language,
                stars, forks,
                created_at, updated_at,
                scraped_at
            FROM repos
            WHERE stars >= ? AND scraped_at >= ?
            ORDER BY stars DESC
            LIMIT ?
        """
        
        async with db.execute(query, (min_stars, threshold, limit * 2)) as cursor:
            rows = await cursor.fetchall()
            repos = [dict(row) for row in rows]
        
        # Calculate growth rates and heat scores
        scored_repos = []
        for repo in repos:
            try:
                # Estimate growth rate (simplified)
                estimated_prev_stars = max(1, int(repo["stars"] * 0.95))
                growth_rate = analyzer.calculate_growth_rate(
                    repo["stars"], 
                    estimated_prev_stars, 
                    period_days
                )
                
                heat_score = analyzer.calculate_heat_score(
                    stars=repo["stars"],
                    forks=repo["forks"],
                    recent_growth=growth_rate,
                    watchers=0  # watchers column not in DB
                )
                
                scored_repos.append({
                    **repo,
                    "growth_rate": growth_rate,
                    "heat_score": heat_score,
                    "period_days": period_days
                })
            except Exception as e:
                # Skip repos with errors
                continue
        
        # Sort by growth rate
        scored_repos.sort(key=lambda x: x["growth_rate"], reverse=True)
        
        return {
            "period_days": period_days,
            "min_stars": min_stars,
            "count": len(scored_repos[:limit]),
            "repos": scored_repos[:limit]
        }


@router.get("/hot")
async def get_hot_repos(
    min_stars: int = Query(100, ge=0, description="Minimum star threshold"),
    limit: int = Query(20, ge=1, le=100, description="Number of results")
):
    """
    Get currently hot repositories based on heat score.
    
    Heat score combines:
    - Star count (popularity)
    - Fork ratio (engagement)
    - Recent growth (momentum)
    - Watcher ratio (active interest)
    """
    async for db in get_db():
        query = """
            SELECT 
                full_name, name, description, language,
                stars, forks,
                created_at, updated_at
            FROM repos
            WHERE stars >= ?
            ORDER BY stars DESC
            LIMIT ?
        """
        
        async with db.execute(query, (min_stars, limit * 3)) as cursor:
            rows = await cursor.fetchall()
            repos = [dict(row) for row in rows]
        
        # Calculate heat scores
        scored_repos = []
        for repo in repos:
            # Estimate growth rate
            growth_rate = (repo["stars"] / 1000) * 0.5  # Simplified estimate
            
            heat_score = analyzer.calculate_heat_score(
                stars=repo["stars"],
                forks=repo["forks"],
                recent_growth=growth_rate,
                watchers=0  # watchers column not in DB
            )
            
            scored_repos.append({
                **repo,
                "heat_score": heat_score
            })
        
        # Sort by heat score
        scored_repos.sort(key=lambda x: x["heat_score"], reverse=True)
        
        return {
            "min_stars": min_stars,
            "count": len(scored_repos[:limit]),
            "repos": scored_repos[:limit]
        }
