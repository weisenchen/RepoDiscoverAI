"""
Collections API - User Collections Endpoints

Allows users to create, manage, and share collections of repositories.
"""

from fastapi import APIRouter, Query, HTTPException, Body
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from app.db.sqlite import get_db

router = APIRouter()


class CollectionCreate(BaseModel):
    name: str
    description: Optional[str] = None


class CollectionItem(BaseModel):
    collection_id: int
    repo_id: int


@router.get("")
async def list_collections():
    """List all collections."""
    async for db in get_db():
        async with db.execute(
            "SELECT * FROM collections ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            collections = [dict(row) for row in rows]
        
        # Add repo count to each collection
        for collection in collections:
            async with db.execute(
                "SELECT COUNT(*) as count FROM collection_items WHERE collection_id = ?",
                (collection["id"],)
            ) as cursor:
                row = await cursor.fetchone()
                collection["repo_count"] = row["count"] if row else 0
        
        return {"collections": collections}


@router.post("")
async def create_collection(collection: CollectionCreate):
    """Create a new collection."""
    async for db in get_db():
        await db.execute(
            "INSERT INTO collections (name, description) VALUES (?, ?)",
            (collection.name, collection.description)
        )
        await db.commit()
        
        # Get the new collection ID
        async with db.execute(
            "SELECT last_insert_rowid() as id"
        ) as cursor:
            row = await cursor.fetchone()
            collection_id = row["id"]
        
        return {
            "id": collection_id,
            "name": collection.name,
            "description": collection.description,
            "created_at": datetime.now().isoformat()
        }


@router.get("/{collection_id}")
async def get_collection(collection_id: int):
    """Get a specific collection with its repositories."""
    async for db in get_db():
        # Get collection info
        async with db.execute(
            "SELECT * FROM collections WHERE id = ?", (collection_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Collection not found")
            
            collection = dict(row)
        
        # Get repos in collection
        async with db.execute("""
            SELECT r.* FROM repos r
            JOIN collection_items ci ON r.id = ci.repo_id
            WHERE ci.collection_id = ?
            ORDER BY ci.added_at DESC
        """, (collection_id,)) as cursor:
            rows = await cursor.fetchall()
            repos = [dict(row) for row in rows]
        
        collection["repos"] = repos
        collection["repo_count"] = len(repos)
        
        return collection


@router.post("/{collection_id}/repos")
async def add_repo_to_collection(collection_id: int, repo_id: int = Body(..., embed=True)):
    """Add a repository to a collection."""
    async for db in get_db():
        # Verify collection exists
        async with db.execute(
            "SELECT id FROM collections WHERE id = ?", (collection_id,)
        ) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(status_code=404, detail="Collection not found")
        
        # Verify repo exists
        async with db.execute(
            "SELECT id FROM repos WHERE id = ?", (repo_id,)
        ) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(status_code=404, detail="Repository not found")
        
        # Add to collection
        await db.execute(
            "INSERT OR IGNORE INTO collection_items (collection_id, repo_id) VALUES (?, ?)",
            (collection_id, repo_id)
        )
        await db.commit()
        
        return {"status": "success", "collection_id": collection_id, "repo_id": repo_id}


@router.delete("/{collection_id}/repos/{repo_id}")
async def remove_repo_from_collection(collection_id: int, repo_id: int):
    """Remove a repository from a collection."""
    async for db in get_db():
        await db.execute(
            "DELETE FROM collection_items WHERE collection_id = ? AND repo_id = ?",
            (collection_id, repo_id)
        )
        await db.commit()
        
        return {"status": "success"}


@router.delete("/{collection_id}")
async def delete_collection(collection_id: int):
    """Delete a collection."""
    async for db in get_db():
        await db.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
        await db.commit()
        
        return {"status": "success"}
