# Backup and Disaster Recovery Strategy

This document outlines the backup policies, retention schedules, and restore procedures for the platform.

## Backup Policy

### PostgreSQL Database
- **Continuous Archiving**: Write-Ahead Logs (WAL) are continuously archived to Object Storage (S3), enabling Point-In-Time Recovery (PITR) with an RPO of 5 minutes.
- **Daily Snapshots**: Automated full database snapshots taken daily at 00:00 UTC.
- **Retention**: Daily snapshots retained for 30 days. Weekly snapshots retained for 1 year.

### Object Storage (Files & Reports)
- File storage buckets (S3) must have **Versioning Enabled** to prevent accidental overwrites or deletions.
- Soft-deleted items are retained via lifecycle policies for 90 days before permanent deletion.

## Disaster Recovery (DR)

- **Recovery Point Objective (RPO)**: 5 minutes (via WAL).
- **Recovery Time Objective (RTO)**: 4 hours.

## Restore Procedure

### Scenario A: Accidental Data Deletion (Point-In-Time Recovery)
1. Provision a new temporary database instance from the latest automated snapshot prior to the incident.
2. Replay the WAL logs up to the exact timestamp before the deletion occurred.
3. Validate data integrity.
4. Update application routing (DNS or connection string) to point to the recovered instance.

### Scenario B: Complete Infrastructure Failure
1. Execute the Infrastructure as Code (IaC) pipeline to spin up a new VPC, Subnets, and Compute instances in the failover region.
2. Restore the PostgreSQL database from the cross-region replicated snapshot.
3. Start the Redis cache (data is ephemeral; start fresh).
4. Deploy application containers pointing to the newly restored DB.
5. Failover the global DNS to the new API Gateway.

## Manual Backup Trigger (Reference)
A reference script for executing manual backups is located at `backend/scripts/backup.sh`.
```bash
./backend/scripts/backup.sh --bucket s3://my-backup-bucket
```
