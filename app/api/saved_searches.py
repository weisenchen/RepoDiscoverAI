"""
Saved Searches API - User Saved Search Endpoints

Allows users to save, manage, and reuse search queries.
"""

from fastapi import APIRouter, Query, HTTPException, Body
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from app.db.sqlite import get_db
import json

router = APIRouter()


class SavedSearchCreate(BaseModel):
    name: str
    query: str
    filters: Optional[dict] = None


class SavedSearchUpdate(BaseModel):
    name: Optional[str] = None
    query: Optional[str] = None
    filters: Optional[dict] = None


@router.get("")
async def list_saved_searches():
    """List all saved searches."""
    async for db in get_db():
        async with db.execute(
            "SELECT * FROM saved_searches ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            searches = []
            for row in rows:
                search = dict(row)
                # Parse filters JSON
                if search.get("filters"):
                    try:
                        search["filters"] = json.loads(search["filters"])
                    except json.JSONDecodeError:
                        search["filters"] = {}
                else:
                    search["filters"] = {}
                searches.append(search)
        
        return {"saved_searches": searches, "count": len(searches)}


@router.post("")
async def create_saved_search(search: SavedSearchCreate):
    """Save a new search query."""
    async for db in get_db():
        # Check if name already exists
        async with db.execute(
            "SELECT id FROM saved_searches WHERE name = ?", (search.name,)
        ) as cursor:
            if await cursor.fetchone():
                raise HTTPException(
                    status_code=400, 
                    detail=f"Saved search with name '{search.name}' already exists"
                )
        
        filters_json = json.dumps(search.filters) if search.filters else "{}"
        
        await db.execute(
            "INSERT INTO saved_searches (name, query, filters) VALUES (?, ?, ?)",
            (search.name, search.query, filters_json)
        )
        await db.commit()
        
        # Get the new search ID
        async with db.execute(
            "SELECT last_insert_rowid() as id"
        ) as cursor:
            row = await cursor.fetchone()
            search_id = row["id"]
        
        return {
            "id": search_id,
            "name": search.name,
            "query": search.query,
            "filters": search.filters or {},
            "created_at": datetime.now().isoformat()
        }


@router.get("/{search_id}")
async def get_saved_search(search_id: int):
    """Get a specific saved search."""
    async for db in get_db():
        async with db.execute(
            "SELECT * FROM saved_searches WHERE id = ?", (search_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Saved search not found")
            
            search = dict(row)
            # Parse filters JSON
            if search.get("filters"):
                try:
                    search["filters"] = json.loads(search["filters"])
                except json.JSONDecodeError:
                    search["filters"] = {}
            else:
                search["filters"] = {}
            
            return search


@router.put("/{search_id}")
async def update_saved_search(search_id: int, search_update: SavedSearchUpdate):
    """Update a saved search."""
    async for db in get_db():
        # Check if search exists
        async with db.execute(
            "SELECT id FROM saved_searches WHERE id = ?", (search_id,)
        ) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(status_code=404, detail="Saved search not found")
        
        # Build update query
        updates = []
        params = []
        
        if search_update.name is not None:
            updates.append("name = ?")
            params.append(search_update.name)
        
        if search_update.query is not None:
            updates.append("query = ?")
            params.append(search_update.query)
        
        if search_update.filters is not None:
            updates.append("filters = ?")
            params.append(json.dumps(search_update.filters))
        
        if updates:
            params.append(search_id)
            await db.execute(
                f"UPDATE saved_searches SET {', '.join(updates)} WHERE id = ?",
                params
            )
            await db.commit()
        
        # Return updated search
        async with db.execute(
            "SELECT * FROM saved_searches WHERE id = ?", (search_id,)
        ) as cursor:
            row = await cursor.fetchone()
            search = dict(row)
            if search.get("filters"):
                try:
                    search["filters"] = json.loads(search["filters"])
                except json.JSONDecodeError:
                    search["filters"] = {}
            
            return search


@router.delete("/{search_id}")
async def delete_saved_search(search_id: int):
    """Delete a saved search."""
    async for db in get_db():
        await db.execute(
            "DELETE FROM saved_searches WHERE id = ?", (search_id,)
        )
        await db.commit()
        
        return {"status": "success", "deleted_id": search_id}


@router.post("/{search_id}/execute")
async def execute_saved_search(search_id: int):
    """Execute a saved search and return results."""
    async for db in get_db():
        # Get saved search
        async with db.execute(
            "SELECT * FROM saved_searches WHERE id = ?", (search_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Saved search not found")
            
            saved_search = dict(row)
        
        # Parse filters
        filters = {}
        if saved_search.get("filters"):
            try:
                filters = json.loads(saved_search["filters"])
            except json.JSONDecodeError:
                filters = {}
        
        # Build and execute search query
        query = "SELECT * FROM repos WHERE 1=1"
        params = []
        
        search_query = saved_search.get("query", "")
        if search_query:
            query += " AND (name LIKE ? OR description LIKE ? OR full_name LIKE ? OR owner LIKE ?)"
            search_term = f"%{search_query}%"
            params.extend([search_term, search_term, search_term, search_term])
        
        if filters.get("language"):
            query += " AND language = ?"
            params.append(filters["language"])
        
        if filters.get("min_stars") is not None:
            query += " AND stars >= ?"
            params.append(filters["min_stars"])
        
        if filters.get("max_stars") is not None:
            query += " AND stars <= ?"
            params.append(filters["max_stars"])
        
        sort_by = filters.get("sort_by", "stars")
        order = filters.get("order", "desc").upper()
        query += f" ORDER BY {sort_by} {order}"
        
        limit = filters.get("limit", 20)
        query += " LIMIT ?"
        params.append(limit)
        
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            repos = [dict(row) for row in rows]
        
        return {
            "saved_search": {
                "id": search_id,
                "name": saved_search["name"],
                "query": search_query
            },
            "count": len(repos),
            "repos": repos
        }
