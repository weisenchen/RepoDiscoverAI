#!/bin/bash
# RepoDiscoverAI - Setup Script
# 
# This script sets up the GitHub Trending scraper and automation.
# Run with: bash scripts/setup.sh

set -e

echo "============================================"
echo "  RepoDiscoverAI - Setup Script"
echo "============================================"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "📁 Project root: $PROJECT_ROOT"
echo ""

# Step 1: Create directories
echo "Step 1: Creating directories..."
mkdir -p logs
mkdir -p data
mkdir -p github_trending_tech/archive
echo "✓ Directories created"
echo ""

# Step 2: Install Python dependencies
echo "Step 2: Installing Python dependencies..."
if command -v pip3 &> /dev/null; then
    pip3 install -r scripts/requirements.txt
elif command -v pip &> /dev/null; then
    pip install -r scripts/requirements.txt
else
    echo "⚠️  pip not found. Please install requirements manually:"
    echo "   pip install -r scripts/requirements.txt"
fi
echo "✓ Dependencies installed"
echo ""

# Step 3: Test the scraper
echo "Step 3: Testing the scraper..."
python3 scripts/github_trending_scraper.py --no-update
echo "✓ Scraper test completed"
echo ""

# Step 4: Setup cron jobs (optional)
echo "Step 4: Cron job setup"
echo ""
echo "Do you want to set up automated scraping? (y/n)"
read -r setup_cron

if [[ "$setup_cron" =~ ^[Yy]$ ]]; then
    # Check if crontab is available
    if command -v crontab &> /dev/null; then
        # Create a personalized cron file
        CRON_FILE="$SCRIPT_DIR/cron_jobs"
        sed "s|/home/wei/.openclaw/workspace/RepoDiscoverAI|$PROJECT_ROOT|g" \
            "$SCRIPT_DIR/cron_jobs.example" > "$CRON_FILE"
        
        # Install cron jobs
        crontab "$CRON_FILE"
        echo "✓ Cron jobs installed"
        echo ""
        echo "Current cron jobs:"
        crontab -l
    else
        echo "⚠️  crontab not available. Manual setup required."
        echo ""
        echo "To set up cron jobs manually:"
        echo "  1. Run: crontab -e"
        echo "  2. Add the lines from: $SCRIPT_DIR/cron_jobs.example"
        echo "  3. Update the paths to match: $PROJECT_ROOT"
    fi
else
    echo "⊘ Cron setup skipped"
    echo ""
    echo "To set up cron jobs later:"
    echo "  crontab $SCRIPT_DIR/cron_jobs.example"
fi
echo ""

# Step 5: Summary
echo "============================================"
echo "  Setup Complete! 🎉"
echo "============================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Manual scrape:"
echo "   python3 scripts/github_trending_scraper.py"
echo ""
echo "2. View trending repos:"
echo "   cat github_trending_tech/README.md"
echo ""
echo "3. Check scraped data:"
echo "   ls -la data/"
echo ""
echo "4. View logs:"
echo "   tail -f logs/trending_daily.log"
echo ""
echo "5. Customize cron jobs:"
echo "   crontab -e"
echo ""
echo "Documentation: scripts/trending_scraper.md"
echo ""
