#!/usr/bin/env python3
"""
SEO Generator

Generate sitemap.xml and optimize meta tags for better search engine visibility.
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SEOGptimizer:
    """SEO optimization utilities."""
    
    def __init__(self, base_url: str = "https://repodiscover.ai"):
        self.base_url = base_url
        self.frontend_dir = Path(__file__).parent.parent / "frontend"
        self.data_dir = Path(__file__).parent.parent / "data"
    
    def generate_sitemap(self, repos: list = None) -> str:
        """Generate sitemap.xml."""
        urlset = ET.Element("urlset")
        urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
        
        # Static pages
        static_pages = [
            ("/", "1.0", "daily"),
            ("/trending", "0.9", "daily"),
            ("/search", "0.9", "daily"),
            ("/collections", "0.8", "weekly"),
            ("/learning-paths", "0.8", "weekly"),
            ("/about", "0.5", "monthly"),
        ]
        
        for path, priority, changefreq in static_pages:
            url = ET.SubElement(urlset, "url")
            loc = ET.SubElement(url, "loc")
            loc.text = f"{self.base_url}{path}"
            
            lastmod = ET.SubElement(url, "lastmod")
            lastmod.text = datetime.now().strftime("%Y-%m-%d")
            
            priority_elem = ET.SubElement(url, "priority")
            priority_elem.text = priority
            
            changefreq_elem = ET.SubElement(url, "changefreq")
            changefreq_elem.text = changefreq
        
        # Repository pages (if repos provided)
        if repos:
            for repo in repos[:1000]:  # Limit to 1000 for sitemap
                url = ET.SubElement(urlset, "url")
                loc = ET.SubElement(url, "loc")
                loc.text = f"{self.base_url}/repo/{repo['id']}"
                
                lastmod = ET.SubElement(url, "lastmod")
                lastmod.text = repo.get('updated_at', datetime.now().strftime("%Y-%m-%d"))[:10]
                
                priority_elem = ET.SubElement(url, "priority")
                priority_elem.text = "0.7"
                
                changefreq_elem = ET.SubElement(url, "changefreq")
                changefreq_elem.text = "weekly"
        
        # Pretty print
        xml_str = ET.tostring(urlset, encoding='unicode')
        
        # Add XML declaration
        sitemap = f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'
        
        return sitemap
    
    def generate_robots_txt(self) -> str:
        """Generate robots.txt."""
        return f"""# RepoDiscoverAI Robots.txt
User-agent: *
Allow: /

# Disallow admin/api endpoints
Disallow: /api/
Disallow: /admin/
Disallow: /docs
Disallow: /redoc

# Sitemap
Sitemap: {self.base_url}/sitemap.xml

# Crawl-delay (optional)
Crawl-delay: 1
"""
    
    def generate_structured_data(self, repo: dict = None) -> dict:
        """Generate JSON-LD structured data."""
        if repo:
            return {
                "@context": "https://schema.org",
                "@type": "SoftwareSourceCode",
                "name": repo.get('full_name', ''),
                "description": repo.get('description', ''),
                "url": repo.get('html_url', ''),
                "programmingLanguage": repo.get('language', ''),
                "applicationCategory": "DeveloperApplication",
                "aggregateRating": {
                    "@type": "AggregateRating",
                    "ratingValue": str(repo.get('score', 4.5)),
                    "ratingCount": repo.get('stargazers_count', 0)
                },
                "interactionStatistic": {
                    "@type": "InteractionCounter",
                    "interactionType": "https://schema.org/FollowAction",
                    "userInteractionCount": repo.get('stargazers_count', 0)
                }
            }
        else:
            # Organization data
            return {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "RepoDiscoverAI",
                "url": self.base_url,
                "logo": f"{self.base_url}/static/logo.png",
                "description": "Discover awesome GitHub repositories with intelligent search, trend analysis, and curated learning paths.",
                "sameAs": [
                    "https://github.com/weisenchen/RepoDiscoverAI",
                    "https://twitter.com/repodiscoverai"
                ]
            }
    
    def update_meta_tags(self, html_file: Path, title: str = None, description: str = None):
        """Update meta tags in HTML file."""
        if not html_file.exists():
            logger.warning(f"File not found: {html_file}")
            return
        
        content = html_file.read_text()
        
        # Default values
        if title is None:
            title = "RepoDiscoverAI - Discover Awesome GitHub Repositories"
        if description is None:
            description = "Discover awesome GitHub repositories with intelligent search, trend analysis, and curated learning paths. Find 5000+ curated AI projects."
        
        # Meta tags to add
        meta_tags = f"""
    <!-- SEO Meta Tags -->
    <meta name="title" content="{title}">
    <meta name="description" content="{description}">
    <meta name="keywords" content="github, repositories, awesome, AI, machine-learning, deep-learning, open-source, discover">
    <meta name="author" content="RepoDiscoverAI Team">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="{self.base_url}/">
    
    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="{self.base_url}/">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:image" content="{self.base_url}/static/og-image.png">
    
    <!-- Twitter -->
    <meta property="twitter:card" content="summary_large_image">
    <meta property="twitter:url" content="{self.base_url}/">
    <meta property="twitter:title" content="{title}">
    <meta property="twitter:description" content="{description}">
    <meta property="twitter:image" content="{self.base_url}/static/og-image.png">
    
    <!-- Favicon -->
    <link rel="icon" type="image/png" sizes="32x32" href="/static/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/static/favicon-16x16.png">
    <link rel="apple-touch-icon" href="/static/apple-touch-icon.png">
"""
        
        # Check if SEO tags already exist
        if '<!-- SEO Meta Tags -->' in content:
            logger.info(f"SEO tags already exist in {html_file}")
            return
        
        # Insert after <head> tag
        content = content.replace('<head>', f'<head>\n{meta_tags}')
        
        html_file.write_text(content)
        logger.info(f"Updated meta tags in {html_file}")
    
    def run(self):
        """Run all SEO optimizations."""
        logger.info("🔍 Starting SEO optimization...")
        
        # Generate sitemap
        sitemap = self.generate_sitemap()
        sitemap_path = self.frontend_dir / "sitemap.xml"
        sitemap_path.write_text(sitemap)
        logger.info(f"✅ Generated sitemap: {sitemap_path}")
        
        # Generate robots.txt
        robots = self.generate_robots_txt()
        robots_path = self.frontend_dir / "robots.txt"
        robots_path.write_text(robots)
        logger.info(f"✅ Generated robots.txt: {robots_path}")
        
        # Update meta tags
        index_html = self.frontend_dir / "index.html"
        self.update_meta_tags(index_html)
        
        # Generate structured data
        org_schema = self.generate_structured_data()
        schema_path = self.frontend_dir / "static" / "schema.json"
        schema_path.parent.mkdir(parents=True, exist_ok=True)
        schema_path.write_text(json.dumps(org_schema, indent=2))
        logger.info(f"✅ Generated structured data: {schema_path}")
        
        logger.info("🎉 SEO optimization complete!")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="SEO Generator for RepoDiscoverAI")
    parser.add_argument(
        "--base-url",
        default="https://repodiscover.ai",
        help="Base URL for the site"
    )
    
    args = parser.parse_args()
    
    optimizer = SEOGptimizer(base_url=args.base_url)
    optimizer.run()


if __name__ == "__main__":
    main()
