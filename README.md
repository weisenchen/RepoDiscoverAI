# RepoDiscoverAI

A curated list of top-rated AI-powered application repositories on GitHub, focused on discovering projects that are above 2000 stars.

## About

RepoDiscoverAI is a project dedicated to aggregating and categorizing outstanding open-source AI applications on GitHub. Aimed at learners, researchers, and developers, this project helps you find valuable, high-quality applications. This will help explore practical implementations of artificial intelligence.

## How to Use

Browse the directories below to find repositories related to specific AI application areas. Each repository includes a brief description, key technologies, example use cases, star count, fork count, and why it's valuable for learning. The star and fork count are as of the date the repository was added to this list.

## Categories

### 📈 Trending Now (Auto-Updated)

- **[GitHub Trending Tech](./github_trending_tech/)** - *Daily updated* cutting-edge repos gaining rapid traction. Filter by language and time period.

### 🏆 Established Projects (2000+ Stars)

- **[AI-Driven Web Apps](./ai_driven_web_apps/)** - Web applications powered by AI
- **[AI-Powered Mobile Apps](./ai_powered_mobile_apps/)** - Mobile applications with AI features
- **[AI-Enhanced Productivity Tools](./ai_enhanced_productivity_tools/)** - Tools to boost productivity with AI
- **[AI for Creative Content Generation](./)** - Coming soon
- **[AI in Business Automation](./)** - Coming soon
- **[AI in Healthcare and Wellness](./)** - Coming soon

---

## 🤖 Automation

### GitHub Trending Scraper

This project includes an automated scraper that monitors [GitHub Trending](https://github.com/trending) daily to identify emerging technologies and hot repositories.

**Features:**
- ✅ Daily scraping at 6:00 AM EST
- ✅ Multi-language support (Python, JavaScript, Rust, Go, etc.)
- ✅ Period filters (today/week/month)
- ✅ Automatic README updates
- ✅ Weekly archive generation

**Quick Start:**
```bash
# Install dependencies
pip install -r scripts/requirements.txt

# Run manual scrape
python scripts/github_trending_scraper.py

# Set up automated scraping (cron)
crontab scripts/cron_jobs.example
```

**Documentation:** [scripts/trending_scraper.md](./scripts/trending_scraper.md)

---

## Contribution Guidelines

See [CONTRIBUTING.md](CONTRIBUTING.md) for information on how to contribute to this project.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.
