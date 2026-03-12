# Monitoring Guide for RepoDiscoverAI

## Overview

RepoDiscoverAI uses the Prometheus-Grafana-Loki stack for comprehensive monitoring.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Prometheus                            │
│  - Metrics collection (15s interval)                     │
│  - Alert rule evaluation                                 │
│  - 15-day retention                                      │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│   Grafana     │ │    Alert      │ │     Loki      │
│  Dashboard    │ │   Manager     │ │    Logs       │
│   (3000)      │ │   (9093)      │ │   (3100)      │
└───────────────┘ └───────────────┘ └───────────────┘
```

---

## Metrics Collected

### Application Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | Request latency |
| `http_requests_in_progress` | Gauge | Current requests |
| `db_query_duration_seconds` | Histogram | Database query time |
| `cache_hits_total` | Counter | Cache hits |
| `cache_misses_total` | Counter | Cache misses |

### System Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `node_cpu_seconds_total` | Counter | CPU usage |
| `node_memory_MemAvailable_bytes` | Gauge | Available memory |
| `node_filesystem_avail_bytes` | Gauge | Disk space |
| `pg_stat_activity_count` | Gauge | DB connections |
| `redis_memory_used_bytes` | Gauge | Redis memory |

---

## Dashboards

### Main Dashboard (ID: repodiscover-main)

**Panels:**
1. Service Status - UP/DOWN indicator
2. Active Users - Requests per second
3. Error Rate - Percentage of 5xx errors
4. Cache Hit Rate - Redis effectiveness
5. Request Rate & Latency - Time series
6. Database Connections - Pool usage
7. CPU Usage - By instance
8. Memory Usage - By instance
9. Disk Usage - By instance
10. Application Logs - Live tail
11. Active Alerts - Current firing alerts

**Access:**
```
URL: http://localhost:3000
Dashboard: RepoDiscoverAI - Main Dashboard
```

---

## Alerts

### Critical Alerts

| Alert | Condition | Action |
|-------|-----------|--------|
| ServiceDown | up == 0 for 1m | Page on-call |
| PostgresDown | PostgreSQL unavailable | Page on-call |
| RedisDown | Redis unavailable | Page on-call |
| HighErrorRate | Error rate > 10% for 5m | Investigate |
| BackupNotRecent | No backup in 24h | Run backup |

### Warning Alerts

| Alert | Condition | Action |
|-------|-----------|--------|
| HighResponseTime | P95 > 1s for 5m | Monitor |
| PostgresHighConnections | > 80% pool usage | Scale up |
| RedisHighMemory | > 90% memory | Clear cache |
| HighCPUUsage | > 80% for 10m | Investigate |
| HighMemoryUsage | > 85% for 10m | Investigate |
| DiskSpaceLow | > 85% for 10m | Clean up |

---

## Log Aggregation

### Log Sources

| Source | Path | Labels |
|--------|------|--------|
| Application | /var/log/app/*.log | job=repodiscover |
| Nginx Access | /var/log/nginx/access.log | job=nginx |
| Nginx Error | /var/log/nginx/error.log | job=nginx |
| System | /var/log/syslog | job=syslog |

### Query Examples

```
# Application errors
{job="repodiscover"} |= "ERROR"

# Slow API requests
{job="nginx"} |= "GET /api/" |~ "\\[5..\\]"

# Database connection issues
{job="repodiscover"} |= "database" |= "connection"
```

---

## Alertmanager Configuration

### Notification Channels

```yaml
# Email
email_configs:
  - to: 'admin@repodiscoverai.com'

# Slack
slack_configs:
  - channel: '#alerts'
    api_url: 'https://hooks.slack.com/services/...'

# PagerDuty (critical only)
pagerduty_configs:
  - service_key: 'your-pagerduty-key'
```

### Routing Rules

```
All alerts → Default receiver (email)
  ↓
Critical severity → Critical receiver (email + slack + pagerduty)
  ↓
Warning severity → Warning receiver (slack)
```

---

## Prometheus Queries

### Request Rate

```promql
sum(rate(http_requests_total{job="repodiscover-web"}[5m]))
```

### Error Rate

```promql
sum(rate(http_requests_total{status=~"5.."}[5m])) / 
sum(rate(http_requests_total[5m])) * 100
```

### P95 Latency

```promql
histogram_quantile(0.95, 
  rate(http_request_duration_seconds_bucket[5m]))
```

### Cache Hit Rate

```promql
rate(redis_keyspace_hits_total[5m]) / 
(rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m])) * 100
```

### Database Connection Usage

```promql
pg_stat_activity_count / pg_settings_max_connections * 100
```

---

## Maintenance

### Log Rotation

Logs are automatically rotated by Promtail. Retention:
- Application logs: 7 days
- Nginx logs: 14 days
- System logs: 30 days

### Metrics Retention

Prometheus retains metrics for 15 days. For longer retention:
- Configure remote storage (Thanos, Cortex)
- Export to long-term storage

### Backup Monitoring Data

```bash
# Backup Prometheus data
docker compose run --rm -v $(pwd)/backups:/backups \
  alpine tar czf /backups/prometheus-backup.tar.gz \
  /prometheus
```

---

## Troubleshooting

### Prometheus Not Scraping

```bash
# Check targets
curl http://localhost:9090/api/v1/targets

# Check config
docker compose exec prometheus cat /etc/prometheus/prometheus.yml

# Reload config
curl -X POST http://localhost:9090/-/reload
```

### Grafana Not Showing Data

1. Verify Prometheus datasource is connected
2. Check time range selector
3. Verify metric names in queries

### Alerts Not Firing

```bash
# Check alert rules
curl http://localhost:9090/api/v1/rules

# Check pending alerts
curl http://localhost:9090/api/v1/alerts

# Check Alertmanager
curl http://localhost:9093/api/v2/alerts
```

---

**Last Updated**: 2026-03-11  
**Version**: 1.0
