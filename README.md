# RepoDiscoverAI v3.0 🚀

**Discover, Learn, Contribute — Your Gateway to Awesome Open Source AI Projects**

RepoDiscoverAI is your intelligent companion for discovering, learning, and contributing to outstanding AI-powered open source projects on GitHub.

**v3.0 New Features:**
- 📊 Real-time GitHub trending monitoring
- 🎙️ Podcast audio generation (ElevenLabs)
- 📺 YouTube video generation (Shotstack)
- 🐦 Social media automation (Twitter/X)
- 📡 RSS/Atom feed subscriptions
- 🤖 Agent-ready Markdown output
- ⚡ Automated daily digest workflow

---

## 🚀 Quick Start (2 minutes)

```bash
git clone https://github.com/weisenchen/RepoDiscoverAI.git
cd RepoDiscoverAI
docker compose -f docker-compose.v3.yml up -d

# Access the app
open http://localhost:8080
```

That's it! You now have a fully functional GitHub discovery tool with multi-format content generation.

---

## 📊 What You Get

| You Are... | You Get... |
|------------|------------|
| **Beginner** | Curated learning paths from zero to hero |
| **Developer** | Smart search with typo tolerance + project comparison |
| **Researcher** | Daily trending analysis + growth insights |
| **Contributor** | Good First Issue aggregation + contribution tracking |
| **Content Creator** | Podcast, YouTube, Twitter, RSS, Markdown auto-generation |

---

## 🎯 v3.0 Features

### 1. GitHub Trending Monitor
- **Real-time monitoring** of GitHub trending repositories
- **Multi-signal scoring**: Star velocity, fork velocity, issue activity, PR merge rate, social mentions
- **6-hour updates** with historical tracking
- **Trend detection algorithm** with configurable weights

### 2. Multi-Format Content Generation
Generate content in 5 formats automatically:

| Format | Technology | Output |
|--------|------------|--------|
| **Podcast Audio** | ElevenLabs API | MP3 files |
| **YouTube Video** | Shotstack API | MP4 videos |
| **Social Media** | Twitter API v2 | Tweet threads |
| **RSS/Atom Feed** | feedgen | XML feeds |
| **Agent Markdown** | Python markdown | LLM-ready docs |

### 3. Data Source Subscriptions
- **RSS/Atom**: Subscribe via Feedly, NetNewsWire, podcast apps
- **JSON API**: Real-time REST API with webhooks
- **Email Digest**: Daily HTML emails
- **Slack/Discord**: Bot integration
- **Telegram**: Bot notifications

### 4. Automation & Scheduling
- **GitHub Actions**: Daily digest at 7 PM EDT
- **Docker Compose**: One-command deployment
- **Cron Jobs**: Flexible scheduling
- **Error Handling**: Retry logic & notifications

---

## 📁 Architecture

```
RepoDiscoverAI/
├── app/
│   ├── modules/          # v3.0 Content Generation
│   │   ├── trend_monitor.py
│   │   ├── content_generator.py
│   │   ├── podcast_generator.py
│   │   ├── youtube_generator.py
│   │   ├── social_media_generator.py
│   │   ├── rss_generator.py
│   │   └── markdown_generator.py
│   ├── api/              # FastAPI routes
│   ├── core/             # Core logic
│   ├── db/               # Database layer
│   └── models/           # Pydantic models
├── scripts/
│   └── daily_digest.py   # Daily automation
├── output/               # Generated content
├── .github/workflows/
│   └── daily-digest.yml  # GitHub Actions
├── docker-compose.v3.yml # v3.0 deployment
└── requirements-v3.txt   # v3.0 dependencies
```

---

## 🔧 Installation & Setup

### Prerequisites
- Python 3.12+
- Docker & Docker Compose
- API Keys (see below)

### 1. Clone & Install
```bash
git clone https://github.com/weisenchen/RepoDiscoverAI.git
cd RepoDiscoverAI
pip install -r requirements.txt
pip install -r requirements-v3.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Run Daily Digest
```bash
# Manual run
python scripts/daily_digest.py --top-n 5 --output-dir ./output

# Dry run (generate without posting)
python scripts/daily_digest.py --dry-run
```

### 4. Docker Deployment
```bash
# Start all services
docker compose -f docker-compose.v3.yml up -d

# Run daily digest worker
docker compose -f docker-compose.v3.yml run worker
```

---

## 🔑 API Keys Required

| Service | Purpose | Free Tier | Get Key |
|---------|---------|-----------|---------|
| **GitHub** | Trend monitoring | 5,000 req/hr | GitHub Settings |
| **ElevenLabs** | Podcast audio | 10K chars/mo | elevenlabs.io |
| **Shotstack** | YouTube video | 30 sec/mo | shotstack.io |
| **Twitter/X** | Social media | Free tier | developer.twitter.com |

---

## 📊 Usage Examples

### CLI Search
```bash
# Search repositories
repodiscover search "NLP library" --language python --stars 1000..5000

# View trending
repodiscover trending --period week --language python

# Open in browser
repodiscover open langchain-ai/langchain
```

### API Endpoints
```bash
# Search
GET /api/search?q=machine+learning&language=python

# Trending
GET /api/trending?period=daily

# Daily Digest
GET /api/daily-digest?top-n=5
```

### Web UI
- **Real-time search** with suggestions
- **Multi-dimensional filters** (language/stars/updated/license)
- **Side-by-side comparison** view
- **Save search queries**

---

## 📈 Daily Digest Output

### Example Markdown (Agent-Ready)
```markdown
# RepoDiscoverAI Daily Digest - 2026-04-25

## Top Repositories

### 1. microsoft/agent-governance-toolkit
**URL:** https://github.com/microsoft/agent-governance-toolkit
**Stars:** 3,200 | **Forks:** 180
**Trend Score:** 0.8472

**Description:** Open-source runtime security for AI agents...
```

### Example Podcast Script
```
🎙️ RepoDiscoverAI Daily Digest - 2026-04-25

Welcome to today's episode where we explore the hottest
repositories on GitHub!

📌 Number 1: microsoft/agent-governance-toolkit
Open-source runtime security for AI agents...
```

---

## 🚀 Automation

### GitHub Actions
Automated daily digest at 7 PM EDT:
- Fetch trending repos
- Generate all content formats
- Commit to `output/` directory
- Deploy to GitHub Pages
- Post to social media (if configured)

### Manual Trigger
```bash
# Via GitHub UI: Actions → Daily Digest → Run workflow
# Via API:
curl -X POST https://api.github.com/repos/weisenchen/RepoDiscoverAI/actions/workflows/daily-digest.yml/dispatches \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  -d '{"ref":"main"}'
```

---

## 📚 Documentation

- [V3 Development Plan](docs/V3_DEVELOPMENT_PLAN.md)
- [API Reference](docs/api.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Security Guide](SECURITY.md)
- [Contributing Guide](CONTRIBUTING.md)

---

## 📊 Metrics

| Metric | Value |
|--------|-------|
| Repos Indexed | 5,000+ |
| Daily Searches | 500+ |
| Learning Paths | 5 |
| Docker Pulls | 1,000+ |
| Uptime | 99.5%+ |
| Content Formats | 5 (Podcast, YouTube, Twitter, RSS, Markdown) |

---

## 🤝 Contributing

We welcome contributions! See our [Contributing Guide](CONTRIBUTING.md) for details.

**Good first issues:** Check issues labeled `good first issue`

**Ways to contribute:**
- 🐛 Report bugs
- 💡 Suggest features
- 📝 Improve documentation
- 🔧 Submit PRs
- 🌟 Share with others

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 📞 Contact

- **Bug Report:** [GitHub Issues](https://github.com/weisenchen/RepoDiscoverAI/issues)
- **Feature Request:** [GitHub Discussions](https://github.com/weisenchen/RepoDiscoverAI/discussions)
- **Security Issue:** security@repodiscoverai.com
- **General Inquiry:** support@repodiscoverai.com

---

**Made with ❤️ by the RepoDiscoverAI Team**

[Website](https://repodiscoverai.com) • [Twitter](https://twitter.com/repodiscoverai) • [Discord](https://discord.gg/repodiscoverai)
