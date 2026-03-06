# Week 1 任务清单 - 项目初始化

**周期:** 2026-03-01 至 2026-03-07  
**目标:** 搭建可运行的基础框架  
**预计时间:** 17 小时  
**实际进度:** ✅ 已完成 (2026-03-05)

---

## 📋 任务总览

| 任务 | 描述 | 时间 | 状态 |
|------|------|------|------|
| 1.1 | 创建项目目录结构 | 2h | ✅ |
| 1.2 | 初始化 Python 项目 | 1h | ✅ |
| 1.3 | 搭建 FastAPI 框架 | 4h | ✅ |
| 1.4 | 配置 SQLite 数据库 | 3h | ✅ |
| 1.5 | 创建 Docker 配置 | 3h | ✅ |
| 1.6 | 迁移现有数据 | 4h | ✅ |

---

## 任务 1.1: 创建项目目录结构 (2h)

### 执行步骤

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

# 验证结构
tree -L 3 -d
```

### 验收标准

- [ ] 所有目录创建成功
- [ ] 目录结构符合设计
- [ ] 现有数据已备份

---

## 任务 1.2: 初始化 Python 项目 (1h)

### 执行步骤

创建 `pyproject.toml`:

```toml
[project]
name = "repodiscover"
version = "2.0.0"
description = "Discover awesome GitHub repositories"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "RepoDiscoverAI Team"}
]
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
cli = [
    "typer>=0.9.0",
    "rich>=13.7.0",
]

[project.scripts]
repodiscover = "cli.main:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

创建 `.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.env
.venv
venv/

# Data
data/*.db
data/*.json
logs/*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

### 验收标准

- [ ] pyproject.toml 创建成功
- [ ] .gitignore 创建成功
- [ ] `pip install -e .` 成功

---

## 任务 1.3: 搭建 FastAPI 框架 (4h)

### 执行步骤

创建 `app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path

from app.db.sqlite import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    print("✅ Database initialized")
    yield
    # Shutdown
    print("👋 Shutting down")

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

# Mount static files
frontend_dir = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_dir / "static"), name="static")

@app.get("/")
async def root():
    return FileResponse(frontend_dir / "index.html")

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.0.0"}

# Import and include routers
from app.api import search, trending, collections, learning_paths

app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(trending.router, prefix="/api/trending", tags=["Trending"])
app.include_router(collections.router, prefix="/api/collections", tags=["Collections"])
app.include_router(learning_paths.router, prefix="/api/paths", tags=["Learning Paths"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

### 验收标准

- [ ] FastAPI 应用可启动
- [ ] `/health` 端点返回正常
- [ ] 根路径返回 HTML 页面
- [ ] API 文档在 `/docs` 可用

---

## 任务 1.4: 配置 SQLite 数据库 (3h)

### 执行步骤

创建 `app/db/sqlite.py`:

```python
import aiosqlite
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "repos.db"

async def init_db():
    """Initialize SQLite database."""
    DB_PATH.parent.mkdir(exist_ok=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Enable foreign keys
        await db.execute("PRAGMA foreign_keys = ON")
        
        # Repos table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS repos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT UNIQUE NOT NULL,
                owner TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                language TEXT,
                stars INTEGER DEFAULT 0,
                forks INTEGER DEFAULT 0,
                url TEXT NOT NULL,
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
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Collection items
        await db.execute("""
            CREATE TABLE IF NOT EXISTS collection_items (
                collection_id INTEGER NOT NULL,
                repo_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (collection_id, repo_id),
                FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
                FOREIGN KEY (repo_id) REFERENCES repos(id) ON DELETE CASCADE
            )
        """)
        
        # Saved searches
        await db.execute("""
            CREATE TABLE IF NOT EXISTS saved_searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                query TEXT NOT NULL,
                filters TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        await db.execute("CREATE INDEX IF NOT EXISTS idx_stars ON repos(stars DESC)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_language ON repos(language)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_updated ON repos(updated_at DESC)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_full_name ON repos(full_name)")
        
        await db.commit()
    
    logger.info(f"Database initialized at {DB_PATH}")

async def get_db():
    """Get database connection."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
```

### 验收标准

- [ ] 数据库文件创建成功
- [ ] 所有表结构正确
- [ ] 索引创建成功
- [ ] 外键约束启用

---

## 任务 1.5: 创建 Docker 配置 (3h)

### 执行步骤

创建 `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application
COPY . .

# Create data directory
RUN mkdir -p data logs

# Expose port
EXPOSE 8080

# Run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

创建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///data/repos.db
      - LOG_LEVEL=INFO
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Optional: Meilisearch for advanced search (Phase 2)
  # meilisearch:
  #   image: getmeili/meilisearch:v1.6
  #   ports:
  #     - "7700:7700"
  #   volumes:
  #     - meili_data:/meili_data
  #   environment:
  #     - MEILI_NO_ANALYTICS=true
  #   profiles:
  #     - advanced

# volumes:
#   meili_data:
```

创建 `.env.example`:

```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///data/repos.db

# GitHub API (optional, for enhanced features)
GITHUB_TOKEN=

# App
APP_HOST=0.0.0.0
APP_PORT=8080
LOG_LEVEL=INFO
```

### 验收标准

- [ ] `docker-compose up -d` 成功
- [ ] 健康检查通过
- [ ] 数据持久化正常
- [ ] 日志输出正常

---

## 任务 1.6: 迁移现有数据 (4h)

### 执行步骤

创建 `scripts/migrate_data.py`:

```python
#!/usr/bin/env python3
"""Migrate existing scraper data to new database."""

import json
import asyncio
from pathlib import Path
import aiosqlite
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "legacy_backup" / "data"
DB_PATH = Path(__file__).parent.parent / "data" / "repos.db"

async def migrate():
    """Migrate data from JSON files to SQLite."""
    if not DB_PATH.exists():
        print("❌ Database not found. Please run app first to initialize.")
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Find all JSON files
        json_files = list(DATA_DIR.glob("*.json"))
        
        if not json_files:
            print("⚠️ No JSON files found in legacy_backup/data/")
            return
        
        migrated = 0
        errors = 0
        
        for json_file in json_files:
            print(f"Processing {json_file.name}...")
            
            try:
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
                        errors += 1
                        print(f"  Error migrating {repo.get('full_name')}: {e}")
                
                await db.commit()
                
            except Exception as e:
                print(f"Error processing {json_file.name}: {e}")
                errors += 1
        
        print(f"\n✅ Migration complete!")
        print(f"   Migrated: {migrated} repositories")
        print(f"   Errors: {errors}")

if __name__ == "__main__":
    asyncio.run(migrate())
```

运行迁移:

```bash
cd /home/wei/.openclaw/workspace/RepoDiscoverAI
python scripts/migrate_data.py

# 验证数据
sqlite3 data/repos.db "SELECT COUNT(*) FROM repos;"
sqlite3 data/repos.db "SELECT full_name, stars FROM repos ORDER BY stars DESC LIMIT 5;"
```

### 验收标准

- [ ] 历史数据成功迁移
- [ ] 数据完整性验证通过
- [ ] 无严重错误

---

## ✅ Week 1 完成检查清单

### 功能验证

```bash
# 1. 启动服务
docker-compose up -d

# 2. 检查健康状态
curl http://localhost:8080/health
# 期望: {"status": "healthy", "version": "2.0.0"}

# 3. 访问 Web UI
open http://localhost:8080

# 4. 查看 API 文档
open http://localhost:8080/docs

# 5. 测试搜索 API (如果有数据)
curl "http://localhost:8080/api/search?q=test&limit=5"

# 6. 检查数据库
sqlite3 data/repos.db "SELECT COUNT(*) FROM repos;"
```

### 文件清单

- [ ] `app/main.py` - FastAPI 入口
- [ ] `app/db/sqlite.py` - 数据库配置
- [ ] `app/api/search.py` - 搜索 API (骨架)
- [ ] `app/api/trending.py` - Trending API (骨架)
- [ ] `frontend/index.html` - Web UI (骨架)
- [ ] `Dockerfile` - Docker 配置
- [ ] `docker-compose.yml` - Docker Compose
- [ ] `pyproject.toml` - Python 项目配置
- [ ] `scripts/migrate_data.py` - 数据迁移脚本

---

## 🐛 常见问题

### Q: Docker 启动失败
```bash
# 查看日志
docker-compose logs app

# 重新构建
docker-compose up -d --build

# 检查端口占用
lsof -i :8080
```

### Q: 数据库为空
```bash
# 运行迁移
python scripts/migrate_data.py

# 验证
sqlite3 data/repos.db "SELECT COUNT(*) FROM repos;"
```

### Q: 导入错误
```bash
# 安装依赖
pip install -e .

# 检查 Python 版本
python --version  # 需要 >= 3.10
```

---

## 📝 每日进度模板

```markdown
### Day X (YYYY-MM-DD)

**完成:**
- [ ] 任务描述

**遇到问题:**
- 问题 + 解决方案

**明日计划:**
- [ ] 任务描述
```

---

**预计完成时间:** 17 小时 (2-3 天)  
**难度:** ⭐⭐☆☆☆  
**下一步:** Week 2 - 基础功能开发
