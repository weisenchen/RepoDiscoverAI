"""
RepoDiscoverAI v3.0 - Trend Monitor Tests
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.modules.trend_monitor import TrendMonitor, RepoMetrics


@pytest.fixture
def monitor():
    """Create TrendMonitor instance."""
    return TrendMonitor(github_token="test-token")


@pytest.fixture
def sample_repos():
    """Create sample repos for testing."""
    return [
        RepoMetrics(
            name="repo1",
            owner="owner1",
            description="Test repo 1",
            language="Python",
            stars=1000,
            forks=100,
            stars_today=50,
            forks_today=5,
            issues_opened_7d=10,
            issues_closed_7d=8,
            prs_merged_7d=5,
            total_prs=20,
            last_updated="2026-04-25T10:00:00",
            url="https://github.com/owner1/repo1"
        ),
        RepoMetrics(
            name="repo2",
            owner="owner2",
            description="Test repo 2",
            language="TypeScript",
            stars=5000,
            forks=500,
            stars_today=200,
            forks_today=20,
            issues_opened_7d=25,
            issues_closed_7d=20,
            prs_merged_7d=15,
            total_prs=50,
            last_updated="2026-04-25T12:00:00",
            url="https://github.com/owner2/repo2"
        )
    ]


class TestTrendMonitor:
    """Test TrendMonitor class."""
    
    def test_calculate_trend_score(self, monitor, sample_repos):
        """Test trend score calculation."""
        repo = sample_repos[0]
        score = monitor.calculate_trend_score(repo)
        
        # Score should be positive
        assert score > 0
        
        # Higher velocity should yield higher score
        repo2 = sample_repos[1]
        score2 = monitor.calculate_trend_score(repo2)
        assert score2 > score  # repo2 has higher velocity
    
    @pytest.mark.asyncio
    async def test_fetch_github_trending(self, monitor):
        """Test fetching trending repos."""
        with patch.object(monitor.client, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = """
            <html>
                <article class="Box-row">
                    <h2><a href="/owner/repo">repo</a></h2>
                    <p>Test description</p>
                    <span itemtype="programmingLanguage">Python</span>
                    <a class="Link--muted">1,000</a>
                </article>
            </html>
            """
            mock_get.return_value = mock_response
            
            repos = await monitor.fetch_github_trending("daily")
            
            assert len(repos) > 0
            assert repos[0].name == "repo"
            assert repos[0].owner == "owner"
            assert repos[0].language == "Python"
    
    @pytest.mark.asyncio
    async def test_monitor_trends(self, monitor):
        """Test full monitoring workflow."""
        with patch.object(monitor, 'fetch_github_trending') as mock_trending, \
             patch.object(monitor, 'fetch_github_api_data') as mock_api:
            
            mock_trending.return_value = [
                RepoMetrics(
                    name="test-repo",
                    owner="test-owner",
                    description="Test",
                    language="Python",
                    stars=100,
                    url="https://github.com/test-owner/test-repo"
                )
            ]
            mock_api.return_value = {
                "stars": 150,
                "forks": 10,
                "issues_opened_7d": 5,
                "issues_closed_7d": 3,
                "prs_merged_7d": 2,
                "total_prs": 10,
                "language": "Python",
                "last_updated": "2026-04-25"
            }
            
            repos = await monitor.monitor_trends("daily")
            
            assert len(repos) == 1
            assert repos[0].trend_score > 0
            assert repos[0].stars == 150
    
    @pytest.mark.asyncio
    async def test_close(self, monitor):
        """Test cleanup."""
        with patch.object(monitor.client, 'aclose') as mock_close:
            await monitor.close()
            mock_close.assert_called_once()


class TestRepoMetrics:
    """Test RepoMetrics dataclass."""
    
    def test_default_values(self):
        """Test default values."""
        repo = RepoMetrics(
            name="test",
            owner="owner",
            description="desc",
            language="Python"
        )
        
        assert repo.stars == 0
        assert repo.forks == 0
        assert repo.trend_score == 0.0
    
    def test_custom_values(self):
        """Test custom values."""
        repo = RepoMetrics(
            name="test",
            owner="owner",
            description="desc",
            language="Python",
            stars=1000,
            forks=100,
            trend_score=0.5
        )
        
        assert repo.stars == 1000
        assert repo.forks == 100
        assert repo.trend_score == 0.5
