"""
RepoDiscoverAI v3.0 - Social Media Generator

Generates social media posts (Twitter/X thread) from trending repositories.
"""

import logging
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)


class SocialMediaGenerator:
    """Generate social media content from trending repos."""
    
    def __init__(self, config: dict):
        self.config = config
        self.twitter_config = {
            "bearer_token": config.get("TWITTER_BEARER_TOKEN"),
            "consumer_key": config.get("TWITTER_API_KEY"),
            "consumer_secret": config.get("TWITTER_API_SECRET"),
            "access_token": config.get("TWITTER_ACCESS_TOKEN"),
            "access_token_secret": config.get("TWITTER_ACCESS_TOKEN_SECRET")
        }
    
    def generate_tweets(self, repos: list, date: str) -> List[str]:
        """
        Generate tweet thread from repos.
        
        Returns:
            List of tweet texts
        """
        tweets = []
        
        # Tweet 1: Hook
        tweets.append(f"""
🚀 Top {len(repos)} GitHub Repos Today ({date})

Here are the hottest repositories trending right now!

Thread 🧵👇
        """.strip())
        
        # Tweets 2-6: Repo details
        for i, repo in enumerate(repos[:5], 1):
            desc = repo.description[:100] + "..." if len(repo.description) > 100 else repo.description
            tweets.append(f"""
#{i} {repo.owner}/{repo.name}

{desc}

⭐ {repo.stars} stars | 🍴 {repo.forks} forks
📅 Updated {repo.last_updated[:10] if repo.last_updated else 'recently'}

🔗 {repo.url}

#OpenSource #GitHub #AI #Tech
            """.strip())
        
        # Tweet 7: CTA
        tweets.append(f"""
That's it for today!

Follow @RepoDiscoverAI for daily updates on the
hottest open source projects.

#AI #Tech #Developers #OpenSource
        """.strip())
        
        return tweets
    
    def post_to_twitter(self, tweets: List[str]) -> Optional[dict]:
        """
        Post tweets using Twitter API v2.
        
        Returns:
            Response data or None
        """
        if not self.twitter_config.get("consumer_key"):
            raise ValueError("Twitter API credentials not configured")
        
        try:
            import tweepy
            
            client = tweepy.Client(
                bearer_token=self.twitter_config["bearer_token"],
                consumer_key=self.twitter_config["consumer_key"],
                consumer_secret=self.twitter_config["consumer_secret"],
                access_token=self.twitter_config["access_token"],
                access_token_secret=self.twitter_config["access_token_secret"]
            )
            
            # Post thread
            response = None
            for tweet in tweets:
                if response is None:
                    response = client.create_tweet(text=tweet)
                else:
                    response = client.create_tweet(
                        text=tweet,
                        in_reply_to_tweet_id=response.data['id']
                    )
            
            logger.info(f"✅ Tweet thread posted successfully")
            return response.data
            
        except ImportError:
            raise ImportError("tweepy package not installed. Run: pip install tweepy")
        except Exception as e:
            logger.error(f"Error posting to Twitter: {e}")
            raise
