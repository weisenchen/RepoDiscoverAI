"""
RepoDiscoverAI - Main FastAPI Application

Discover awesome GitHub repositories with intelligent search,
trend analysis, and curated learning paths.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from contextlib import asynccontextmanager
from pathlib import Path
import logging

from app.db.sqlite import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("🚀 Starting RepoDiscoverAI...")
    await init_db()
    logger.info("✅ Database initialized")
    yield
    # Shutdown
    logger.info("👋 Shutting down RepoDiscoverAI")


# Create FastAPI application
app = FastAPI(
    title="RepoDiscoverAI",
    description="Discover awesome GitHub repositories with intelligent search, trend analysis, and curated learning paths.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Mount static files
frontend_dir = Path(__file__).parent.parent / "frontend"
static_dir = frontend_dir / "static"

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page."""
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse(content="<h1>RepoDiscoverAI API</h1><p>Visit /docs for API documentation</p>")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "service": "RepoDiscoverAI"
    }


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "name": "RepoDiscoverAI API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "search": "/api/search",
            "trending": "/api/trending",
            "collections": "/api/collections",
            "paths": "/api/paths"
        }
    }


# Import and include API routers
from app.api import search, trending, collections, learning_paths

app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(trending.router, prefix="/api/trending", tags=["Trending"])
app.include_router(collections.router, prefix="/api/collections", tags=["Collections"])
app.include_router(learning_paths.router, prefix="/api/paths", tags=["Learning Paths"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
