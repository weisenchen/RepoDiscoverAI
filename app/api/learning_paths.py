"""
Learning Paths API - Curated Learning Path Endpoints

Provides structured learning paths for different career tracks.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from pathlib import Path
import markdown
from app.db.sqlite import get_db

router = APIRouter()

# Learning paths directory
PATHS_DIR = Path(__file__).parent.parent.parent / "collections" / "learning-paths"


# Learning paths metadata (parsed from markdown files)
# Format: path_id -> metadata
PATHS_METADATA = {
    "ai-developer": {
        "title": "AI Developer",
        "description": "Learn to build AI-powered applications",
        "duration": "6-12 months",
        "difficulty": "Intermediate"
    },
    "web-developer": {
        "title": "Web Developer", 
        "description": "Full-stack web development path",
        "duration": "6-9 months",
        "difficulty": "Beginner"
    },
    "data-scientist": {
        "title": "Data Scientist",
        "description": "Data analysis and machine learning",
        "duration": "9-12 months",
        "difficulty": "Intermediate"
    },
    "devops-engineer": {
        "title": "DevOps Engineer",
        "description": "Cloud infrastructure and automation",
        "duration": "8-12 months",
        "difficulty": "Advanced"
    },
    "mobile-developer": {
        "title": "Mobile Developer",
        "description": "iOS, Android, and cross-platform development",
        "duration": "8-12 months",
        "difficulty": "Intermediate"
    }
}


def _parse_markdown_path(path_id: str) -> Optional[dict]:
    """Parse a learning path from markdown file."""
    md_file = PATHS_DIR / f"{path_id}.md"
    
    if not md_file.exists():
        return None
    
    with open(md_file) as f:
        content = f.read()
    
    # Parse metadata from markdown
    import re
    
    # Extract title
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1) if title_match else PATHS_METADATA.get(path_id, {}).get("title", path_id)
    
    # Extract duration and difficulty from metadata section
    duration_match = re.search(r'\*\*持续时间:\*\*\s*(.+)$', content, re.MULTILINE)
    duration = duration_match.group(1) if duration_match else "Unknown"
    
    difficulty_match = re.search(r'\*\*难度:\*\*\s*(.+)$', content, re.MULTILINE)
    difficulty = difficulty_match.group(1) if difficulty_match else "Unknown"
    
    # Extract stages (H2 headers with stage emoji)
    stage_matches = re.findall(r'^##\s+🎯\s+阶段\s*\d+:\s*(.+)$', content, re.MULTILINE)
    stages = [{"name": stage.strip(), "projects": 3} for stage in stage_matches]
    
    # If no stages found, use default
    if not stages:
        stages = PATHS_METADATA.get(path_id, {}).get("stages", [])
    
    return {
        "id": path_id,
        "title": title,
        "description": PATHS_METADATA.get(path_id, {}).get("description", ""),
        "duration": duration,
        "difficulty": difficulty,
        "stages": stages,
        "content": content,
        "html": markdown.markdown(content)
    }


@router.get("")
async def list_paths():
    """List all available learning paths."""
    paths = []
    
    # Load paths from markdown files
    if PATHS_DIR.exists():
        for md_file in PATHS_DIR.glob("*.md"):
            path_id = md_file.stem
            path_data = _parse_markdown_path(path_id)
            if path_data:
                # Remove heavy content for list view
                path_data.pop("content", None)
                path_data.pop("html", None)
                paths.append(path_data)
    
    # Fallback to metadata if no markdown files
    if not paths:
        for path_id, meta in PATHS_METADATA.items():
            paths.append({
                "id": path_id,
                **meta
            })
    
    return {"paths": paths, "count": len(paths)}


@router.get("/{path_id}")
async def get_path(path_id: str):
    """Get a specific learning path with details."""
    path_data = _parse_markdown_path(path_id)
    
    if not path_data:
        raise HTTPException(status_code=404, detail=f"Learning path '{path_id}' not found")
    
    # Get recommended repos for each stage
    path_data["stages_with_repos"] = []
    for stage in path_data.get("stages", []):
        stage_repos = await _get_repos_for_stage(stage["name"])
        path_data["stages_with_repos"].append({
            **stage,
            "repos": stage_repos
        })
    
    return path_data


async def _get_repos_for_stage(stage_name: str) -> List[dict]:
    """Get recommended repositories for a learning stage."""
    # Map stage names to search queries
    stage_queries = {
        "Python Basics": ("python beginner", "Python", 10),
        "ML Fundamentals": ("machine learning", "Python", 10),
        "Deep Learning": ("deep learning pytorch tensorflow", "Python", 10),
        "LLM Applications": ("llm langchain", "Python", 10),
        "HTML/CSS/JS": ("javascript tutorial", "JavaScript", 10),
        "Frontend Framework": ("react vue angular", "JavaScript", 10),
        "Backend Development": ("fastapi flask django", "Python", 10),
        "Deployment & DevOps": ("docker kubernetes", "Python", 10),
        "Data Visualization": ("matplotlib plotly", "Python", 10),
        "Statistics": ("statistics probability", "Python", 10),
    }
    
    query, language, limit = stage_queries.get(stage_name, (stage_name.lower(), None, 10))
    
    async for db in get_db():
        sql = "SELECT * FROM repos WHERE 1=1"
        params = []
        
        sql += " AND (name LIKE ? OR description LIKE ?)"
        search_term = f"%{query.split()[0]}%"
        params.extend([search_term, search_term])
        
        if language:
            sql += " AND language = ?"
            params.append(language)
        
        sql += " ORDER BY stars DESC LIMIT ?"
        params.append(limit)
        
        async with db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    return []


@router.get("/{path_id}/progress")
async def get_path_progress(path_id: str, completed_stages: str = Query("", description="Comma-separated completed stage names")):
    """Get learning path progress."""
    if path_id not in DEFAULT_PATHS:
        raise HTTPException(status_code=404, detail="Learning path not found")
    
    path_data = DEFAULT_PATHS[path_id]
    stages = path_data.get("stages", [])
    
    completed = [s.strip() for s in completed_stages.split(",") if s.strip()]
    completed_count = len([s for s in completed if s in [stage["name"] for stage in stages]])
    total_stages = len(stages)
    
    progress_percentage = (completed_count / total_stages * 100) if total_stages > 0 else 0
    
    return {
        "path_id": path_id,
        "total_stages": total_stages,
        "completed_stages": completed_count,
        "progress_percentage": round(progress_percentage, 1),
        "next_stage": stages[completed_count]["name"] if completed_count < total_stages else None
    }


@router.get("/suggestions")
async def get_path_suggestions(interest: str = Query(..., description="User's area of interest")):
    """Get learning path suggestions based on interest."""
    interest_lower = interest.lower()
    
    suggestions = []
    for path_id, path_data in DEFAULT_PATHS.items():
        # Simple keyword matching
        if any(kw in interest_lower for kw in ["ai", "ml", "machine learning", "llm"]):
            if path_id == "ai-developer":
                suggestions.append(path_data)
        elif any(kw in interest_lower for kw in ["web", "frontend", "backend", "fullstack"]):
            if path_id == "web-developer":
                suggestions.append(path_data)
        elif any(kw in interest_lower for kw in ["data", "analytics", "science"]):
            if path_id == "data-scientist":
                suggestions.append(path_data)
    
    # If no match, return all
    if not suggestions:
        suggestions = list(DEFAULT_PATHS.values())
    
    return {"suggestions": suggestions}
