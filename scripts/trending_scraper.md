# GitHub Trending Scraper Documentation

## Overview

The GitHub Trending Scraper automatically monitors [GitHub Trending](https://github.com/trending) to identify emerging repositories and technology trends. This helps users discover cutting-edge tools before they go mainstream.

## Features

- ✅ **Daily Scraping** - Automatically fetches trending repos every day
- ✅ **Multi-Language Support** - Can filter by programming language
- ✅ **Period Options** - Supports today/week/month trending
- ✅ **Data Persistence** - Saves JSON snapshots for historical analysis
- ✅ **README Auto-Update** - Keeps the trending page current
- ✅ **Weekly Archives** - Creates weekly summary reports

## Installation

### Requirements

```bash
cd /path/to/RepoDiscoverAI
pip install -r scripts/requirements.txt
```

### Dependencies

- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing
- `python-dateutil` - Date utilities

## Usage

### Basic Usage

```bash
# Scrape all languages, today's trending
python scripts/github_trending_scraper.py

# Scrape Python repos only
python scripts/github_trending_scraper.py --language python

# Scrape weekly trending
python scripts/github_trending_scraper.py --period week

# Scrape monthly trending for JavaScript
python scripts/github_trending_scraper.py --language javascript --period month

# Scrape without updating README
python scripts/github_trending_scraper.py --no-update
```

### Command Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--language` | `-l` | Filter by language | all |
| `--period` | `-p` | Time period (today/week/month) | today |
| `--no-update` | - | Don't update README | false |

## Automation

### Cron Job Setup

The scraper is designed to run daily via cron. Here's the recommended setup:

```bash
# Edit crontab
crontab -e

# Add these lines:

# Daily scrape at 6:00 AM EST (all languages)
0 10 * * * cd /path/to/RepoDiscoverAI && /usr/bin/python3 scripts/github_trending_scraper.py >> logs/trending_daily.log 2>&1

# Weekly scrape on Monday 9:00 AM EST
0 13 * * 1 cd /path/to/RepoDiscoverAI && /usr/bin/python3 scripts/github_trending_scraper.py --period week >> logs/trending_weekly.log 2>&1

# Monthly scrape on 1st of each month at 10:00 AM EST
0 14 1 * * cd /path/to/RepoDiscoverAI && /usr/bin/python3 scripts/github_trending_scraper.py --period month >> logs/trending_monthly.log 2>&1
```

### Systemd Timer (Alternative)

For systems using systemd:

```ini
# /etc/systemd/system/github-trending.service
[Unit]
Description=GitHub Trending Scraper
After=network.target

[Service]
Type=oneshot
User=wei
WorkingDirectory=/home/wei/.openclaw/workspace/RepoDiscoverAI
ExecStart=/usr/bin/python3 /home/wei/.openclaw/workspace/RepoDiscoverAI/scripts/github_trending_scraper.py
StandardOutput=append:/var/log/github-trending.log
StandardError=append:/var/log/github-trending.log
```

```ini
# /etc/systemd/system/github-trending.timer
[Unit]
Description=Run GitHub Trending Scraper Daily
Requires=github-trending.service

[Timer]
OnCalendar=*-*-* 10:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
# Enable and start
sudo systemctl enable github-trending.timer
sudo systemctl start github-trending.timer
```

## Output Files

### Data Directory (`data/`)

| File | Description |
|------|-------------|
| `latest_all_today.json` | Most recent daily scrape |
| `latest_all_week.json` | Most recent weekly scrape |
| `latest_all_month.json` | Most recent monthly scrape |
| `trending_all_today_YYYYMMDD_HHMMSS.json` | Historical snapshots |

### Archive Directory (`github_trending_tech/archive/`)

| File | Description |
|------|-------------|
| `2026-W09.md` | Weekly summary for week 9 of 2026 |

### Updated Files

| File | Update Frequency |
|------|------------------|
| `github_trending_tech/README.md` | Daily |
| `github_trending_tech/archive/YYYY-Www.md` | Weekly (Mondays) |

## Data Schema

### Repository Object

```json
{
  "full_name": "owner/repo",
  "owner": "owner",
  "name": "repo",
  "description": "Repository description",
  "language": "Python",
  "stars": 1234,
  "forks": 567,
  "url": "https://github.com/owner/repo",
  "scraped_at": "2026-03-01T00:00:00",
  "period": "today"
}
```

### Data File Structure

```json
{
  "scraped_at": "2026-03-01T00:00:00",
  "language": "all",
  "period": "today",
  "count": 25,
  "repos": [...]
}
```

## Error Handling

The scraper handles common errors:

- **Network errors** - Retries with exponential backoff
- **Parse errors** - Logs and continues with next repo
- **GitHub rate limits** - Respects rate limits, exits gracefully

### Logs

Check `logs/trending_*.log` for execution logs.

## Best Practices

1. **Run during off-peak hours** - Avoid GitHub API rate limits
2. **Monitor disk space** - Historical data accumulates over time
3. **Review before commit** - Auto-generated content should be reviewed
4. **Backup data** - Keep backups of historical trending data

## Troubleshooting

### Common Issues

**Issue:** "Error fetching trending page"
- **Solution:** Check network connection, GitHub may be temporarily unavailable

**Issue:** "No repos found"
- **Solution:** GitHub may have changed HTML structure, update parser

**Issue:** "Permission denied"
- **Solution:** Ensure write permissions to data/ and github_trending_tech/ directories

## Future Enhancements

- [ ] GitHub API integration for additional metadata
- [ ] Trend analysis (star growth over time)
- [ ] Email/Slack notifications for hot repos
- [ ] Web dashboard for browsing trends
- [ ] Machine learning for trend prediction

## Contributing

Found a bug or want to suggest improvements? Please open an issue or submit a PR!

---

**Maintainer:** RepoDiscoverAI Team  
**Last Updated:** 2026-03-01
