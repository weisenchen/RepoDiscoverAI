"""
RepoDiscoverAI v3.0 - YouTube Video Generator

Generates YouTube videos from trending repositories using Shotstack API.
"""

import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class YouTubeGenerator:
    """Generate YouTube videos from trending repos."""
    
    def __init__(self, config: dict):
        self.config = config
        self.api_key = config.get("SHOTSTACK_API_KEY")
        self.base_url = config.get("SHOTSTACK_BASE_URL", "https://api.shotstack.io/v1")
        self.output_dir = Path(config.get("OUTPUT_DIR", "./output"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def write_video_script(self, repos: list, date: str) -> str:
        """Generate YouTube video script."""
        script = f"""
        Welcome to RepoDiscoverAI! Today's date is {date}.
        
        We're looking at the top trending repositories on GitHub.
        These are the projects everyone is talking about right now.
        
        """
        
        for i, repo in enumerate(repos[:5], 1):
            script += f"""
            Number {i}: {repo.owner}/{repo.name}
            
            {repo.description}
            
            This repository has {repo.stars} stars and
            {repo.forks} forks. It was last updated on
            {repo.last_updated[:10] if repo.last_updated else 'recently'}.
            
            """
        
        script += """
        That's our top 5 for today! Don't forget to like and
        subscribe for daily updates on the hottest open source
        projects.
        
        See you next time!
        """
        
        return script.strip()
    
    def generate_video(self, repos: list, date: str) -> str:
        """
        Generate YouTube video using Shotstack API.
        
        Returns:
            Render ID or file path
        """
        if not self.api_key:
            raise ValueError("SHOTSTACK_API_KEY not configured")
        
        try:
            import requests
            
            # Step 1: Write script
            script = self.write_video_script(repos, date)
            logger.info(f"YouTube script generated ({len(script)} chars)")
            
            # Step 2: Create video edit
            edit = {
                "sequence": [
                    {
                        "type": "color",
                        "color": "#1a1a2e",
                        "duration": 30
                    },
                    {
                        "type": "text",
                        "text": f"RepoDiscoverAI - {date}",
                        "position": "top",
                        "duration": 5
                    },
                    *[self._create_repo_card(repo, i) for i, repo in enumerate(repos[:5])],
                    {
                        "type": "text",
                        "text": "Subscribe for daily updates!",
                        "position": "bottom",
                        "duration": 3
                    }
                ]
            }
            
            # Step 3: Submit render job
            logger.info("Submitting video render to Shotstack...")
            response = requests.post(
                f"{self.base_url}/renders",
                headers={"X-Api-Key": self.api_key},
                json={
                    "edit": edit,
                    "output": {
                        "format": "mp4",
                        "resolution": "hd"
                    }
                }
            )
            
            if response.status_code == 200:
                render_id = response.json().get("id", "unknown")
                logger.info(f"✅ Video render submitted: {render_id}")
                return render_id
            else:
                logger.error(f"Shotstack API error: {response.text}")
                raise Exception(f"Shotstack API error: {response.status_code}")
                
        except ImportError:
            raise ImportError("requests package not installed")
        except Exception as e:
            logger.error(f"Error generating video: {e}")
            raise
    
    def _create_repo_card(self, repo, index: int) -> dict:
        """Create a video card for a repository."""
        return {
            "type": "text",
            "text": f"#{index+1}: {repo.owner}/{repo.name}\n{repo.description[:80]}...\n⭐ {repo.stars} stars",
            "position": "center",
            "duration": 5,
            "style": "title"
        }
