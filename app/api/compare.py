"""
Compare API - Repository Comparison Endpoints

Allows users to compare multiple repositories side by side.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from app.db.sqlite import get_db

router = APIRouter()


@router.get("")
async def compare_repos(
    repos: str = Query(..., description="Comma-separated list of repo full_names (e.g., 'langchain/langchain,llama-index/llama_index')"),
    metrics: str = Query("all", description="Metrics to compare: all,stars,forks,activity,quality")
):
    """
    Compare multiple repositories side by side.
    
    **Example:**
    - `?repos=public-apis/public-apis,facebook/react,microsoft/vscode`
    - `?repos=langchain/langchain,llama-index/llama_index&metrics=stars,forks`
    """
    repo_list = [r.strip() for r in repos.split(",") if r.strip()]
    
    if len(repo_list) < 2:
        raise HTTPException(status_code=400, detail="Please provide at least 2 repositories to compare")
    
    if len(repo_list) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 repositories can be compared at once")
    
    async for db in get_db():
        comparison = []
        
        for repo_name in repo_list:
            async with db.execute(
                "SELECT * FROM repos WHERE full_name = ?", (repo_name,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if not row:
                    comparison.append({
                        "full_name": repo_name,
                        "error": "Repository not found",
                        "found": False
                    })
                else:
                    repo_data = dict(row)
                    repo_data["found"] = True
                    
                    # Calculate additional metrics
                    repo_data["metrics"] = await _calculate_metrics(db, repo_data, metrics)
                    
                    comparison.append(repo_data)
        
        return {
            "count": len(comparison),
            "repositories": comparison
        }


async def _calculate_metrics(db, repo: dict, metrics: str) -> dict:
    """Calculate comparison metrics for a repository."""
    result = {}
    
    # Basic metrics (always included)
    result["stars"] = repo.get("stars", 0)
    result["forks"] = repo.get("forks", 0)
    result["fork_star_ratio"] = round(repo.get("forks", 0) / max(repo.get("stars", 1), 1), 3)
    
    if metrics in ["all", "activity"]:
        # Calculate activity score based on scraped_at
        from datetime import datetime
        updated_at = repo.get("updated_at")
        if updated_at:
            try:
                updated_date = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                days_since_update = (datetime.now() - updated_date).days
                result["days_since_update"] = days_since_update
                result["activity_score"] = max(0, 100 - days_since_update)  # Higher is better
            except:
                result["days_since_update"] = None
                result["activity_score"] = None
        else:
            result["days_since_update"] = None
            result["activity_score"] = None
    
    if metrics in ["all", "quality"]:
        # Simple quality score based on stars and forks
        stars = repo.get("stars", 0)
        forks = repo.get("forks", 0)
        
        # Normalize scores (assuming max stars is 500k)
        result["quality_score"] = min(100, round((stars / 5000) + (forks / 1000), 1))
        
        # Has description?
        result["has_description"] = bool(repo.get("description"))
        
        # Has topics?
        result["has_topics"] = bool(repo.get("topics"))
    
    return result


@router.get("/suggest")
async def suggest_comparison(
    repo: str = Query(..., description="Repository to find similar repos for comparison"),
    limit: int = Query(3, ge=1, le=10, description="Number of suggestions")
):
    """
    Suggest repositories for comparison based on similarity.
    
    Finds repos with similar language and star range.
    """
    async for db in get_db():
        # Get the target repo
        async with db.execute(
            "SELECT * FROM repos WHERE full_name = ?", (repo,)
        ) as cursor:
            row = await cursor.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail=f"Repository '{repo}' not found")
            
            target = dict(row)
        
        # Find similar repos (same language, similar stars)
        target_stars = target.get("stars", 0)
        min_stars = target_stars * 0.5
        max_stars = target_stars * 2.0
        
        query = """
            SELECT * FROM repos 
            WHERE full_name != ?
            AND (language = ? OR language IS NULL)
            AND stars >= ?
            AND stars <= ?
            ORDER BY ABS(stars - ?)
            LIMIT ?
        """
        
        async with db.execute(
            query,
            (repo, target.get("language"), min_stars, max_stars, target_stars, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            suggestions = [dict(row) for row in rows]
        
        return {
            "target": {
                "full_name": target["full_name"],
                "language": target.get("language"),
                "stars": target.get("stars")
            },
            "suggestions": [
                {
                    "full_name": s["full_name"],
                    "language": s.get("language"),
                    "stars": s.get("stars"),
                    "forks": s.get("forks"),
                    "url": s.get("url")
                }
                for s in suggestions
            ]
        }


@router.get("/stats/summary")
async def get_comparison_stats():
    """Get summary statistics for comparison feature."""
    async for db in get_db():
        # Get total repos
        async with db.execute("SELECT COUNT(*) FROM repos") as cursor:
            total = (await cursor.fetchone())[0]
        
        # Get average stars
        async with db.execute("SELECT AVG(stars) FROM repos") as cursor:
            avg_stars = (await cursor.fetchone())[0] or 0
        
        # Get max stars
        async with db.execute("SELECT MAX(stars) FROM repos") as cursor:
            max_stars = (await cursor.fetchone())[0] or 0
        
        # Get top languages
        async with db.execute(
            """
            SELECT language, COUNT(*) as count 
            FROM repos 
            WHERE language IS NOT NULL 
            GROUP BY language 
            ORDER BY count DESC 
            LIMIT 5
            """
        ) as cursor:
            top_languages = [dict(row) for row in await cursor.fetchall()]
        
        return {
            "total_repos": total,
            "avg_stars": round(avg_stars, 0),
            "max_stars": max_stars,
            "top_languages": top_languages,
            "max_compare": 5
        }
