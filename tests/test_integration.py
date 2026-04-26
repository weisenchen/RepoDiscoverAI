"""
RepoDiscoverAI v3.0 - Integration Tests

End-to-end tests for content generation pipeline.
"""

import pytest
import asyncio
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from app.modules.trend_monitor import TrendMonitor, RepoMetrics
from app.modules.content_generator import ContentGenerator
from app.modules.podcast_generator import PodcastGenerator
from app.modules.youtube_generator import YouTubeGenerator
from app.modules.social_media_generator import SocialMediaGenerator
from app.modules.rss_generator import RSSGenerator
from app.modules.markdown_generator import MarkdownGenerator


@pytest.fixture
def test_config():
    """Test configuration."""
    return {
        "GITHUB_TOKEN": "test-token",
        "ELEVENLABS_API_KEY": "test-key",
        "SHOTSTACK_API_KEY": "test-key",
        "TWITTER_API_KEY": "test-key",
        "TWITTER_API_SECRET": "test-key",
        "TWITTER_ACCESS_TOKEN": "test-key",
        "TWITTER_ACCESS_TOKEN_SECRET": "test-key",
        "SITE_URL": "https://test.example.com",
        "OUTPUT_DIR": "./test-output"
    }


@pytest.fixture
def sample_repos():
    """Create sample repos for testing."""
    return [
        RepoMetrics(
            name="agent-governance-toolkit",
            owner="microsoft",
            description="Open-source runtime security for AI agents. Addresses all 10 OWASP Agentic AI risks.",
            language="Python",
            stars=3200,
            forks=180,
            stars_today=139,
            forks_today=12,
            issues_opened_7d=25,
            issues_closed_7d=20,
            prs_merged_7d=15,
            total_prs=50,
            last_updated="2026-04-25T10:00:00",
            url="https://github.com/microsoft/agent-governance-toolkit",
            trend_score=0.8472
        ),
        RepoMetrics(
            name="last30days-skill",
            owner="mvanhorn",
            description="AI agent skill that researches any topic across Reddit, X, YouTube, HN, Polymarket.",
            language="Python",
            stars=2800,
            forks=95,
            stars_today=89,
            forks_today=8,
            issues_opened_7d=12,
            issues_closed_7d=10,
            prs_merged_7d=8,
            total_prs=30,
            last_updated="2026-04-25T12:00:00",
            url="https://github.com/mvanhorn/last30days-skill",
            trend_score=0.7234
        ),
        RepoMetrics(
            name="openclaw",
            owner="openclaw",
            description="Open-source AI agent platform for personal productivity and automation.",
            language="TypeScript",
            stars=351000,
            forks=12000,
            stars_today=500,
            forks_today=45,
            issues_opened_7d=100,
            issues_closed_7d=85,
            prs_merged_7d=50,
            total_prs=200,
            last_updated="2026-04-25T14:00:00",
            url="https://github.com/openclaw/openclaw",
            trend_score=0.9123
        )
    ]


class TestEndToEndPipeline:
    """Test complete content generation pipeline."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline(self, test_config, sample_repos, tmp_path):
        """Test complete pipeline from monitoring to content generation."""
        # Override output directory
        test_config["OUTPUT_DIR"] = str(tmp_path)
        
        generator = ContentGenerator(test_config)
        
        # Mock monitoring
        with patch.object(generator.trend_monitor, 'monitor_trends') as mock_monitor:
            mock_monitor.return_value = sample_repos
            
            # Mock content generators
            with patch.object(generator.md_gen, 'generate_markdown') as mock_md, \
                 patch.object(generator.rss_gen, 'generate_feed') as mock_rss, \
                 patch.object(generator.podcast_gen, 'generate_podcast') as mock_podcast, \
                 patch.object(generator.youtube_gen, 'generate_video') as mock_youtube, \
                 patch.object(generator.social_gen, 'generate_tweets') as mock_tweets:
                
                mock_md.return_value = "# Test Markdown Content"
                mock_rss.return_value = ("<rss>test</rss>", "<atom>test</atom>")
                mock_podcast.return_value = str(tmp_path / "podcast.mp3")
                mock_youtube.return_value = "render-123"
                mock_tweets.return_value = ["Tweet 1", "Tweet 2", "Tweet 3"]
                
                # Run pipeline
                result = await generator.generate_daily_digest(top_n=3)
                
                # Verify results
                assert result["status"] == "success"
                assert len(result["top_repos"]) == 3
                assert "files" in result
                assert result["files"]["markdown"] is not None
                assert result["files"]["rss"] is not None
                assert result["files"]["atom"] is not None
                assert result["files"]["podcast"] is not None
                assert result["files"]["youtube"] is not None
                assert len(result["social_media"]) == 3
        
        await generator.close()
    
    @pytest.mark.asyncio
    async def test_pipeline_with_partial_failure(self, test_config, sample_repos, tmp_path):
        """Test pipeline handles partial failures gracefully."""
        test_config["OUTPUT_DIR"] = str(tmp_path)
        generator = ContentGenerator(test_config)
        
        with patch.object(generator.trend_monitor, 'monitor_trends') as mock_monitor:
            mock_monitor.return_value = sample_repos
            
            # Mock successful markdown/RSS but failed podcast
            with patch.object(generator.md_gen, 'generate_markdown') as mock_md, \
                 patch.object(generator.rss_gen, 'generate_feed') as mock_rss, \
                 patch.object(generator.podcast_gen, 'generate_podcast') as mock_podcast:
                
                mock_md.return_value = "# Test"
                mock_rss.return_value = ("<rss></rss>", "<atom></atom>")
                mock_podcast.side_effect = Exception("API Error")
                
                result = await generator.generate_daily_digest(top_n=3)
                
                # Should still succeed with partial content
                assert result["status"] == "success"
                assert result["files"]["markdown"] is not None
                assert result["files"]["podcast"] is None  # Failed
        
        await generator.close()


class TestMarkdownGeneratorIntegration:
    """Test Markdown generator with real data."""
    
    def test_generate_complete_markdown(self, test_config, sample_repos):
        """Test markdown generation with sample repos."""
        gen = MarkdownGenerator(test_config)
        date = "2026-04-26"
        
        markdown = gen.generate_markdown(sample_repos, date)
        
        # Verify structure
        assert "# RepoDiscoverAI Daily Digest" in markdown
        assert "## Executive Summary" in markdown
        assert "## Top Repositories" in markdown
        assert "## Trend Analysis" in markdown
        assert "## Data Sources" in markdown
        
        # Verify content
        assert "microsoft/agent-governance-toolkit" in markdown
        assert "mvanhorn/last30days-skill" in markdown
        assert "openclaw/openclaw" in markdown
        
        # Verify metrics
        assert "3,200" in markdown  # stars
        assert "0.8472" in markdown  # trend score
        assert "Python" in markdown  # language
        
        # Verify metadata
        assert "*Generated by RepoDiscoverAI v3.0*" in markdown
        assert "Next update:" in markdown


class TestRSSGeneratorIntegration:
    """Test RSS generator with real data."""
    
    def test_generate_complete_rss(self, test_config, sample_repos):
        """Test RSS/Atom generation with sample repos."""
        gen = RSSGenerator(test_config)
        date = "2026-04-26"
        
        rss_xml, atom_xml = gen.generate_feed(sample_repos, date)
        
        # Verify RSS structure
        assert "<?xml" in rss_xml
        assert "<rss" in rss_xml
        assert "<channel>" in rss_xml
        assert "<title>RepoDiscoverAI Daily Digest</title>" in rss_xml
        assert "microsoft/agent-governance-toolkit" in rss_xml
        assert "⭐ 3,200 stars" in rss_xml
        
        # Verify Atom structure
        assert "<?xml" in atom_xml
        assert "<feed" in atom_xml
        assert "RepoDiscoverAI Daily Digest" in atom_xml


class TestSocialMediaGeneratorIntegration:
    """Test social media generator with real data."""
    
    def test_generate_complete_thread(self, test_config, sample_repos):
        """Test tweet thread generation with sample repos."""
        gen = SocialMediaGenerator(test_config)
        date = "2026-04-26"
        
        tweets = gen.generate_tweets(sample_repos, date)
        
        # Verify structure
        assert len(tweets) == 8  # Hook + 3 repos + CTA (adjusted for 3 repos)
        assert "🚀 Top 3 GitHub Repos Today" in tweets[0]
        assert "microsoft/agent-governance-toolkit" in tweets[1]
        assert "#OpenSource #GitHub #AI" in tweets[1]
        assert "Follow @RepoDiscoverAI" in tweets[-1]
        assert "#AI #Tech #Developers #OpenSource" in tweets[-1]


class TestPerformanceOptimization:
    """Test performance optimizations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_fetching(self, test_config):
        """Test concurrent API fetching."""
        from app.modules.trend_monitor import TrendMonitor
        
        monitor = TrendMonitor(test_config.get("GITHUB_TOKEN"))
        
        # Mock concurrent requests
        with patch.object(monitor.client, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"stargazers_count": 1000}
            mock_get.return_value = mock_response
            
            # Fetch multiple repos concurrently
            tasks = [
                monitor.fetch_github_api_data("owner1", "repo1"),
                monitor.fetch_github_api_data("owner2", "repo2"),
                monitor.fetch_github_api_data("owner3", "repo3"),
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 3
            assert all(r.get("stars") == 1000 for r in results)
        
        await monitor.close()
    
    @pytest.mark.asyncio
    async def test_cache_integration(self, test_config, tmp_path):
        """Test cache reduces API calls."""
        from app.core.cache import CacheManager
        
        cache = CacheManager(str(tmp_path / "cache"))
        
        # First call - cache miss
        result1 = await cache.get("test-key")
        assert result1 is None
        
        # Set value
        await cache.set("test-key", {"data": "test"}, ttl=3600)
        
        # Second call - cache hit
        result2 = await cache.get("test-key")
        assert result2 == {"data": "test"}
        
        # Invalidate
        await cache.invalidate("test-key")
        result3 = await cache.get("test-key")
        assert result3 is None


class TestCostOptimization:
    """Test cost optimization features."""
    
    def test_api_budget_tracker(self):
        """Test API budget tracking."""
        from app.core.cost_optimizer import CostOptimizer, APICallTracker
        
        tracker = APICallTracker()
        
        # Track API calls
        tracker.record_call("github", 1)
        tracker.record_call("github", 1)
        tracker.record_call("elevenlabs", 1)
        
        assert tracker.get_calls("github") == 2
        assert tracker.get_calls("elevenlabs") == 1
        assert tracker.get_total_calls() == 3
        
        # Check budget
        budget = {"github": 5000, "elevenlabs": 10000}
        assert tracker.is_within_budget(budget) is True
        
        # Exceed budget
        for _ in range(5000):
            tracker.record_call("github", 1)
        assert tracker.is_within_budget(budget) is False
    
    def test_rate_limiter(self):
        """Test rate limiter."""
        from app.core.cost_optimizer import RateLimiter
        import time
        
        limiter = RateLimiter(max_calls=5, time_window=1.0)
        
        # Should allow 5 calls
        for i in range(5):
            assert limiter.can_proceed() is True
        
        # 6th call should be blocked
        assert limiter.can_proceed() is False
        
        # Wait for window to reset
        time.sleep(1.1)
        assert limiter.can_proceed() is True
