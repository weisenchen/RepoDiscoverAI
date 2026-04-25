"""
RepoDiscoverAI v3.0 - Podcast Audio Generator

Generates podcast audio from trending repositories using ElevenLabs API.
"""

import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PodcastGenerator:
    """Generate podcast audio from trending repos."""
    
    def __init__(self, config: dict):
        self.config = config
        self.api_key = config.get("ELEVENLABS_API_KEY")
        self.voice_id = config.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel
        self.model = config.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")
        self.output_dir = Path(config.get("OUTPUT_DIR", "./output"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def write_script(self, repos: list, date: str) -> str:
        """Generate podcast script from repos."""
        script = f"""
        🎙️ RepoDiscoverAI Daily Digest - {date}
        
        Welcome to today's episode where we explore the hottest
        repositories on GitHub! I'm your host, and today we're
        looking at the top {len(repos)} trending projects.
        
        """
        
        for i, repo in enumerate(repos[:5], 1):
            script += f"""
            📌 Number {i}: {repo.owner}/{repo.name}
            
            {repo.description}
            
            This repository has {repo.stars} stars and
            {repo.forks} forks. It was last updated on
            {repo.last_updated[:10] if repo.last_updated else 'recently'}.
            
            """
        
        script += """
        That's all for today! Subscribe for daily updates on the
        most exciting open source projects.
        
        Thanks for listening, and happy coding!
        """
        
        return script.strip()
    
    def generate_podcast(self, repos: list, date: str) -> str:
        """
        Generate podcast audio using ElevenLabs API.
        
        Returns:
            Path to generated MP3 file
        """
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY not configured")
        
        try:
            from elevenlabs import generate, save
            
            # Step 1: Write script
            script = self.write_script(repos, date)
            logger.info(f"Podcast script generated ({len(script)} chars)")
            
            # Step 2: Generate voiceover
            logger.info("Generating voiceover with ElevenLabs...")
            audio = generate(
                text=script,
                voice=self.voice_id,
                model=self.model
            )
            
            # Step 3: Save audio
            filename = f"repodiscover-podcast-{date}.mp3"
            filepath = self.output_dir / filename
            save(audio, str(filepath))
            
            logger.info(f"✅ Podcast saved to {filepath}")
            return str(filepath)
            
        except ImportError:
            raise ImportError("elevenlabs package not installed. Run: pip install elevenlabs")
        except Exception as e:
            logger.error(f"Error generating podcast: {e}")
            raise
