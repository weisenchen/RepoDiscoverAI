"""
RepoDiscoverAI v3.0 - RSS/Atom Feed Generator

Generates RSS and Atom feeds from trending repositories.
"""

import logging
from datetime import datetime
from typing import List, Tuple

logger = logging.getLogger(__name__)


class RSSGenerator:
    """Generate RSS/Atom feeds from trending repos."""
    
    def __init__(self, config: dict):
        self.config = config
        self.site_url = config.get("SITE_URL", "https://repodiscoverai.com")
        self.feed_title = "RepoDiscoverAI Daily Digest"
        self.feed_description = "Daily digest of top trending GitHub repositories"
    
    def generate_feed(self, repos: list, date: str) -> Tuple[str, str]:
        """
        Generate RSS and Atom feeds.
        
        Returns:
            Tuple of (RSS XML, Atom XML)
        """
        try:
            from feedgen.feed import FeedGenerator
            
            # Create feed
            fg = FeedGenerator()
            fg.id(f'{self.site_url}/feed')
            fg.title(self.feed_title)
            fg.link(href=self.site_url, rel='alternate')
            fg.subtitle(self.feed_description)
            fg.language('en')
            fg.generator('RepoDiscoverAI v3.0')
            
            # Add entries
            for repo in repos:
                fe = fg.add_entry()
                fe.id(repo.url)
                fe.title(f"{repo.owner}/{repo.name}: {repo.description[:50]}...")
                fe.link(href=repo.url)
                fe.description(self._format_entry(repo))
                fe.pubDate(repo.last_updated or datetime.now().isoformat())
                fe.author({'name': 'RepoDiscoverAI'})
                fe.category(term=repo.language or "Programming")
            
            # Generate feeds
            rss_xml = fg.rss_str(pretty=True).decode('utf-8')
            atom_xml = fg.atom_str(pretty=True).decode('utf-8')
            
            logger.info(f"✅ RSS/Atom feeds generated ({len(repos)} entries)")
            return rss_xml, atom_xml
            
        except ImportError:
            raise ImportError("feedgen package not installed. Run: pip install feedgen")
        except Exception as e:
            logger.error(f"Error generating feeds: {e}")
            raise
    
    def _format_entry(self, repo) -> str:
        """Format RSS entry for a repo."""
        return f"""
        <h2>{repo.owner}/{repo.name}</h2>
        <p>{repo.description}</p>
        <ul>
            <li>⭐ {repo.stars} stars</li>
            <li>🍴 {repo.forks} forks</li>
            <li>📅 Last updated: {repo.last_updated[:10] if repo.last_updated else 'N/A'}</li>
            <li>🌐 Language: {repo.language or 'N/A'}</li>
        </ul>
        <p><a href="{repo.url}">View on GitHub</a></p>
        <p><strong>Trend Score:</strong> {repo.trend_score:.4f}</p>
        """.strip()
