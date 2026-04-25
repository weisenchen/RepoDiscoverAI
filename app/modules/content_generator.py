"""
RepoDiscoverAI v3.0 - Content Generator Orchestrator

Orchestrates multi-format content generation from trending repositories.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from .trend_monitor import RepoMetrics, TrendMonitor
from .podcast_generator import PodcastGenerator
from .youtube_generator import YouTubeGenerator
from .social_media_generator import SocialMediaGenerator
from .rss_generator import RSSGenerator
from .markdown_generator import MarkdownGenerator

logger = logging.getLogger(__name__)


class ContentGenerator:
    """Orchestrate multi-format content generation."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.trend_monitor = TrendMonitor(
            github_token=config.get("GITHUB_TOKEN")
        )
        self.podcast_gen = PodcastGenerator(config)
        self.youtube_gen = YouTubeGenerator(config)
        self.social_gen = SocialMediaGenerator(config)
        self.rss_gen = RSSGenerator(config)
        self.md_gen = MarkdownGenerator(config)
        
        self.output_dir = Path(config.get("OUTPUT_DIR", "./output"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def generate_daily_digest(self, top_n: int = 5) -> Dict:
        """
        Generate complete daily digest in all formats.
        
        Returns:
            Dict with paths to generated content
        """
        date = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"Starting daily digest generation for {date}")
        
        # Step 1: Monitor trends
        logger.info("Step 1: Monitoring GitHub trends...")
        repos = await self.trend_monitor.monitor_trends("daily")
        top_repos = repos[:top_n]
        
        if not top_repos:
            logger.warning("No trending repositories found")
            return {"error": "No trending repos found"}
        
        logger.info(f"Found {len(top_repos)} trending repos")
        
        # Step 2: Generate content in parallel
        logger.info("Step 2: Generating multi-format content...")
        
        # Markdown (Agent-ready)
        md_path = self.output_dir / f"repodiscover-daily-{date}.md"
        md_content = self.md_gen.generate_markdown(top_repos, date)
        md_path.write_text(md_content, encoding="utf-8")
        logger.info(f"✅ Markdown generated: {md_path}")
        
        # RSS/Atom Feed
        rss_xml, atom_xml = self.rss_gen.generate_feed(top_repos, date)
        rss_path = self.output_dir / "feed.xml"
        atom_path = self.output_dir / "feed.atom"
        rss_path.write_text(rss_xml, encoding="utf-8")
        atom_path.write_text(atom_xml, encoding="utf-8")
        logger.info(f"✅ RSS/Atom feeds generated")
        
        # Podcast Audio
        podcast_path = None
        if self.config.get("ELEVENLABS_API_KEY"):
            try:
                podcast_path = self.podcast_gen.generate_podcast(top_repos, date)
                logger.info(f"✅ Podcast generated: {podcast_path}")
            except Exception as e:
                logger.error(f"Podcast generation failed: {e}")
        
        # YouTube Video
        video_path = None
        if self.config.get("SHOTSTACK_API_KEY"):
            try:
                video_path = self.youtube_gen.generate_video(top_repos, date)
                logger.info(f"✅ YouTube video generated: {video_path}")
            except Exception as e:
                logger.error(f"YouTube video generation failed: {e}")
        
        # Social Media Posts
        tweets = None
        if self.config.get("TWITTER_API_KEY"):
            try:
                tweets = self.social_gen.generate_tweets(top_repos, date)
                logger.info(f"✅ Social media posts generated ({len(tweets)} tweets)")
            except Exception as e:
                logger.error(f"Social media generation failed: {e}")
        
        # Step 3: Compile results
        result = {
            "date": date,
            "top_repos": [r.name for r in top_repos],
            "files": {
                "markdown": str(md_path),
                "rss": str(rss_path),
                "atom": str(atom_path),
                "podcast": str(podcast_path) if podcast_path else None,
                "youtube": str(video_path) if video_path else None
            },
            "social_media": tweets,
            "status": "success"
        }
        
        logger.info("✅ Daily digest generation complete")
        return result
    
    async def close(self):
        """Close resources."""
        await self.trend_monitor.close()
