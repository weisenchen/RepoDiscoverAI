#!/bin/bash
# SSL Certificate Setup Script using Let's Encrypt
# Usage: ./scripts/ssl_setup.sh your-domain.com

set -e

DOMAIN=${1:-${DOMAIN_NAME:-localhost}}
EMAIL=${2:-${ADMIN_EMAIL:-admin@localhost}}

echo "🔐 Setting up SSL certificate for $DOMAIN"

# Create directories
mkdir -p nginx/ssl
mkdir -p nginx/logs
mkdir -p /var/www/certbot

# Check if running in production environment
if [ "$DOMAIN" = "localhost" ]; then
    echo "⚠️  Generating self-signed certificate for development..."
    
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/privkey.pem \
        -out nginx/ssl/fullchain.pem \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN" \
        -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost,IP:127.0.0.1"
    
    echo "✅ Self-signed certificate generated successfully!"
    echo "⚠️  Note: Browser will show security warning for self-signed certs"
else
    echo "📜 Requesting Let's Encrypt certificate..."
    
    # Install certbot if not present
    if ! command -v certbot &> /dev/null; then
        echo "Installing certbot..."
        apt-get update && apt-get install -y certbot
    fi
    
    # Request certificate
    certbot certonly --webroot \
        --webroot-path=/var/www/certbot \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        --force-renewal \
        -d "$DOMAIN" \
        -d "www.$DOMAIN"
    
    # Copy certificates to nginx directory
    cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem nginx/ssl/fullchain.pem
    cp /etc/letsencrypt/live/$DOMAIN/privkey.pem nginx/ssl/privkey.pem
    
    # Set permissions
    chmod 600 nginx/ssl/privkey.pem
    chmod 644 nginx/ssl/fullchain.pem
    
    echo "✅ Let's Encrypt certificate installed successfully!"
    
    # Setup auto-renewal cron job
    echo "⏰ Setting up certificate auto-renewal..."
    (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && docker compose -f docker-compose.prod.yml restart nginx") | crontab -
    
    echo "✅ Auto-renewal cron job configured (daily at 3 AM)"
fi

# Verify certificate
echo ""
echo "📋 Certificate details:"
openssl x509 -in nginx/ssl/fullchain.pem -text -noout | grep -E "(Subject:|Issuer:|Not Before:|Not After :)"

echo ""
echo "✅ SSL setup complete!"
echo "🌐 Your site will be available at: https://$DOMAIN"
