# Deployment Guide for RepoDiscoverAI

## Quick Start

```bash
# Clone repository
git clone https://github.com/wei/RepoDiscoverAI.git
cd RepoDiscoverAI

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Start with Docker Compose
docker compose -f docker-compose.prod.yml up -d

# Run migrations
docker compose exec web python scripts/migrate.py migrate

# Verify deployment
curl https://your-domain.com/health
```

---

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 2 CPU cores minimum
- 50GB disk space

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| SECRET_KEY | ✅ | - | Application secret key |
| DATABASE_URL | ✅ | - | PostgreSQL connection string |
| REDIS_URL | ✅ | - | Redis connection string |
| GITHUB_TOKEN | ✅ | - | GitHub API token |
| DOMAIN_NAME | ✅ | - | Your domain name |
| ADMIN_EMAIL | ✅ | - | Admin email for SSL |

### SSL Certificate

```bash
# Automatic setup with Let's Encrypt
./scripts/ssl_setup.sh your-domain.com admin@your-domain.com

# For development (self-signed)
./scripts/ssl_setup.sh localhost
```

---

## Docker Compose Services

| Service | Port | Description |
|---------|------|-------------|
| nginx | 80, 443 | Reverse proxy |
| web | 8000 | FastAPI application (3 replicas) |
| postgres | 5432 | PostgreSQL database |
| redis | 6379 | Redis cache |
| prometheus | 9090 | Metrics collection |
| grafana | 3000 | Monitoring dashboard |
| loki | 3100 | Log aggregation |
| alertmanager | 9093 | Alert management |

---

## Health Checks

```bash
# Full health check
curl https://your-domain.com/health

# Readiness probe
curl https://your-domain.com/ready

# Liveness probe
curl https://your-domain.com/live

# Prometheus metrics
curl https://your-domain.com/metrics
```

---

## Monitoring

### Access Grafana

```
URL: http://localhost:3000
Username: admin
Password: admin (change in production!)
```

### Key Dashboards

- Main Dashboard: Service health, requests, latency
- Database Dashboard: Connections, queries, replication
- System Dashboard: CPU, memory, disk usage

### Alert Channels

- Email: Configure in `monitoring/alertmanager.yml`
- Slack: Add webhook URL to alertmanager config
- PagerDuty: Add service key for critical alerts

---

## Backup & Restore

### Manual Backup

```bash
# Database backup
docker compose exec postgres pg_dump -U repodiscover repodiscover | gzip > backup.sql.gz

# Verify backup
gunzip -c backup.sql.gz | head -20
```

### Automated Backups

Backups run daily at 2 AM via the `backup` service.

```bash
# List backups
ls -lh backups/

# Restore from backup
gunzip -c backups/repodiscover_20260311_020000.sql.gz | \
  docker compose exec -T postgres psql -U repodiscover -d repodiscover
```

### Backup Retention

- Default: 30 days
- Configure: `RETENTION_DAYS` in `.env`

---

## Scaling

### Horizontal Scaling

```yaml
# In docker-compose.prod.yml
deploy:
  replicas: 5  # Increase web replicas
  resources:
    limits:
      cpus: '1.0'  # Increase CPU limit
      memory: 1G   # Increase memory limit
```

### Vertical Scaling

```bash
# Increase PostgreSQL resources
docker compose up -d --scale postgres=1

# Increase Redis memory
# Edit docker-compose.prod.yml: command: redis-server --maxmemory 1gb
```

---

## Troubleshooting

### Check Service Status

```bash
# All services
docker compose ps

# Specific service
docker compose ps web

# View logs
docker compose logs -f web
docker compose logs -f nginx
docker compose logs -f postgres
```

### Common Issues

#### Service Won't Start

```bash
# Check logs
docker compose logs web

# Verify environment
docker compose config

# Restart service
docker compose restart web
```

#### Database Connection Failed

```bash
# Check PostgreSQL status
docker compose exec postgres pg_isready

# Verify connection string
docker compose exec web env | grep DATABASE_URL

# Test connection
docker compose exec web python -c "import asyncpg; asyncio.run(asyncpg.connect('your-url'))"
```

#### High Memory Usage

```bash
# Check container stats
docker stats

# Restart high-memory containers
docker compose restart web

# Scale down if needed
docker compose up -d --scale web=2
```

---

## Update Procedure

```bash
# 1. Pull latest image
docker compose pull

# 2. Run migrations
docker compose run --rm web python scripts/migrate.py migrate

# 3. Rolling update
docker compose up -d --force-recreate web

# 4. Verify health
curl https://your-domain.com/health

# 5. Rollback if needed
docker compose rollback
```

---

## Production Checklist

- [ ] SSL certificate valid
- [ ] Secrets rotated from defaults
- [ ] Firewall rules configured
- [ ] Monitoring active
- [ ] Backups verified
- [ ] Rate limiting enabled
- [ ] Error alerts configured
- [ ] Documentation updated

---

**Last Updated**: 2026-03-11  
**Version**: 1.0
