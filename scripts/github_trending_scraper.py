#!/usr/bin/env python3
"""
GitHub Trending Scraper

Scrapes GitHub Trending page and updates the trending tech category.
Runs daily via cron job.

Usage:
    python github_trending_scraper.py [--language LANG] [--period PERIOD]

Options:
    --language  Filter by language (python, javascript, rust, go, etc.)
    --period    Time period: today, week, month (default: today)
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from pathlib import Path
import json
import argparse
from typing import List, Dict, Optional
import sys

# GitHub Trending URL
GITHUB_TRENDING_URL = "https://github.com/trending"

# Output paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
TRENDING_DIR = PROJECT_ROOT / "github_trending_tech"
ARCHIVE_DIR = TRENDING_DIR / "archive"
DATA_DIR = PROJECT_ROOT / "data"

# Ensure directories exist
TRENDING_DIR.mkdir(exist_ok=True)
ARCHIVE_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)


class GitHubTrendingScraper:
    """Scraper for GitHub Trending repositories."""
    
    def __init__(self, language: Optional[str] = None, period: str = "today"):
        self.language = language
        self.period = period
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
    
    def fetch_trending(self) -> str:
        """Fetch the GitHub Trending page."""
        url = GITHUB_TRENDING_URL
        params = {}
        
        if self.language:
            params['language'] = self.language
        if self.period:
            params['since'] = self.period
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching trending page: {e}")
            sys.exit(1)
    
    def parse_repos(self, html: str) -> List[Dict]:
        """Parse repository information from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        repos = []
        
        # Find all repository articles
        articles = soup.find_all('article', class_='Box-row')
        
        for article in articles:
            try:
                # Repository name and link
                name_elem = article.find('h2', class_='h3 lh-condensed')
                if not name_elem:
                    continue
                
                link = name_elem.find('a')
                if not link:
                    continue
                
                full_name = link['href'].strip('/')
                name_parts = full_name.split('/')
                owner = name_parts[0] if len(name_parts) > 0 else ''
                repo_name = name_parts[1] if len(name_parts) > 1 else ''
                
                # Description
                desc_elem = article.find('p', class_='col-9 color-fg-muted my-1 pr-4')
                description = desc_elem.get_text(strip=True) if desc_elem else ''
                
                # Language
                lang_elem = article.find('span', itemprop='programmingLanguage')
                language = lang_elem.get_text(strip=True) if lang_elem else 'Unknown'
                
                # Stars
                star_elem = article.find('a', href=lambda x: x and '/stargazers' in x if x else False)
                stars_text = star_elem.get_text(strip=True) if star_elem else '0'
                stars = self._parse_number(stars_text)
                
                # Forks
                fork_elem = article.find('a', href=lambda x: x and '/forks' in x if x else False)
                forks_text = fork_elem.get_text(strip=True) if fork_elem else '0'
                forks = self._parse_number(forks_text)
                
                # Build repo data
                repo_data = {
                    'full_name': full_name,
                    'owner': owner,
                    'name': repo_name,
                    'description': description,
                    'language': language,
                    'stars': stars,
                    'forks': forks,
                    'url': f'https://github.com/{full_name}',
                    'scraped_at': datetime.now().isoformat(),
                    'period': self.period,
                }
                
                repos.append(repo_data)
                
            except Exception as e:
                print(f"Error parsing repo: {e}")
                continue
        
        return repos
    
    def _parse_number(self, text: str) -> int:
        """Parse number from text (handles k, M suffixes)."""
        text = text.strip().replace(',', '')
        
        if 'k' in text.lower():
            return int(float(text.lower().replace('k', '')) * 1000)
        elif 'm' in text.lower():
            return int(float(text.lower().replace('m', '')) * 1000000)
        else:
            try:
                return int(text)
            except ValueError:
                return 0
    
    def save_data(self, repos: List[Dict]):
        """Save scraped data to JSON file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'trending_{self.language or "all"}_{self.period}_{timestamp}.json'
        filepath = DATA_DIR / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'scraped_at': datetime.now().isoformat(),
                'language': self.language or 'all',
                'period': self.period,
                'count': len(repos),
                'repos': repos
            }, f, indent=2, ensure_ascii=False)
        
        # Also save as latest
        latest_path = DATA_DIR / f'latest_{self.language or "all"}_{self.period}.json'
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump({
                'scraped_at': datetime.now().isoformat(),
                'language': self.language or 'all',
                'period': self.period,
                'count': len(repos),
                'repos': repos
            }, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(repos)} repos to {filepath}")
        return filepath
    
    def update_readme(self, repos: List[Dict]):
        """Update the trending README with latest data."""
        readme_path = TRENDING_DIR / 'README.md'
        
        if not readme_path.exists():
            print(f"README not found at {readme_path}")
            return
        
        # Generate markdown table
        table_rows = []
        for repo in repos[:10]:  # Top 10
            row = f"| [{repo['name']}](<{repo['url']}>) | {repo['stars']:,} | {repo['forks']:,} | {repo['language']} | {repo['description'][:80]}... |"
            table_rows.append(row)
        
        table_content = '\n'.join(table_rows)
        
        # Read current README
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace the table section
        import re
        pattern = r'(\|\s*Repo\s*\|\s*Stars\s*\|\s*Forks\s*\|.*?\n)((?:\|.*\|\n)+)'
        replacement = f'\\1{table_content}\n\n'
        
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # Update last updated date
        today = datetime.now().strftime('%Y-%m-%d')
        new_content = re.sub(
            r'\*\*Last Updated:\*\* \d{4}-\d{2}-\d{2}',
            f'**Last Updated:** {today}',
            new_content
        )
        
        # Write updated README
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"Updated README at {readme_path}")
    
    def save_weekly_archive(self, repos: List[Dict]):
        """Save weekly summary to archive."""
        today = datetime.now()
        week_num = today.isocalendar()[1]
        year = today.year
        archive_file = ARCHIVE_DIR / f'{year}-W{week_num:02d}.md'
        
        content = f"""# Weekly Trending Archive - {year} Week {week_num:02d}

**Period:** {today.strftime('%Y-%m-%d')}  
**Generated:** {datetime.now().isoformat()}

## Top 10 Repositories

| Rank | Repository | Stars | Forks | Language | Description |
|------|------------|-------|-------|----------|-------------|
"""
        
        for i, repo in enumerate(repos[:10], 1):
            content += f"| {i} | [{repo['name']}](<{repo['url']}>) | {repo['stars']:,} | {repo['forks']:,} | {repo['language']} | {repo['description'][:60]}... |\n"
        
        content += f"""
## Language Distribution

"""
        
        # Count by language
        lang_counts = {}
        for repo in repos:
            lang = repo['language']
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
        
        for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1])[:5]:
            content += f"- **{lang}**: {count} repos\n"
        
        with open(archive_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Saved weekly archive to {archive_file}")
    
    def run(self, update_readme: bool = True):
        """Run the full scraping pipeline."""
        print(f"Scraping GitHub Trending (language={self.language}, period={self.period})...")
        
        # Fetch and parse
        html = self.fetch_trending()
        repos = self.parse_repos(html)
        
        print(f"Found {len(repos)} trending repositories")
        
        # Save data
        self.save_data(repos)
        
        # Update README
        if update_readme:
            self.update_readme(repos)
        
        # Save weekly archive (if running on Monday)
        if datetime.now().weekday() == 0:  # Monday
            self.save_weekly_archive(repos)
        
        return repos


def main():
    parser = argparse.ArgumentParser(description='GitHub Trending Scraper')
    parser.add_argument('--language', '-l', type=str, default=None,
                       help='Filter by language (python, javascript, rust, go, etc.)')
    parser.add_argument('--period', '-p', type=str, default='today',
                       choices=['today', 'week', 'month'],
                       help='Time period (default: today)')
    parser.add_argument('--no-update', action='store_true',
                       help='Do not update README')
    
    args = parser.parse_args()
    
    scraper = GitHubTrendingScraper(
        language=args.language,
        period=args.period
    )
    
    scraper.run(update_readme=not args.no_update)


if __name__ == '__main__':
    main()
