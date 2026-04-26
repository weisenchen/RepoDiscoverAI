"""
RepoDiscoverAI v3.0 - Content Generator Tests
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime
from app.modules.content_generator import ContentGenerator
from app.modules.trend_monitor import RepoMetrics


@pytest.fixture
def config():
    """Test configuration."""
    return {
        "GITHUB_TOKEN": "test-token",
        "ELEVENLABS_API_KEY": "test-key",
        "SHOTSTACK_API_KEY": "test-key",
        "TWITTER_API_KEY": "test-key",
        "OUTPUT_DIR": "./test-output",
        "SITE_URL": "https://test.example.com"
    }


@pytest.fixture
def generator(config):
    """Create ContentGenerator instance."""
    return ContentGenerator(config)


@pytest.fixture
def sample_repos():
    """Create sample repos."""
    return [
        RepoMetrics(
            name="repo1",
            owner="owner1",
            description="Test repository 1",
            language="Python",
            stars=1000,
            forks=100,
            last_updated="2026-04-25T10:00:00",
            url="https://github.com/owner1/repo1",
            trend_score=0.85
        ),
        RepoMetrics(
            name="repo2",
            owner="owner2",
            description="Test repository 2",
            language="TypeScript",
            stars=5000,
            forks=500,
            last_updated="2026-04-25T12:00:00",
            url="https://github.com/owner2/repo2",
            trend_score=0.92
        )
    ]


class TestContentGenerator:
    """Test ContentGenerator class."""
    
    @pytest.mark.asyncio
    async def test_generate_daily_digest(self, generator, sample_repos):
        """Test daily digest generation."""
        with patch.object(generator.trend_monitor, 'monitor_trends') as mock_monitor, \
             patch.object(generator.md_gen, 'generate_markdown') as mock_md, \
             patch.object(generator.rss_gen, 'generate_feed') as mock_rss, \
             patch.object(generator.podcast_gen, 'generate_podcast') as mock_podcast, \
             patch.object(generator.youtube_gen, 'generate_video') as mock_youtube, \
             patch.object(generator.social_gen, 'generate_tweets') as mock_tweets:
            
            mock_monitor.return_value = sample_repos
            mock_md.return_value = "# Test Markdown"
            mock_rss.return_value = ("<rss></rss>", "<atom></atom>")
            mock_podcast.return_value = "./output/podcast.mp3"
            mock_youtube.return_value = "render-123"
            mock_tweets.return_value = ["Tweet 1", "Tweet 2"]
            
            result = await generator.generate_daily_digest(top_n=2)
            
            assert result["status"] == "success"
            assert len(result["top_repos"]) == 2
            assert "files" in result
            assert result["files"]["podcast"] == "./output/podcast.mp3"
            assert result["files"]["youtube"] == "render-123"
            assert len(result["social_media"]) == 2
    
    @pytest.mark.asyncio
    async def test_generate_daily_digest_no_repos(self, generator):
        """Test digest generation with no repos."""
        with patch.object(generator.trend_monitor, 'monitor_trends') as mock_monitor:
            mock_monitor.return_value = []
            
            result = await generator.generate_daily_digest(top_n=5)
            
            assert "error" in result
            assert result["error"] == "No trending repos found"
    
    @pytest.mark.asyncio
    async def test_close(self, generator):
        """Test cleanup."""
        with patch.object(generator.trend_monitor, 'close') as mock_close:
            await generator.close()
            mock_close.assert_called_once()


class TestMarkdownGenerator:
    """Test MarkdownGenerator class."""
    
    def test_generate_markdown(self, config, sample_repos):
        """Test markdown generation."""
        from app.modules.markdown_generator import MarkdownGenerator
        
        gen = MarkdownGenerator(config)
        date = "2026-04-25"
        
        markdown = gen.generate_markdown(sample_repos, date)
        
        assert "# RepoDiscoverAI Daily Digest" in markdown
        assert "owner1/repo1" in markdown
        assert "owner2/repo2" in markdown
        assert "0.8500" in markdown  # trend score
        assert "0.9200" in markdown
        assert "## Trend Analysis" in markdown
        assert "## Data Sources" in markdown


class TestRSSGenerator:
    """Test RSSGenerator class."""
    
    def test_generate_feed(self, config, sample_repos):
        """Test RSS/Atom feed generation."""
        from app.modules.rss_generator import RSSGenerator
        
        gen = RSSGenerator(config)
        date = "2026-04-25"
        
        rss_xml, atom_xml = gen.generate_feed(sample_repos, date)
        
        assert "<?xml" in rss_xml
        assert "<rss" in rss_xml
        assert "RepoDiscoverAI Daily Digest" in rss_xml
        assert "owner1/repo1" in rss_xml
        
        assert "<?xml" in atom_xml
        assert "<feed" in atom_xml


class TestSocialMediaGenerator:
    """Test SocialMediaGenerator class."""
    
    def test_generate_tweets(self, config, sample_repos):
        """Test tweet generation."""
        from app.modules.social_media_generator import SocialMediaGenerator
        
        gen = SocialMediaGenerator(config)
        date = "2026-04-25"
        
        tweets = gen.generate_tweets(sample_repos, date)
        
        assert len(tweets) == 7  # Hook + 5 repos + CTA
        assert "🚀 Top 2 GitHub Repos Today" in tweets[0]
        assert "#OpenSource #GitHub #AI" in tweets[1]
        assert "Follow @RepoDiscoverAI" in tweets[-1]
