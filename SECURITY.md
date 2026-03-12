# Security Hardening Guide for RepoDiscoverAI

## Overview

This document outlines security measures implemented for production deployment.

---

## 🔐 Authentication & Authorization

### API Key Authentication

```python
# Generate API key
import secrets
api_key = secrets.token_urlsafe(32)
# Store hash in database, never store plain text
```

### Rate Limiting

| Endpoint | Limit | Window |
|----------|-------|--------|
| /api/search | 100 req | per minute |
| /api/repos | 200 req | per minute |
| /api/trending | 50 req | per minute |
| /api/* (authenticated) | 1000 req | per minute |

### Implementation

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/search")
@limiter.limit("100/minute")
async def search(request: Request):
    ...
```

---

## 🔒 HTTPS Configuration

### Nginx SSL Settings

```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:50m;
ssl_session_timeout 1d;
```

### HSTS Header

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

---

## 🛡️ Input Validation & Sanitization

### SQL Injection Prevention

- ✅ Use parameterized queries (asyncpg)
- ✅ ORM with built-in protection
- ✅ Input validation on all user inputs

### XSS Prevention

- ✅ Content-Security-Policy header
- ✅ Output encoding
- ✅ HTTP-only cookies

### CSRF Protection

```python
from fastapi_csrf_protect import CsrfProtect

@CsrfProtect.load_header
async def load_csrf_header(request: Request):
    return request.headers.get("X-CSRF-Token")
```

---

## 🔑 Secrets Management

### Environment Variables

```bash
# .env (never commit!)
SECRET_KEY=your-secret-key-min-32-chars
DATABASE_URL=postgresql://user:pass@host/db
REDIS_URL=redis://host:6379/0
GITHUB_TOKEN=ghp_xxx
```

### Docker Secrets

```yaml
secrets:
  db_password:
    external: true
  api_key:
    external: true

services:
  web:
    secrets:
      - db_password
      - api_key
```

---

## 🚫 Security Headers

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self';" always;
```

---

## 📊 Security Monitoring

### Failed Login Attempts

```python
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 900  # 15 minutes

async def check_login_attempts(user_id: int):
    attempts = await get_failed_attempts(user_id)
    if attempts >= MAX_LOGIN_ATTEMPTS:
        raise AccountLockedException()
```

### Audit Logging

```python
import logging

security_logger = logging.getLogger("security")

async def log_security_event(event_type: str, details: dict):
    security_logger.info(f"{event_type}: {details}")
```

---

## 🔍 Security Scanning

### Dependency Scanning

```bash
# Run safety check
safety check -r requirements.txt

# Run bandit
bandit -r app/ -f json -o bandit-report.json
```

### Container Scanning

```bash
# Scan Docker image
docker scan repodiscoverai:latest

# Run trivy
trivy image repodiscoverai:latest
```

---

## 📋 Security Checklist

### Pre-Deployment

- [ ] All secrets rotated
- [ ] HTTPS enforced
- [ ] Rate limiting enabled
- [ ] Security headers configured
- [ ] Dependencies scanned
- [ ] Container scanned
- [ ] Firewall rules configured

### Post-Deployment

- [ ] SSL certificate valid
- [ ] Monitoring active
- [ ] Alerts configured
- [ ] Backup verified
- [ ] Access logs reviewed

---

## 🚨 Incident Response

### Contact

- Security Team: security@repodiscoverai.com
- On-Call: oncall@repodiscoverai.com

### Steps

1. Identify and contain the incident
2. Assess impact and scope
3. Notify affected users if required
4. Document and learn

---

**Last Updated**: 2026-03-11  
**Version**: 1.0
