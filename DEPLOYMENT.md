# RepoDiscoverAI - Deployment Guide

**Version:** 5.0  
**Last Updated:** 2026-03-11  
**Status:** Production Ready

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Production Deployment](#production-deployment)
4. [Configuration](#configuration)
5. [SSL/TLS Setup](#ssltls-setup)
6. [Monitoring](#monitoring)
7. [Backup & Recovery](#backup--recovery)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Storage | 20 GB | 50+ GB SSD |
| Network | 100 Mbps | 1 Gbps |

### Software Requirements

- Docker 20.10+
- Docker Compose 2.0+
- Git
- Python 3.11+ (for local development)

### Required Ports

| Port | Service | Description |
|------|---------|-------------|
| 80 | Nginx | HTTP (redirects to HTTPS) |
| 443 | Nginx | HTTPS |
| 3000 | Grafana | Monitoring dashboard |
| 9090 | Prometheus | Metrics |
| 3100 | Loki | Logs |
| 5432 | PostgreSQL | Database (internal) |
| 6379 | Redis | Cache (internal) |

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/your-org/repodiscoverai.git
cd repodiscoverai
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Generate secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Edit .env with your settings
nano .env
```

### 3. Start Services

```bash
# Start all services
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f
```

### 4. Run Database Migrations

```bash
docker compose -f docker-compose.prod.yml exec web python scripts/migrate.py migrate
```

### 5. Verify Deployment

```bash
# Health check
curl http://localhost/health

# Should return: {"status": "healthy", ...}
```

---

## Production Deployment

### Step 1: Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
```

### Step 2: Clone and Configure

```bash
# Clone repository
git clone https://github.com/your-org/repodiscoverai.git /opt/repodiscoverai
cd /opt/repodiscoverai

# Configure environment
cp .env.example .env
nano .env  # Update with production values
```

### Step 3: SSL Certificate

```bash
# For production domain
chmod +x scripts/ssl_setup.sh
./scripts/ssl_setup.sh your-domain.com admin@your-domain.com

# For development (self-signed)
./scripts/ssl_setup.sh localhost
```

### Step 4: Deploy

```bash
# Build and start
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Run migrations
docker compose -f docker-compose.prod.yml exec web python scripts/migrate.py migrate

# Verify
docker compose -f docker-compose.prod.yml ps
```

### Step 5: Configure Firewall

```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow SSH (if not already)
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Application secret key | (required) |
| `DATABASE_URL` | PostgreSQL connection string | (auto-generated) |
| `REDIS_URL` | Redis connection string | (auto-generated) |
| `GITHUB_TOKEN` | GitHub API token | (required for API) |
| `SMTP_HOST` | Email server host | localhost |
| `SMTP_USER` | Email username | - |
| `SMTP_PASSWORD` | Email password | - |
| `RATE_LIMIT_PER_MINUTE` | API rate limit | 100 |
| `GRAFANA_USER` | Grafana admin user | admin |
| `GRAFANA_PASSWORD` | Grafana admin password | admin |

### Docker Compose Overrides

Create `docker-compose.override.yml` for local customization:

```yaml
version: '3.8'

services:
  web:
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    volumes:
      - ./app:/app/app
```

---

## SSL/TLS Setup

### Let's Encrypt (Production)

```bash
# Automatic setup
./scripts/ssl_setup.sh your-domain.com admin@your-domain.com

# Manual certificate request
certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  -d your-domain.com \
  -d www.your-domain.com
```

### Self-Signed (Development)

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/privkey.pem \
  -out nginx/ssl/fullchain.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

### Certificate Auto-Renewal

The backup service includes automatic renewal:

```cron
0 3 * * * certbot renew --quiet && docker compose restart nginx
```

---

## Monitoring

### Access Dashboards

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://your-domain:3000 | admin/admin |
| Prometheus | http://your-domain:9090 | - |
| Alertmanager | http://your-domain:9093 | - |
| Loki | http://your-domain:3100 | - |

### Key Metrics

- **Application**: Request rate, error rate, response time
- **Database**: Connections, query time, storage
- **Cache**: Hit rate, memory usage
- **System**: CPU, memory, disk

### Configure Alerts

Edit `monitoring/alertmanager.yml`:

```yaml
receivers:
  - name: 'default-receiver'
    email_configs:
      - to: 'your-email@example.com'
```

---

## Backup & Recovery

### Manual Backup

```bash
# Database backup
docker compose exec postgres pg_dump -U repodiscover repodiscover > backup.sql

# Restore
docker compose exec -T postgres psql -U repodiscover repodiscover < backup.sql
```

### Automated Backups

Backups run daily at 2 AM and are stored in `./backups/`:

```bash
# List backups
ls -la backups/

# Restore from backup
gunzip -c backups/repodiscover_20260311_020000.sql.gz | \
  docker compose exec -T postgres psql -U repodiscover repodiscover
```

### Backup Retention

Default retention is 30 days. Configure in `.env`:

```bash
BACKUP_RETENTION_DAYS=30
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose logs web
docker compose logs postgres

# Check configuration
docker compose config

# Test database connection
docker compose exec postgres pg_isready
```

### High Memory Usage

```bash
# Check container memory
docker stats

# Restart services
docker compose restart

# Scale down workers
# Edit docker-compose.prod.yml, reduce replicas
```

### Database Connection Issues

```bash
# Check database health
curl http://localhost/health

# Test connection
docker compose exec postgres psql -U repodiscover -c "SELECT 1"

# Check connection pool
docker compose exec postgres psql -U repodiscover -c "SELECT * FROM pg_stat_activity"
```

### SSL Certificate Issues

```bash
# Verify certificate
openssl x509 -in nginx/ssl/fullchain.pem -text -noout

# Check expiration
openssl x509 -in nginx/ssl/fullchain.pem -enddate -noout

# Force renewal
./scripts/ssl_setup.sh your-domain.com
```

### Performance Issues

```bash
# Run performance tests
python scripts/perf_test.py --url http://localhost:8000

# Check slow queries
docker compose exec postgres psql -U repodiscover -c \
  "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10"
```

---

## Support

- **Documentation:** https://docs.repodiscoverai.com
- **GitHub Issues:** https://github.com/your-org/repodiscoverai/issues
- **Email:** support@repodiscoverai.com

---

**Last Reviewed:** 2026-03-11  
**Next Review:** 2026-04-11
