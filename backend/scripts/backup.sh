#!/bin/bash
set -e

# Backup Configuration
PG_USER=${POSTGRES_USER:-postgres}
PG_DB=${POSTGRES_DB:-platform}
PG_HOST=${POSTGRES_HOST:-localhost}
S3_BUCKET=""

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --bucket) S3_BUCKET="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

if [ -z "$S3_BUCKET" ]; then
    echo "Error: --bucket argument is required"
    exit 1
fi

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="/tmp/platform_backup_${TIMESTAMP}.sql.gz"

echo "Starting backup of ${PG_DB} to ${BACKUP_FILE}..."

# Dump and compress
pg_dump -h $PG_HOST -U $PG_USER $PG_DB | gzip > $BACKUP_FILE

echo "Backup complete. Uploading to S3..."

# Upload to S3 (assuming AWS CLI is configured)
# For MinIO, you might use mc (MinIO Client) instead.
aws s3 cp $BACKUP_FILE $S3_BUCKET/db-backups/platform_backup_${TIMESTAMP}.sql.gz

echo "Upload complete. Cleaning up local backup file..."
rm $BACKUP_FILE

echo "Database Backup finished successfully."
