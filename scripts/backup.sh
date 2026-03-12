#!/bin/bash
# Automated Database Backup Script
# Usage: ./backup.sh

set -e

# Configuration
DB_HOST=${DB_HOST:-postgres}
DB_NAME=${DB_NAME:-repodiscover}
DB_USER=${DB_USER:-repodiscover}
DB_PASSWORD=${DB_PASSWORD:-changeme}
BACKUP_DIR=${BACKUP_DIR:-/backups}
RETENTION_DAYS=${RETENTION_DAYS:-30}

# Timestamp for backup file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"

echo "🗄️  Starting database backup..."
echo "   Database: $DB_NAME"
echo "   Host: $DB_HOST"
echo "   Backup: $BACKUP_FILE"

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

# Perform backup
PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" | gzip > "$BACKUP_FILE"

# Verify backup
if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Backup completed successfully!"
    echo "   File: $BACKUP_FILE"
    echo "   Size: $BACKUP_SIZE"
else
    echo "❌ Backup failed!"
    exit 1
fi

# Cleanup old backups
echo ""
echo "🧹 Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete
REMAINING=$(ls -1 "$BACKUP_DIR"/*.sql.gz 2>/dev/null | wc -l)
echo "   Remaining backups: $REMAINING"

# List recent backups
echo ""
echo "📋 Recent backups:"
ls -lht "$BACKUP_DIR"/*.sql.gz 2>/dev/null | head -5 || echo "   No backups found"

echo ""
echo "✅ Backup process complete!"
