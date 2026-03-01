# Phase 1 快速启动指南

**目标:** 2 小时内搭建可运行的 RepoDiscoverAI 2.0 基础框架

---

## 📋 Phase 1 任务清单

- [ ] 1. 创建项目结构
- [ ] 2. 搭建 FastAPI 后端
- [ ] 3. 实现基础搜索 API
- [ ] 4. 创建 HTMX 前端
- [ ] 5. Docker Compose 部署
- [ ] 6. 迁移现有数据

---

## 步骤 1: 创建项目结构 (15 分钟)

```bash
cd /home/wei/.openclaw/workspace/RepoDiscoverAI

# 备份现有内容
mkdir -p legacy_backup
cp -r github_trending_tech scripts data legacy_backup/

# 创建新目录结构
mkdir -p app/{api,core,models,db/migrations}
mkdir -p frontend/{components,static,templates}
mkdir -p cli/{commands,utils}
mkdir -p collections/learning-paths
mkdir -p tests
mkdir -p docs

# 创建空文件
touch app/__init__.py
touch app/main.py
touch app/api/{search,trending,collections,learning_paths}.py
touch app/core/{search_engine,recommendation,trend_analysis,github_client}.py
touch app/models/{repo,user,collection}.py
touch app/db/{sqlite.py}
touch cli/__init__.py
touch cli/main.py
```

---

## 步骤 2: 搭建 FastAPI 后端 (30 分钟)

### 2.1 创建 pyproject.toml

```toml
[project]
name = "repodiscover"
version = "2.0.0"
description = "Discover awesome GitHub repositories"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "httpx>=0.26.0",
    "aiosqlite>=0.19.0",
    "pydantic>=2.5.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "black>=24.1.0",
    "ruff>=0.1.0",
]
search = [
    "meilisearch>=0.31.0",
]
cli = [
    "typer>=0.9.0",
    "rich>=13.7.0",
]

[project.scripts]
repodiscover = "cli.main:app"
```

### 2.2 创建 app/main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api import search, trending, collections, learning_paths
from app.db.sqlite import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="RepoDiscoverAI",
    description="Discover awesome GitHub repositories",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(trending.router, prefix="/api/trending", tags=["Trending"])
app.include_router(collections.router, prefix="/api/collections", tags=["Collections"])
app.include_router(learning_paths.router, prefix="/api/paths", tags=["Learning Paths"])

@app.get("/")
async def root():
    return {
        "name": "RepoDiscoverAI",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

### 2.3 创建 app/db/sqlite.py

```python
import aiosqlite
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent.parent / "data" / "repos.db"

async def init_db():
    """Initialize SQLite database."""
    DB_PATH.parent.mkdir(exist_ok=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Repos table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS repos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT UNIQUE,
                owner TEXT,
                name TEXT,
                description TEXT,
                language TEXT,
                stars INTEGER,
                forks INTEGER,
                url TEXT,
                topics TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Collections table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Collection items
        await db.execute("""
            CREATE TABLE IF NOT EXISTS collection_items (
                collection_id INTEGER,
                repo_id INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (collection_id, repo_id),
                FOREIGN KEY (collection_id) REFERENCES collections(id),
                FOREIGN KEY (repo_id) REFERENCES repos(id)
            )
        """)
        
        # Create indexes
        await db.execute("CREATE INDEX IF NOT EXISTS idx_stars ON repos(stars DESC)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_language ON repos(language)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_updated ON repos(updated_at DESC)")
        
        await db.commit()
    
    print(f"✅ Database initialized at {DB_PATH}")

async def get_db():
    """Get database connection."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
```

---

## 步骤 3: 实现基础搜索 API (30 分钟)

### 3.1 创建 app/api/search.py

```python
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from app.db.sqlite import get_db

router = APIRouter()

@router.get("")
async def search_repos(
    q: str = Query(..., description="Search query"),
    language: Optional[str] = Query(None, description="Filter by language"),
    min_stars: Optional[int] = Query(None, description="Minimum stars"),
    max_stars: Optional[int] = Query(None, description="Maximum stars"),
    limit: int = Query(20, ge=1, le=100, description="Results limit")
):
    """Search repositories."""
    async for db in get_db():
        # Build query
        query = "SELECT * FROM repos WHERE 1=1"
        params = []
        
        if q:
            query += " AND (name LIKE ? OR description LIKE ? OR full_name LIKE ?)"
            search_term = f"%{q}%"
            params.extend([search_term, search_term, search_term])
        
        if language:
            query += " AND language = ?"
            params.append(language)
        
        if min_stars is not None:
            query += " AND stars >= ?"
            params.append(min_stars)
        
        if max_stars is not None:
            query += " AND stars <= ?"
            params.append(max_stars)
        
        query += " ORDER BY stars DESC LIMIT ?"
        params.append(limit)
        
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            
            return {
                "query": q,
                "count": len(rows),
                "repos": [dict(row) for row in rows]
            }

@router.get("/suggestions")
async def search_suggestions(
    q: str = Query(..., min_length=2, description="Partial query")
):
    """Get search suggestions."""
    async for db in get_db():
        async with db.execute(
            "SELECT DISTINCT language FROM repos WHERE language LIKE ? LIMIT 10",
            (f"{q}%",)
        ) as cursor:
            rows = await cursor.fetchall()
            return {"suggestions": [row["language"] for row in rows]}
```

### 3.2 创建 app/api/trending.py

```python
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime

router = APIRouter()

@router.get("")
async def get_trending(
    period: str = Query("today", enum=["today", "week", "month"]),
    language: Optional[str] = Query(None)
):
    """Get trending repositories."""
    # TODO: Integrate with existing scraper data
    return {
        "period": period,
        "language": language or "all",
        "updated_at": datetime.now().isoformat(),
        "repos": []  # Will be populated from scraper data
    }

@router.get("/history")
async def get_trending_history(
    days: int = Query(7, ge=1, le=90)
):
    """Get historical trending data."""
    # TODO: Load from archive
    return {
        "days": days,
        "data": []
    }
```

---

## 步骤 4: 创建 HTMX 前端 (30 分钟)

### 4.1 创建 frontend/index.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RepoDiscoverAI - Discover Awesome GitHub Repos</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .htmx-request { opacity: 0.5; }
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <!-- Header -->
    <header class="bg-white shadow">
        <div class="max-w-7xl mx-auto px-4 py-6">
            <h1 class="text-3xl font-bold text-gray-900">
                🚀 RepoDiscoverAI
            </h1>
            <p class="text-gray-600 mt-2">
                Discover awesome GitHub repositories
            </p>
        </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 py-8">
        <!-- Search Box -->
        <div class="mb-8">
            <form class="flex gap-4" 
                  hx-get="/api/search" 
                  hx-target="#results"
                  hx-trigger="submit">
                <input type="text" 
                       name="q" 
                       placeholder="Search repositories..." 
                       class="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                       required>
                <select name="language" 
                        class="px-4 py-3 border border-gray-300 rounded-lg">
                    <option value="">All Languages</option>
                    <option value="Python">Python</option>
                    <option value="JavaScript">JavaScript</option>
                    <option value="TypeScript">TypeScript</option>
                    <option value="Rust">Rust</option>
                    <option value="Go">Go</option>
                </select>
                <button type="submit" 
                        class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
                    Search
                </button>
            </form>
        </div>

        <!-- Results -->
        <div id="results" class="grid gap-4">
            <!-- Results will be loaded here -->
            <div class="text-center text-gray-500 py-12">
                Start searching to discover repositories
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="bg-white border-t mt-12">
        <div class="max-w-7xl mx-auto px-4 py-6 text-center text-gray-600">
            <a href="https://github.com/weisenchen/RepoDiscoverAI" 
               class="text-blue-600 hover:underline">
                GitHub
            </a>
            ·
            <a href="/docs" class="text-blue-600 hover:underline">
                Docs
            </a>
        </div>
    </footer>
</body>
</html>
```

---

## 步骤 5: Docker Compose 部署 (15 分钟)

### 5.1 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///data/repos.db
    restart: unless-stopped

  # Optional: Meilisearch for advanced search
  meilisearch:
    image: getmeili/meilisearch:v1.6
    ports:
      - "7700:7700"
    volumes:
      - meili_data:/meili_data
    environment:
      - MEILI_NO_ANALYTICS=true
    profiles:
      - advanced

volumes:
  meili_data:
```

### 5.2 创建 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application
COPY . .

# Expose port
EXPOSE 8080

# Run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 5.3 创建 .env.example

```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///data/repos.db

# GitHub API (optional, for enhanced features)
GITHUB_TOKEN=

# Meilisearch (optional)
MEILI_HOST=http://meilisearch:7700
MEILI_MASTER_KEY=changeme

# App
APP_HOST=0.0.0.0
APP_PORT=8080
```

---

## 步骤 6: 迁移现有数据 (30 分钟)

### 6.1 创建 scripts/migrate_data.py

```python
#!/usr/bin/env python3
"""Migrate existing scraper data to new database."""

import json
from pathlib import Path
import aiosqlite
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "legacy_backup" / "data"
DB_PATH = Path(__file__).parent.parent / "data" / "repos.db"

async def migrate():
    """Migrate data from JSON files to SQLite."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Find all JSON files
        json_files = list(DATA_DIR.glob("*.json"))
        
        migrated = 0
        for json_file in json_files:
            print(f"Processing {json_file.name}...")
            
            with open(json_file) as f:
                data = json.load(f)
            
            repos = data.get("repos", [])
            
            for repo in repos:
                try:
                    await db.execute("""
                        INSERT OR REPLACE INTO repos 
                        (full_name, owner, name, description, language, 
                         stars, forks, url, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        repo.get("full_name"),
                        repo.get("owner"),
                        repo.get("name"),
                        repo.get("description"),
                        repo.get("language"),
                        repo.get("stars"),
                        repo.get("forks"),
                        repo.get("url"),
                        repo.get("scraped_at", datetime.now().isoformat())
                    ))
                    migrated += 1
                except Exception as e:
                    print(f"  Error migrating {repo.get('full_name')}: {e}")
            
            await db.commit()
        
        print(f"✅ Migrated {migrated} repositories")

if __name__ == "__main__":
    import asyncio
    asyncio.run(migrate())
```

### 6.2 运行迁移

```bash
cd /home/wei/.openclaw/workspace/RepoDiscoverAI
python scripts/migrate_data.py
```

---

## ✅ 验收标准

完成 Phase 1 后，应该能够：

```bash
# 1. 启动服务
docker-compose up -d

# 2. 访问 Web UI
open http://localhost:8080

# 3. 测试搜索 API
curl "http://localhost:8080/api/search?q=llm&language=Python&limit=5"

# 4. 查看 API 文档
open http://localhost:8080/docs

# 5. 检查健康状态
curl http://localhost:8080/health
```

---

## 🐛 常见问题

### Q: Docker 启动失败
```bash
# 检查日志
docker-compose logs app

# 重新构建
docker-compose up -d --build
```

### Q: 数据库为空
```bash
# 运行数据迁移
python scripts/migrate_data.py

# 验证数据
sqlite3 data/repos.db "SELECT COUNT(*) FROM repos;"
```

### Q: 搜索不工作
```bash
# 检查 API 日志
docker-compose logs -f app

# 测试 API 直接
curl "http://localhost:8080/api/search?q=test"
```

---

## 📞 需要帮助？

- 📖 查看 [REDESIGN_PLAN.md](./REDESIGN_PLAN.md) 了解完整计划
- 💬 在 GitHub 提 Issue
- 📧 邮件联系 (待添加)

---

**预计完成时间:** 2-3 小时  
**难度:** ⭐⭐☆☆☆ (入门级)  
**下一步:** Phase 2 - 核心功能开发
