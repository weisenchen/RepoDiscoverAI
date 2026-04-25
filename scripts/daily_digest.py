#!/usr/bin/env python3
"""
RepoDiscoverAI v3.0 - Daily Digest Generator

Automated daily digest generation and distribution.
Run via cron or GitHub Actions.

Usage:
    python scripts/daily_digest.py [--top-n 5] [--output-dir ./output]
"""

import asyncio
import argparse
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.content_generator import ContentGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Run daily digest generation."""
    parser = argparse.ArgumentParser(description="RepoDiscoverAI Daily Digest Generator")
    parser.add_argument("--top-n", type=int, default=5, help="Number of top repos to include")
    parser.add_argument("--output-dir", type=str, default="./output", help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Generate without posting")
    
    args = parser.parse_args()
    
    # Load configuration from environment
    config = {
        "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN"),
        "ELEVENLABS_API_KEY": os.getenv("ELEVENLABS_API_KEY"),
        "ELEVENLABS_VOICE_ID": os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
        "ELEVENLABS_MODEL": os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
        "SHOTSTACK_API_KEY": os.getenv("SHOTSTACK_API_KEY"),
        "SHOTSTACK_BASE_URL": os.getenv("SHOTSTACK_BASE_URL", "https://api.shotstack.io/v1"),
        "TWITTER_BEARER_TOKEN": os.getenv("TWITTER_BEARER_TOKEN"),
        "TWITTER_API_KEY": os.getenv("TWITTER_API_KEY"),
        "TWITTER_API_SECRET": os.getenv("TWITTER_API_SECRET"),
        "TWITTER_ACCESS_TOKEN": os.getenv("TWITTER_ACCESS_TOKEN"),
        "TWITTER_ACCESS_TOKEN_SECRET": os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
        "SITE_URL": os.getenv("SITE_URL", "https://repodiscoverai.com"),
        "OUTPUT_DIR": args.output_dir
    }
    
    logger.info(f"🚀 Starting RepoDiscoverAI Daily Digest Generator")
    logger.info(f"📅 Date: {datetime.now().strftime('%Y-%m-%d')}")
    logger.info(f"📊 Top N: {args.top_n}")
    logger.info(f"📁 Output: {args.output_dir}")
    
    try:
        # Initialize content generator
        generator = ContentGenerator(config)
        
        # Generate daily digest
        result = await generator.generate_daily_digest(top_n=args.top_n)
        
        if "error" in result:
            logger.error(f"❌ Generation failed: {result['error']}")
            sys.exit(1)
        
        # Log results
        logger.info("✅ Daily digest generation complete!")
        logger.info(f"📁 Files generated:")
        for fmt, path in result.get("files", {}).items():
            if path:
                logger.info(f"   - {fmt}: {path}")
        
        if result.get("social_media"):
            logger.info(f"🐦 Social media posts: {len(result['social_media'])} tweets")
        
        # In dry-run mode, save results to JSON
        if args.dry_run:
            import json
            output_path = Path(args.output_dir) / f"digest-{datetime.now().strftime('%Y-%m-%d')}.json"
            output_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
            logger.info(f"📝 Dry run complete. Results saved to {output_path}")
        
        logger.info("🎉 Done!")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await generator.close()


if __name__ == "__main__":
    asyncio.run(main())
