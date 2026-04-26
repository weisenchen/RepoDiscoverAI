#!/usr/bin/env python3
"""
RepoDiscoverAI v3.0 - Daily Digest Generator (Enhanced)

Automated daily digest generation with performance monitoring,
cost optimization, and quality evaluation.

Usage:
    python scripts/daily_digest.py [--top-n 5] [--output-dir ./output] [--dry-run]
"""

import asyncio
import argparse
import logging
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.content_generator import ContentGenerator
from app.core.performance import perf_monitor
from app.core.cost_optimizer import cost_optimizer
from app.core.quality import QualityEvaluator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Run daily digest generation with monitoring."""
    parser = argparse.ArgumentParser(description="RepoDiscoverAI Daily Digest Generator")
    parser.add_argument("--top-n", type=int, default=5, help="Number of top repos to include")
    parser.add_argument("--output-dir", type=str, default="./output", help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Generate without posting")
    parser.add_argument("--skip-podcast", action="store_true", help="Skip podcast generation")
    parser.add_argument("--skip-video", action="store_true", help="Skip video generation")
    parser.add_argument("--skip-social", action="store_true", help="Skip social media posting")
    
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
    logger.info(f"🔧 Options: dry_run={args.dry_run}, skip_podcast={args.skip_podcast}, skip_video={args.skip_video}, skip_social={args.skip_social}")
    
    start_time = time.time()
    
    try:
        # Initialize generators
        generator = ContentGenerator(config)
        quality_evaluator = QualityEvaluator()
        
        # Step 1: Monitor trends
        logger.info("Step 1: Monitoring GitHub trends...")
        repos = await generator.trend_monitor.monitor_trends("daily")
        top_repos = repos[:args.top_n]
        
        if not top_repos:
            logger.error("❌ No trending repositories found")
            sys.exit(1)
        
        logger.info(f"✅ Found {len(top_repos)} trending repos")
        
        # Step 2: Generate content with quality evaluation
        logger.info("Step 2: Generating content...")
        
        # Markdown (always generate)
        logger.info("  Generating Markdown...")
        md_content = generator.md_gen.generate_markdown(top_repos, datetime.now().strftime("%Y-%m-%d"))
        md_score = quality_evaluator.evaluate_markdown(md_content, top_repos)
        quality_evaluator.review_content("markdown-daily", "markdown", md_score)
        logger.info(f"  ✅ Markdown quality score: {md_score.overall:.2f}")
        
        # RSS/Atom
        logger.info("  Generating RSS/Atom feeds...")
        rss_xml, atom_xml = generator.rss_gen.generate_feed(top_repos, datetime.now().strftime("%Y-%m-%d"))
        logger.info("  ✅ RSS/Atom feeds generated")
        
        # Podcast (optional)
        podcast_path = None
        if not args.skip_podcast and config.get("ELEVENLABS_API_KEY"):
            if cost_optimizer.check_rate_limit("elevenlabs"):
                logger.info("  Generating Podcast...")
                try:
                    podcast_path = generator.podcast_gen.generate_podcast(top_repos, datetime.now().strftime("%Y-%m-%d"))
                    cost_optimizer.record_api_call("elevenlabs", cost=0.05)  # ~$0.05 per generation
                    logger.info(f"  ✅ Podcast generated: {podcast_path}")
                except Exception as e:
                    logger.error(f"  ❌ Podcast generation failed: {e}")
            else:
                logger.warning("  ⚠️ ElevenLabs rate limit reached, skipping podcast")
        
        # YouTube Video (optional)
        video_path = None
        if not args.skip_video and config.get("SHOTSTACK_API_KEY"):
            if cost_optimizer.check_rate_limit("shotstack"):
                logger.info("  Generating YouTube Video...")
                try:
                    video_path = generator.youtube_gen.generate_video(top_repos, datetime.now().strftime("%Y-%m-%d"))
                    cost_optimizer.record_api_call("shotstack", cost=0.50)  # ~$0.50 per video
                    logger.info(f"  ✅ YouTube video generated: {video_path}")
                except Exception as e:
                    logger.error(f"  ❌ Video generation failed: {e}")
            else:
                logger.warning("  ⚠️ Shotstack rate limit reached, skipping video")
        
        # Social Media (optional)
        tweets = None
        if not args.skip_social and config.get("TWITTER_API_KEY"):
            if cost_optimizer.check_rate_limit("twitter"):
                logger.info("  Generating Social Media posts...")
                try:
                    tweets = generator.social_gen.generate_tweets(top_repos, datetime.now().strftime("%Y-%m-%d"))
                    tweet_score = quality_evaluator.evaluate_tweets(tweets)
                    quality_evaluator.review_content("tweets-daily", "tweets", tweet_score)
                    logger.info(f"  ✅ Social media posts generated ({len(tweets)} tweets, quality: {tweet_score.overall:.2f})")
                    
                    # Post to Twitter (if not dry run)
                    if not args.dry_run:
                        generator.social_gen.post_to_twitter(tweets)
                        cost_optimizer.record_api_call("twitter", cost=0.001)
                        logger.info("  ✅ Tweets posted")
                except Exception as e:
                    logger.error(f"  ❌ Social media generation failed: {e}")
            else:
                logger.warning("  ⚠️ Twitter rate limit reached, skipping social posts")
        
        # Step 3: Save outputs
        logger.info("Step 3: Saving outputs...")
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Save Markdown
        md_path = output_dir / f"repodiscover-daily-{date_str}.md"
        md_path.write_text(md_content, encoding="utf-8")
        logger.info(f"  ✅ Markdown saved: {md_path}")
        
        # Save RSS
        rss_path = output_dir / "feed.xml"
        rss_path.write_text(rss_xml, encoding="utf-8")
        
        # Save Atom
        atom_path = output_dir / "feed.atom"
        atom_path.write_text(atom_xml, encoding="utf-8")
        logger.info(f"  ✅ RSS/Atom feeds saved")
        
        # Step 4: Generate summary report
        elapsed_time = time.time() - start_time
        cost_summary = cost_optimizer.get_cost_summary()
        quality_summary = {
            "total_reviews": len(quality_evaluator.reviews),
            "average_score": quality_evaluator.get_average_score().to_dict() if quality_evaluator.get_average_score() else None,
            "approval_rate": sum(1 for r in quality_evaluator.reviews if r.approved) / max(len(quality_evaluator.reviews), 1)
        }
        
        summary = {
            "date": date_str,
            "top_repos": [r.name for r in top_repos],
            "files": {
                "markdown": str(md_path),
                "rss": str(rss_path),
                "atom": str(atom_path),
                "podcast": podcast_path,
                "youtube": video_path
            },
            "social_media": tweets,
            "performance": {
                "elapsed_time_seconds": round(elapsed_time, 2),
                "metrics": perf_monitor.get_metrics()
            },
            "cost": cost_summary,
            "quality": quality_summary,
            "status": "success"
        }
        
        # Save summary
        summary_path = output_dir / f"digest-summary-{date_str}.json"
        summary_path.write_text(
            __import__("json").dumps(summary, indent=2, default=str),
            encoding="utf-8"
        )
        logger.info(f"  ✅ Summary saved: {summary_path}")
        
        # Log final report
        logger.info("\n" + "="*60)
        logger.info("📊 DAILY DIGEST REPORT")
        logger.info("="*60)
        logger.info(f"📅 Date: {date_str}")
        logger.info(f"📊 Repos: {len(top_repos)}")
        logger.info(f"⏱️  Time: {elapsed_time:.2f}s")
        logger.info(f"💰 Cost: ${cost_summary['total_cost']:.4f}")
        logger.info(f"⭐ Quality: {quality_summary['average_score']['overall']:.2f}" if quality_summary['average_score'] else "⭐ Quality: N/A")
        logger.info(f"✅ Approval Rate: {quality_summary['approval_rate']:.0%}")
        logger.info("="*60)
        
        if args.dry_run:
            logger.info("🔍 DRY RUN MODE - No content posted")
        
        logger.info("🎉 Daily digest generation complete!")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await generator.close()


if __name__ == "__main__":
    asyncio.run(main())
