#!/bin/bash
# RepoDiscoverAI - Local Deployment Script
# 
# This script sets up the local environment and runs the application.
# Run with: bash local-deploy.sh

set -e

# Configuration
PORT=8080
BACKEND_PORT=8000
VENV_DIR=".venv"

echo "============================================"
echo "  🚀 RepoDiscoverAI Local Deployment"
echo "============================================"
echo ""

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Step 1: Cleanup existing processes on relevant ports
echo "Step 1: Checking for existing processes on ports $PORT and $BACKEND_PORT..."

# Function to kill process on port
kill_on_port() {
    local port=$1
    local pid=$(lsof -t -i:$port 2>/dev/null || true)
    if [ ! -z "$pid" ]; then
        echo "  - Stopping process on port $port (PID: $pid)..."
        kill -9 $pid || true
    fi
}

kill_on_port $PORT
kill_on_port $BACKEND_PORT

# Step 2: Create directories
echo "Step 2: Creating necessary directories..."
mkdir -p logs data github_trending_tech/archive
echo "✓ Directories ready"
echo ""

# Step 3: Setup Virtual Environment
echo "Step 3: Setting up Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "✓ Virtual environment created"
else
    echo "  - Using existing virtual environment"
fi
source "$VENV_DIR/bin/activate"
echo "✓ Virtual environment activated"
echo ""

# Step 4: Install dependencies
echo "Step 4: Installing dependencies..."
pip install --upgrade pip
pip install -e "."
# Install scraper dependencies specifically
pip install -r scripts/requirements.txt
echo "✓ Dependencies installed"
echo ""

# Step 5: Initial Data Population (Optional but recommended)
echo "Step 5: Populating initial data..."
# Run one quick scrape to make sure something is in the DB
echo "  - Scraping Python trending repos..."
python3 scripts/github_trending_scraper.py --language python --no-update
echo "  - Migrating data to SQLite..."
python3 scripts/migrate_data.py
echo "✓ Initial data populated"
echo ""

# Step 6: Start the Application
echo "Step 6: Starting RepoDiscoverAI..."
echo "  - Backend will run on http://0.0.0.0:$PORT"
echo "  - Documentation: http://0.0.0.0:$PORT/docs"
echo ""
echo "Press Ctrl+C to stop the server."
echo ""

# Export environment variables if needed
export DATABASE_URL="sqlite+aiosqlite:///data/repos.db"
export LOG_LEVEL="INFO"

# Run the app
# We use uvicorn directly to ensure it runs as expected
python3 -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload
