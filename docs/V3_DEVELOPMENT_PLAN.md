# RepoDiscoverAI v3.0: 完整开发计划

**版本：** 3.0.0  
**创建日期：** 2026-04-25  
**目标：** 打造多格式内容生成引擎，实时监控 GitHub 前沿技术趋势，实现自动化分发  
**状态：** 核心模块开发中，基础设施就绪

---

## 🎯 1. 项目愿景与目标

### 核心使命
将 RepoDiscoverAI 从“仓库发现工具”升级为“AI 驱动的多格式内容引擎”，实现：
- **第一手技术挖掘：** 实时监控 GitHub Trending、Reddit、Hacker News、Polymarket
- **多格式输出：** Podcast 音频、YouTube 视频、Twitter 推文、RSS/Atom 订阅、Agent 专用 Markdown
- **全自动化工作流：** 每日定时抓取 → AI 分析 → 内容生成 → 多平台分发

### 关键指标 (KPIs)
| 指标 | 3 个月目标 | 6 个月目标 |
|------|-----------|-----------|
| GitHub Stars | 1,000+ | 5,000+ |
| Podcast 订阅 | 100+ | 500+ |
| YouTube 订阅 | 500+ | 2,000+ |
| Twitter 粉丝 | 200+ | 1,000+ |
| RSS 订阅 | 50+ | 200+ |
| 网站月访问 | 10,000+ | 50,000+ |

---

## 🏗️ 2. 系统架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    数据采集层 (Data Collection)               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │GitHub API│  │Trending  │  │Reddit    │  │Hacker    │    │
│  │(实时)    │  │爬虫      │  │API       │  │News API  │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    分析引擎层 (Analysis Engine)               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │趋势检测  │  │评分算法  │  │分类 AI   │  │摘要生成  │    │
│  │TrendDet  │  │Scorer    │  │Categorizer│  │Summarizer│    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    内容生成层 (Content Generation)            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │Podcast   │  │YouTube   │  │Social    │  │RSS/Atom  │    │
│  │(ElevenLabs)│ │(Shotstack)│ │(Twitter) │  │(feedgen) │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│  ┌──────────┐                                                │
│  │Agent     │                                                │
│  │Markdown  │                                                │
│  └──────────┘                                                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    分发层 (Distribution)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │GitHub    │  │YouTube   │  │Twitter/  │  │Podcast   │    │
│  │Pages     │  │API       │  │X API     │  │Platforms │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📅 3. 分阶段实施路线图

### Phase 1: 基础与监控 (Week 1-2) ✅ 已完成
- [x] GitHub Trending 监控器 (`trend_monitor.py`)
- [x] 趋势评分算法 (Star Velocity, Fork Velocity, Issue Activity, PR Merge Rate, Social Mentions)
- [x] 数据采集管道 (GitHub API, Web Scraping)
- [x] 数据库初始化 (SQLite + DuckDB)
- [x] 核心 API 接口 (`/api/trending`, `/api/search`)

### Phase 2: 内容生成引擎 (Week 3-4) ✅ 已完成
- [x] 内容生成编排器 (`content_generator.py`)
- [x] Podcast 音频生成 (`podcast_generator.py` → ElevenLabs)
- [x] YouTube 视频生成 (`youtube_generator.py` → Shotstack)
- [x] 社交媒体推文 (`social_media_generator.py` → Twitter API v2)
- [x] RSS/Atom 订阅源 (`rss_generator.py` → feedgen)
- [x] Agent 专用 Markdown (`markdown_generator.py` → LLM 优化)
- [x] 每日摘要脚本 (`scripts/daily_digest.py`)

### Phase 3: 自动化与部署 (Week 5-6) 🔄 进行中
- [ ] GitHub Actions 工作流配置 (需手动添加 `workflow` 权限)
- [ ] Docker Compose v3 部署验证
- [ ] 环境变量与密钥管理 (`.env` 模板)
- [ ] 错误处理与重试机制
- [ ] 日志监控与告警 (Prometheus + Grafana)

### Phase 4: 测试与优化 (Week 7-8)
- [ ] 单元测试覆盖 (`tests/test_trend_monitor.py`, `tests/test_generators.py`)
- [ ] 集成测试 (端到端内容生成流程)
- [ ] 性能优化 (并发抓取, 缓存策略)
- [ ] 内容质量评估 (人工审核 + AI 评分)
- [ ] 成本优化 (API 调用频率控制)

### Phase 5: 扩展与社区 (Week 9-12)
- [ ] 多语言支持 (中文、日语、西班牙语)
- [ ] Webhook 集成 (Slack, Discord, Telegram)
- [ ] 高级分析仪表板
- [ ] 社区贡献系统
- [ ] 企业版功能 (SSO, RBAC, 私有部署)

---

## 🛠️ 4. 核心技术栈

| 类别 | 技术 | 用途 |
|------|------|------|
| **后端** | Python 3.12+, FastAPI | API 服务, 异步处理 |
| **前端** | HTMX, Alpine.js | 轻量 Web UI |
| **数据库** | SQLite, DuckDB | 本地存储, 分析查询 |
| **搜索** | Meilisearch | 模糊搜索, 拼写容错 |
| **缓存** | Redis (可选) | 高性能缓存 |
| **内容生成** | ElevenLabs, Shotstack, feedgen, tweepy | 多格式输出 |
| **自动化** | GitHub Actions, Docker Compose, APScheduler | 定时任务, 部署 |
| **监控** | Prometheus, Grafana, structlog | 指标采集, 日志 |

---

## 📊 5. 数据源与监控策略

### 数据源配置
| 源 | 频率 | 端点/方法 | 数据点 |
|----|------|-----------|--------|
| GitHub Trending | 每 6 小时 | Web Scraping | Top 25 repos/day |
| GitHub API | 每 1 小时 | REST API | Stars, forks, issues, PRs |
| Reddit | 每 4 小时 | Reddit API | r/programming, r/MachineLearning |
| Hacker News | 每 2 小时 | HN API | Front page, technology |
| Polymarket | 每日 | API | Prediction markets |

### 趋势评分算法
```python
Trend Score = (Star Velocity × 0.3) + 
             (Fork Velocity × 0.2) + 
             (Issue Activity × 0.15) + 
             (PR Merge Rate × 0.15) + 
             (Social Mentions × 0.2)
```

---

## 📝 6. 多格式内容生成工作流

### 6.1 Podcast 音频
- **输入：** Top 5 趋势仓库
- **处理：** 生成脚本 → ElevenLabs 语音合成 → 添加片头片尾
- **输出：** MP3 文件 (3-5 分钟)
- **分发：** RSS 订阅 + 播客平台 (Spotify, Apple Podcasts)

### 6.2 YouTube 视频
- **输入：** Top 5 趋势仓库
- **处理：** 生成脚本 → ElevenLabs 配音 → Shotstack 视频渲染 → 自动生成缩略图
- **输出：** MP4 视频 (HD, 2-4 分钟)
- **分发：** YouTube API 自动上传

### 6.3 社交媒体推文
- **输入：** Top 5 趋势仓库
- **处理：** 生成推文线程 (Hook + 5 条详情 + CTA)
- **输出：** 7 条推文
- **分发：** Twitter API v2 自动发布

### 6.4 RSS/Atom 订阅
- **输入：** Top 5 趋势仓库
- **处理：** feedgen 生成 XML
- **输出：** `feed.xml`, `feed.atom`
- **分发：** GitHub Pages 托管 + Feedly 订阅

### 6.5 Agent 专用 Markdown
- **输入：** Top 5 趋势仓库
- **处理：** 结构化 Markdown 生成 (URL, Stars, Forks, Description, Trend Score)
- **输出：** `repodiscover-daily-YYYY-MM-DD.md`
- **分发：** GitHub Pages + JSON API + Webhook

---

## 📡 7. 分发与订阅渠道

| 渠道 | 格式 | 更新频率 | 订阅方式 |
|------|------|----------|----------|
| **GitHub Pages** | Markdown, JSON, XML | 每日 19:00 EDT | 访问 `repodiscoverai.com` |
| **YouTube** | MP4 视频 | 每日 19:00 EDT | 订阅频道 |
| **Twitter/X** | 推文线程 | 每日 19:00 EDT | 关注 `@RepoDiscoverAI` |
| **Podcast** | MP3 音频 | 每日 19:00 EDT | RSS / Apple Podcasts / Spotify |
| **RSS/Atom** | XML | 每 6 小时 | Feedly, NetNewsWire |
| **JSON API** | JSON | 实时 | REST API + Webhooks |
| **Email** | HTML | 每日 19:00 EDT | 邮件订阅 (Newsletter) |
| **Slack/Discord** | Markdown | 每日 19:00 EDT | Bot / Webhook |
| **Telegram** | Markdown | 每日 19:00 EDT | Bot 通知 |

---

## 🔒 8. 安全与合规

### API 密钥管理
- 所有密钥存储在 `.env` 文件中，不提交到 Git
- 使用 GitHub Secrets 管理 CI/CD 密钥
- 定期轮换密钥 (每 90 天)

### 数据隐私
- 不收集用户 PII (个人身份信息)
- 所有数据本地优先 (Local-first)
- GDPR 合规 (支持数据导出/删除)

### 内容合规
- 遵守各平台 API 使用条款
- 自动标记 AI 生成内容
- 尊重开源许可证 (MIT, Apache 2.0, GPL 等)

---

## 🧪 9. 测试与质量保证

### 测试策略
| 类型 | 工具 | 覆盖率目标 |
|------|------|-----------|
| 单元测试 | pytest | 80%+ |
| 集成测试 | pytest + httpx | 核心流程 100% |
| 端到端测试 | Playwright | 关键用户路径 |
| 性能测试 | locust | 并发 100+ 请求 |
| 安全扫描 | bandit, safety | 零高危漏洞 |

### 质量门禁
- PR 必须通过 CI 检查
- 代码覆盖率 < 80% 禁止合并
- 安全扫描失败禁止部署
- 手动审核首次 AI 生成内容

---

## 🚀 10. 部署与运维

### 部署选项
| 方式 | 命令 | 适用场景 |
|------|------|----------|
| **Docker Compose** | `docker compose -f docker-compose.v3.yml up -d` | 本地/私有云 |
| **GitHub Actions** | 手动触发或定时 | 自动化每日摘要 |
| **Kubernetes** | `kubectl apply -f k8s/` | 生产环境 |
| **Serverless** | AWS Lambda / Cloudflare Workers | 低成本 API |

### 运维监控
- **健康检查:** `/health` 端点
- **指标:** Prometheus 采集 (请求数, 延迟, 错误率)
- **日志:** structlog 结构化日志 → Loki → Grafana
- **告警:** 失败重试 + Slack/Email 通知

---

## 📅 11. 时间表与里程碑

| 阶段 | 时间 | 交付物 | 状态 |
|------|------|--------|------|
| **Phase 1** | Week 1-2 | 趋势监控器, 评分算法, 核心 API | ✅ 完成 |
| **Phase 2** | Week 3-4 | 多格式生成器, 每日脚本, Docker 配置 | ✅ 完成 |
| **Phase 3** | Week 5-6 | GitHub Actions, 密钥管理, 错误处理 | 🔄 进行中 |
| **Phase 4** | Week 7-8 | 测试套件, 性能优化, 内容审核 | ⏳ 待开始 |
| **Phase 5** | Week 9-12 | 多语言, Webhook, 分析仪表板, 社区功能 | ⏳ 待开始 |
| **v3.0 发布** | Week 12 | 生产部署, 文档完善, 发布公告 | ⏳ 待开始 |

---

## ⚠️ 12. 风险管理

| 风险 | 影响 | 概率 | 缓解策略 |
|------|------|------|----------|
| API 密钥泄露 | 高 | 中 | 使用 GitHub Secrets, 定期轮换, 最小权限原则 |
| API 限流/封禁 | 高 | 中 | 指数退避重试, 多账号备份, 遵守速率限制 |
| 内容质量下降 | 中 | 高 | 人工审核机制, AI 评分过滤, 用户反馈循环 |
| 成本超支 | 中 | 低 | 预算告警, 按需生成, 免费层优先 |
| 平台政策变更 | 高 | 中 | 抽象 API 层, 多平台支持, 快速适配 |
| 法律合规 | 高 | 低 | 明确 AI 生成标签, 遵守版权法, 用户协议 |

---

## 📞 13. 支持与反馈

- **文档:** [README.md](../README.md) | [V3 开发计划](V3_DEVELOPMENT_PLAN.md)
- **问题:** [GitHub Issues](https://github.com/weisenchen/RepoDiscoverAI/issues)
- **讨论:** [GitHub Discussions](https://github.com/weisenchen/RepoDiscoverAI/discussions)
- **安全:** security@repodiscoverai.com
- **邮件:** support@repodiscoverai.com

---

**最后更新:** 2026-04-25  
**作者:** RepoDiscoverAI Team  
**许可:** MIT License
