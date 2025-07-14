#!/bin/bash
# PostgreSQL Backup Script for SKYCASTER Weather API
# This script creates daily backups of the PostgreSQL database

# Configuration
BACKUP_DIR="/app/backend/backups"
DB_URL="postgresql://neondb_owner:npg_2bUiOWoTX0Rg@ep-misty-meadow-a1prskmn-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
BACKUP_NAME="skycaster_backup_$(date +%Y%m%d_%H%M%S).sql"
RETENTION_DAYS=7

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Create backup
echo "Creating backup: $BACKUP_NAME"
pg_dump "$DB_URL" > "$BACKUP_DIR/$BACKUP_NAME"

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo "Backup created successfully: $BACKUP_DIR/$BACKUP_NAME"
    
    # Compress backup
    gzip "$BACKUP_DIR/$BACKUP_NAME"
    echo "Backup compressed: $BACKUP_DIR/$BACKUP_NAME.gz"
    
    # Clean up old backups (keep only last 7 days)
    find "$BACKUP_DIR" -name "skycaster_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
    echo "Old backups cleaned up (keeping last $RETENTION_DAYS days)"
    
    # List current backups
    echo "Current backups:"
    ls -la "$BACKUP_DIR"/skycaster_backup_*.sql.gz
else
    echo "Backup failed!"
    exit 1
fi