"""
Search Engine Module

Provides Meilisearch integration as an alternative to SQLite search
for better full-text search capabilities.
"""

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class SearchConfig:
    """Meilisearch configuration."""
    host: str = "http://localhost:7700"
    api_key: Optional[str] = None
    index_name: str = "repositories"


class MeilisearchEngine:
    """
    Meilisearch integration for full-text search.
    
    This is an optional enhancement over SQLite search.
    Use when you need:
    - Better full-text search relevance
    - Typo tolerance
    - Faceted search
    - Faster search on large datasets
    """
    
    def __init__(self, config: Optional[SearchConfig] = None):
        self.config = config or SearchConfig(
            host=os.getenv("MEILI_HOST", "http://localhost:7700"),
            api_key=os.getenv("MEILI_MASTER_KEY"),
            index_name=os.getenv("MEILI_INDEX", "repositories")
        )
        self._client = None
        self._index = None
    
    @property
    def client(self):
        """Lazy-load Meilisearch client."""
        if self._client is None:
            try:
                import meilisearch
                self._client = meilisearch.Client(
                    self.config.host,
                    self.config.api_key
                )
                self._index = self._client.index(self.config.index_name)
            except ImportError:
                raise ImportError(
                    "meilisearch package not installed. "
                    "Run: pip install meilisearch"
                )
            except Exception as e:
                # Meilisearch not available, fall back to SQLite
                return None
        return self._client
    
    @property
    def index(self):
        """Get Meilisearch index."""
        if self.client is None:
            return None
        return self._index
    
    def is_available(self) -> bool:
        """Check if Meilisearch is available."""
        try:
            if self.client is None:
                return False
            # Try to get stats
            self.index.get_stats()
            return True
        except Exception:
            return False
    
    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        offset: int = 0,
        sort: Optional[List[str]] = None
    ) -> Dict:
        """
        Search repositories using Meilisearch.
        
        Args:
            query: Search query string
            filters: Filter conditions (e.g., {"language": "Python"})
            limit: Max results
            offset: Result offset
            sort: Sort order (e.g., ["stars:desc"])
            
        Returns:
            Search results with hits and metadata
        """
        if not self.is_available():
            return {"error": "Meilisearch not available", "hits": []}
        
        search_params = {
            "limit": limit,
            "offset": offset,
            "attributesToHighlight": ["name", "description"],
            "highlightPreTag": "<mark>",
            "highlightPostTag": "</mark>",
        }
        
        if filters:
            filter_parts = []
            for key, value in filters.items():
                if isinstance(value, str):
                    filter_parts.append(f'{key} = "{value}"')
                elif isinstance(value, (int, float)):
                    filter_parts.append(f"{key} = {value}")
                elif isinstance(value, (list, tuple)):
                    # Range or list
                    if len(value) == 2:
                        filter_parts.append(f"{key} >= {value[0]} AND {key} <= {value[1]}")
                    else:
                        filter_parts.append(f"{key} IN [{', '.join(map(str, value))}]")
            
            if filter_parts:
                search_params["filter"] = " AND ".join(filter_parts)
        
        if sort:
            search_params["sort"] = sort
        
        results = self.index.search(query, search_params)
        
        return {
            "hits": results.get("hits", []),
            "total": results.get("estimatedTotalHits", 0),
            "query": results.get("query", query),
            "processing_time_ms": results.get("processingTimeMs", 0)
        }
    
    def add_document(self, repo: Dict) -> Dict:
        """Add or update a repository document."""
        if not self.is_available():
            return {"error": "Meilisearch not available"}
        
        # Prepare document
        doc = {
            "id": repo.get("id") or repo.get("full_name"),
            "full_name": repo.get("full_name", ""),
            "name": repo.get("name", ""),
            "description": repo.get("description", ""),
            "owner": repo.get("owner", ""),
            "language": repo.get("language", ""),
            "stars": repo.get("stars", 0),
            "forks": repo.get("forks", 0),
            "watchers": repo.get("watchers", 0),
            "topics": repo.get("topics", []),
            "url": repo.get("html_url", ""),
            "updated_at": repo.get("updated_at", ""),
            "created_at": repo.get("created_at", ""),
        }
        
        task = self.index.add_documents([doc])
        return {"task_id": task.get("taskUid"), "status": "queued"}
    
    def add_documents(self, repos: List[Dict]) -> Dict:
        """Add or update multiple repository documents."""
        if not self.is_available():
            return {"error": "Meilisearch not available"}
        
        docs = []
        for repo in repos:
            docs.append({
                "id": repo.get("id") or repo.get("full_name"),
                "full_name": repo.get("full_name", ""),
                "name": repo.get("name", ""),
                "description": repo.get("description", ""),
                "owner": repo.get("owner", ""),
                "language": repo.get("language", ""),
                "stars": repo.get("stars", 0),
                "forks": repo.get("forks", 0),
                "watchers": repo.get("watchers", 0),
                "topics": repo.get("topics", []),
                "url": repo.get("html_url", ""),
                "updated_at": repo.get("updated_at", ""),
                "created_at": repo.get("created_at", ""),
            })
        
        task = self.index.add_documents(docs)
        return {"task_id": task.get("taskUid"), "status": "queued"}
    
    def delete_document(self, doc_id: str) -> Dict:
        """Delete a repository document."""
        if not self.is_available():
            return {"error": "Meilisearch not available"}
        
        task = self.index.delete_document(doc_id)
        return {"task_id": task.get("taskUid"), "status": "queued"}
    
    def configure_index(self):
        """Configure index settings for optimal search."""
        if not self.is_available():
            return {"error": "Meilisearch not available"}
        
        # Set searchable attributes
        self.index.update_searchable_attributes([
            "name",
            "description",
            "full_name",
            "owner",
            "topics"
        ])
        
        # Set filterable attributes
        self.index.update_filterable_attributes([
            "language",
            "stars",
            "forks",
            "watchers",
            "created_at",
            "updated_at"
        ])
        
        # Set sortable attributes
        self.index.update_sortable_attributes([
            "stars",
            "forks",
            "watchers",
            "created_at",
            "updated_at",
            "name"
        ])
        
        # Set ranking rules
        self.index.update_ranking_rules([
            "words",
            "typo",
            "proximity",
            "attribute",
            "sort",
            "exactness",
            "stars:desc"
        ])
        
        # Enable typo tolerance
        self.index.update_typo_tolerance({
            "enabled": True,
            "minWordSizeForTypos": {
                "oneTypo": 4,
                "twoTypos": 8
            }
        })
        
        return {"status": "configured"}
    
    def sync_from_sqlite(self, sqlite_repos: List[Dict]) -> Dict:
        """
        Sync all repositories from SQLite to Meilisearch.
        
        Args:
            sqlite_repos: List of repository dicts from SQLite
            
        Returns:
            Sync status
        """
        if not self.is_available():
            return {"error": "Meilisearch not available"}
        
        # Add all documents
        result = self.add_documents(sqlite_repos)
        
        return {
            **result,
            "synced_count": len(sqlite_repos),
            "status": "synced"
        }


# Singleton instance
_search_engine: Optional[MeilisearchEngine] = None


def get_search_engine() -> Optional[MeilisearchEngine]:
    """Get the Meilisearch engine instance."""
    global _search_engine
    if _search_engine is None:
        _search_engine = MeilisearchEngine()
    return _search_engine


def is_meilisearch_available() -> bool:
    """Check if Meilisearch is available and configured."""
    engine = get_search_engine()
    return engine.is_available() if engine else False
