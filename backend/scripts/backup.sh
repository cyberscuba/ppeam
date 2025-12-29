#!/bin/bash
# Backup script for PostgreSQL database

set -e

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/exhibidores_backup_$TIMESTAMP.sql"

echo "Starting backup at $(date)"

# Create backup directory if not exists
mkdir -p $BACKUP_DIR

# Dump database
pg_dump -U $POSTGRES_USER $POSTGRES_DB > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

echo "Backup completed: ${BACKUP_FILE}.gz"

# Delete backups older than retention period
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Old backups cleaned (retention: $RETENTION_DAYS days)"

# Optional: Upload to S3
if [ ! -z "$BACKUP_S3_BUCKET" ]; then
    echo "Uploading to S3..."
    aws s3 cp ${BACKUP_FILE}.gz s3://$BACKUP_S3_BUCKET/
    echo "Upload completed"
fi

echo "Backup process finished at $(date)"
