"""
Email Notification System

Send email notifications for trending repos, saved searches, and collection updates.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class EmailTemplate:
    """Email template manager."""
    
    TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates" / "emails"
    
    @classmethod
    def get_template(cls, name: str) -> str:
        """Load email template from file."""
        template_path = cls.TEMPLATES_DIR / f"{name}.html"
        if template_path.exists():
            return template_path.read_text()
        return cls._get_default_template(name)
    
    @classmethod
    def _get_default_template(cls, name: str) -> str:
        """Return default template if file not found."""
        templates = {
            "trending_alert": cls._trending_alert_template(),
            "saved_search_match": cls._saved_search_match_template(),
            "collection_update": cls._collection_update_template(),
            "gfi_alert": cls._gfi_alert_template(),
            "welcome": cls._welcome_template(),
        }
        return templates.get(name, "<html><body>{{content}}</body></html>")
    
    @staticmethod
    def _trending_alert_template() -> str:
        return """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        .repo { border-left: 3px solid #0366d6; padding-left: 15px; margin: 20px 0; }
        .repo-name { font-size: 18px; font-weight: bold; color: #0366d6; }
        .repo-desc { color: #586069; margin: 8px 0; }
        .repo-stats { color: #959da5; font-size: 14px; }
        .cta-button { 
            display: inline-block; 
            padding: 10px 20px; 
            background: #0366d6; 
            color: white; 
            text-decoration: none; 
            border-radius: 6px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <h1>🔥 Today's Trending Repositories</h1>
    <p>Here are the hot repositories trending on GitHub today:</p>
    
    {{#repos}}
    <div class="repo">
        <div class="repo-name">
            <a href="{{html_url}}">{{full_name}}</a>
        </div>
        <div class="repo-desc">{{description}}</div>
        <div class="repo-stats">
            ⭐ {{stargazers_count}} stars | 🍴 {{forks_count}} forks | 📅 {{updated_at}}
        </div>
    </div>
    {{/repos}}
    
    <a href="{{view_all_url}}" class="cta-button">View All Trending</a>
    
    <hr style="margin: 30px 0; border: none; border-top: 1px solid #eaecef;">
    <p style="color: #959da5; font-size: 12px;">
        You're receiving this because you subscribed to trending alerts.
        <a href="{{unsubscribe_url}}">Unsubscribe</a>
    </p>
</body>
</html>
"""
    
    @staticmethod
    def _saved_search_match_template() -> str:
        return """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        .match { background: #f6f8fa; padding: 15px; border-radius: 6px; margin: 15px 0; }
        .match-name { font-weight: bold; color: #0366d6; }
    </style>
</head>
<body>
    <h1>🔍 New Matches for Your Saved Search</h1>
    <p>Your saved search "<strong>{{search_name}}</strong>" has {{count}} new matches:</p>
    
    {{#matches}}
    <div class="match">
        <div class="match-name">
            <a href="{{html_url}}">{{full_name}}</a>
        </div>
        <p>{{description}}</p>
    </div>
    {{/matches}}
    
    <p><a href="{{view_all_url}}">View all matches →</a></p>
    
    <hr style="margin: 30px 0; border: none; border-top: 1px solid #eaecef;">
    <p style="color: #959da5; font-size: 12px;">
        <a href="{{preferences_url}}">Manage notification preferences</a>
    </p>
</body>
</html>
"""
    
    @staticmethod
    def _collection_update_template() -> str:
        return """
<!DOCTYPE html>
<html>
<body>
    <h1>📚 Collection Update</h1>
    <p>Your collection "<strong>{{collection_name}}</strong>" has been updated with {{count}} new repositories.</p>
    <p><a href="{{collection_url}}">View collection →</a></p>
</body>
</html>
"""
    
    @staticmethod
    def _gfi_alert_template() -> str:
        return """
<!DOCTYPE html>
<html>
<body>
    <h1>🎯 Good First Issues</h1>
    <p>Found {{count}} new beginner-friendly issues in your watched languages:</p>
    {{#issues}}
    <div>
        <a href="{{html_url}}">{{title}}</a> - {{repo}}
    </div>
    {{/issues}}
</body>
</html>
"""
    
    @staticmethod
    def _welcome_template() -> str:
        return """
<!DOCTYPE html>
<html>
<body>
    <h1>👋 Welcome to RepoDiscoverAI!</h1>
    <p>Thanks for subscribing. You'll now receive notifications about:</p>
    <ul>
        <li>Daily trending repositories</li>
        <li>Matches for your saved searches</li>
        <li>Good first issues in your languages</li>
    </ul>
    <p><a href="{{dashboard_url}}">Go to your dashboard →</a></p>
</body>
</html>
"""


class NotificationService:
    """Email notification service."""
    
    def __init__(
        self,
        smtp_host: str = "smtp.gmail.com",
        smtp_port: int = 587,
        sender_email: Optional[str] = None,
        sender_password: Optional[str] = None
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self._render = self._simple_render
    
    def _simple_render(self, template: str, context: Dict) -> str:
        """Simple template rendering (replace {{key}} with value)."""
        result = template
        for key, value in context.items():
            if isinstance(value, list):
                # Handle simple loops
                pass
            else:
                result = result.replace(f"{{{{{key}}}}}", str(value))
        return result
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: Dict,
        html: bool = True
    ) -> bool:
        """Send email notification."""
        try:
            # Load and render template
            template = EmailTemplate.get_template(template_name)
            content = self._render(template, context)
            
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = to_email
            
            # Attach content
            msg_type = "html" if html else "plain"
            msg.attach(MIMEText(content, msg_type))
            
            # Send (mock for now - implement real SMTP when needed)
            logger.info(f"📧 Would send email to {to_email}: {subject}")
            logger.debug(f"Content preview: {content[:200]}...")
            
            # Uncomment to actually send:
            # with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            #     server.starttls()
            #     server.login(self.sender_email, self.sender_password)
            #     server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    async def send_trending_alert(
        self,
        to_email: str,
        repos: List[Dict],
        unsubscribe_url: str
    ) -> bool:
        """Send daily trending alert."""
        return await self.send_email(
            to_email=to_email,
            subject=f"🔥 {len(repos)} Trending Repositories Today",
            template_name="trending_alert",
            context={
                "repos": repos[:10],  # Top 10
                "view_all_url": "https://repodiscover.ai/trending",
                "unsubscribe_url": unsubscribe_url
            }
        )
    
    async def send_saved_search_match(
        self,
        to_email: str,
        search_name: str,
        matches: List[Dict],
        preferences_url: str
    ) -> bool:
        """Send saved search match notification."""
        return await self.send_email(
            to_email=to_email,
            subject=f"🔍 {len(matches)} New Matches for '{search_name}'",
            template_name="saved_search_match",
            context={
                "search_name": search_name,
                "count": len(matches),
                "matches": matches[:5],  # Top 5
                "view_all_url": "https://repodiscover.ai/searches",
                "preferences_url": preferences_url
            }
        )
    
    async def send_collection_update(
        self,
        to_email: str,
        collection_name: str,
        new_repos: List[Dict],
        collection_url: str
    ) -> bool:
        """Send collection update notification."""
        return await self.send_email(
            to_email=to_email,
            subject=f"📚 '{collection_name}' Updated with {len(new_repos)} Repos",
            template_name="collection_update",
            context={
                "collection_name": collection_name,
                "count": len(new_repos),
                "collection_url": collection_url
            }
        )
    
    async def send_gfi_alert(
        self,
        to_email: str,
        issues: List[Dict],
        languages: List[str]
    ) -> bool:
        """Send good first issue alert."""
        return await self.send_email(
            to_email=to_email,
            subject=f"🎯 {len(issues)} Good First Issues Available",
            template_name="gfi_alert",
            context={
                "count": len(issues),
                "languages": ", ".join(languages),
                "issues": issues[:10]  # Top 10
            }
        )
    
    async def send_welcome(
        self,
        to_email: str,
        dashboard_url: str
    ) -> bool:
        """Send welcome email."""
        return await self.send_email(
            to_email=to_email,
            subject="👋 Welcome to RepoDiscoverAI!",
            template_name="welcome",
            context={
                "dashboard_url": dashboard_url
            }
        )


class NotificationPreferences:
    """User notification preferences."""
    
    def __init__(self, db_path: str = "data/notifications.db"):
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self):
        """Initialize preferences database."""
        import sqlite3
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                trending_alerts BOOLEAN DEFAULT TRUE,
                saved_search_alerts BOOLEAN DEFAULT TRUE,
                collection_alerts BOOLEAN DEFAULT TRUE,
                gfi_alerts BOOLEAN DEFAULT TRUE,
                frequency TEXT DEFAULT 'daily',
                languages TEXT DEFAULT '["Python","JavaScript"]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                topic TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(email, topic)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_preferences(self, email: str) -> Optional[Dict]:
        """Get user preferences."""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM preferences WHERE email = ?",
            (email,)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def set_preferences(self, email: str, **kwargs) -> bool:
        """Set user preferences."""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if exists
        cursor.execute(
            "SELECT id FROM preferences WHERE email = ?",
            (email,)
        )
        exists = cursor.fetchone()
        
        if exists:
            # Update
            fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [email]
            cursor.execute(
                f"UPDATE preferences SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE email = ?",
                values
            )
        else:
            # Insert
            kwargs["email"] = email
            fields = ", ".join(kwargs.keys())
            placeholders = ", ".join(["?" for _ in kwargs])
            values = list(kwargs.values())
            cursor.execute(
                f"INSERT INTO preferences ({fields}) VALUES ({placeholders})",
                values
            )
        
        conn.commit()
        conn.close()
        return True
    
    def subscribe(self, email: str, topic: str) -> bool:
        """Subscribe to a topic."""
        import sqlite3
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT OR IGNORE INTO subscriptions (email, topic) VALUES (?, ?)",
                (email, topic)
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe {email} to {topic}: {e}")
            return False
    
    def unsubscribe(self, email: str, topic: Optional[str] = None) -> bool:
        """Unsubscribe from topic or all."""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if topic:
            cursor.execute(
                "DELETE FROM subscriptions WHERE email = ? AND topic = ?",
                (email, topic)
            )
        else:
            cursor.execute(
                "DELETE FROM subscriptions WHERE email = ?",
                (email,)
            )
        
        conn.commit()
        conn.close()
        return True
    
    def get_subscribers(self, topic: str) -> List[str]:
        """Get all subscribers for a topic."""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT email FROM subscriptions WHERE topic = ?",
            (topic,)
        )
        
        emails = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return emails


# Global notification service instance
_notification_service: Optional[NotificationService] = None
_preferences: Optional[NotificationPreferences] = None


def get_notification_service() -> NotificationService:
    """Get or create notification service."""
    global _notification_service
    
    if _notification_service is None:
        import os
        _notification_service = NotificationService(
            smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            sender_email=os.getenv("SENDER_EMAIL"),
            sender_password=os.getenv("SENDER_PASSWORD")
        )
    
    return _notification_service


def get_preferences() -> NotificationPreferences:
    """Get or create preferences manager."""
    global _preferences
    
    if _preferences is None:
        _preferences = NotificationPreferences()
    
    return _preferences
