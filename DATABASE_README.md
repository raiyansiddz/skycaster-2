# 🗃️ Skycaster Weather API - Database Management Guide

## 📋 Table of Contents
- [Overview](#overview)
- [Database Schema](#database-schema)
- [Setup & Installation](#setup--installation)
- [Migration Guide](#migration-guide)
- [Import & Export Procedures](#import--export-procedures)
- [Cross-Server Migration](#cross-server-migration)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)
- [Performance Optimization](#performance-optimization)
- [Security Best Practices](#security-best-practices)

## 🎯 Overview

The Skycaster Weather API uses PostgreSQL as its primary database with a comprehensive schema supporting:

- **User Management & Authentication**
- **API Key Management with UUID support**
- **Subscription & Billing System (Stripe integration)**
- **Weather API Configuration & Dynamic Pricing**
- **Usage Tracking & Analytics**
- **Enterprise-grade Audit Logging**
- **Security Event Monitoring**
- **Performance Metrics Collection**
- **Support Ticket System**

### Key Features
- ✅ Production-ready PostgreSQL schema
- ✅ Auto-generated from SQLAlchemy models
- ✅ UUID primary keys for scalability
- ✅ Comprehensive indexing for performance
- ✅ Multi-currency support
- ✅ Enterprise audit logging
- ✅ Automated schema generation tools

## 🗂️ Database Schema

### Core Tables

| Table | Purpose | Key Relationships |
|-------|---------|-------------------|
| `users` | User management & authentication | → `api_keys`, `subscriptions`, `usage_logs` |
| `api_keys` | API key management | → `users`, `usage_logs`, `weather_requests` |
| `subscriptions` | Subscription plans & billing | → `users`, `invoices` |
| `usage_logs` | API usage tracking | → `users`, `api_keys` |
| `weather_requests` | Weather API request logs | → `users`, `api_keys` |
| `pricing_config` | Dynamic pricing configuration | → `users` |
| `audit_logs` | Comprehensive system audit | - |
| `security_events` | Security incident tracking | - |
| `support_tickets` | Customer support system | → `users` |

### Schema Files
- **`/app/schema.sql`** - Production-ready complete schema
- **`/app/backend/schema_generator.py`** - Auto-generation tool
- **`/app/backend/alembic/`** - Migration files for production

## 🚀 Setup & Installation

### Prerequisites
- PostgreSQL 12+ 
- Python 3.8+
- Required extensions: `uuid-ossp`, `pgcrypto`

### Quick Start

#### 1. Fresh Database Setup
```bash
# Create new database
createdb skycaster_db

# Import complete schema
psql -d skycaster_db -f /app/schema.sql

# Verify tables created
psql -d skycaster_db -c "\dt"
```

#### 2. Using Schema Generator (Recommended for Development)
```bash
# Navigate to backend directory
cd /app/backend

# Set database connection
export SCHEMA_DB_URL="postgresql://user:password@localhost:5432/skycaster_db"

# Generate schema from models
python schema_generator.py --mode=create

# View generation report
cat schema_report.txt
```

#### 3. Using Alembic (Production)
```bash
# Initialize database with migrations
cd /app/backend
alembic upgrade head
```

### Environment Configuration

Create `.env` file in backend directory:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/skycaster_db

# Redis (required for caching & queues)
REDIS_URL=redis://localhost:6379

# Other configurations...
```

## 📈 Migration Guide

### Development to Production Migration

#### Step 1: Backup Current Data
```bash
# Export data only (no schema)
pg_dump -d source_db --data-only --inserts > data_backup.sql

# Export specific tables
pg_dump -d source_db -t users -t api_keys --data-only --inserts > user_data.sql
```

#### Step 2: Setup Production Database
```bash
# Create production database
createdb production_skycaster_db

# Apply production schema
psql -d production_skycaster_db -f /app/schema.sql

# Import data
psql -d production_skycaster_db -f data_backup.sql
```

#### Step 3: Verify Migration
```bash
# Check table counts
psql -d production_skycaster_db -c "
SELECT 
    schemaname,
    tablename,
    n_tup_ins - n_tup_del as row_count
FROM pg_stat_user_tables
ORDER BY tablename;"

# Test critical queries
psql -d production_skycaster_db -c "SELECT COUNT(*) FROM users;"
psql -d production_skycaster_db -c "SELECT COUNT(*) FROM api_keys;"
```

### Schema Version Upgrades

#### Using Alembic (Recommended)
```bash
# Check current version
alembic current

# Upgrade to latest
alembic upgrade head

# Downgrade if needed
alembic downgrade -1
```

#### Manual Schema Updates
```bash
# Generate new schema
python schema_generator.py --mode=validate > schema_changes.txt

# Review changes and apply manually
psql -d your_db -f manual_updates.sql
```

## 📤📥 Import & Export Procedures

### Complete Database Export
```bash
# Full database export (schema + data)
pg_dump -d skycaster_db -f skycaster_complete_backup.sql

# Compressed export
pg_dump -d skycaster_db | gzip > skycaster_backup.sql.gz

# Directory format (parallel export)
pg_dump -d skycaster_db -F d -j 4 -f skycaster_backup_dir/
```

### Complete Database Import
```bash
# From SQL file
psql -d new_db -f skycaster_complete_backup.sql

# From compressed file
gunzip -c skycaster_backup.sql.gz | psql -d new_db

# From directory format
pg_restore -d new_db -j 4 skycaster_backup_dir/
```

### Selective Data Export/Import

#### Export Specific Tables
```bash
# Export user and subscription data
pg_dump -d skycaster_db -t users -t subscriptions -t api_keys > user_data.sql

# Export configuration tables
pg_dump -d skycaster_db -t pricing_config -t currency_config -t variable_mapping > config_data.sql
```

#### Import with Conflict Resolution
```bash
# Import with conflict handling
psql -d target_db -c "
\copy users FROM 'users.csv' WITH CSV HEADER 
ON CONFLICT (email) DO UPDATE SET 
updated_at = EXCLUDED.updated_at;
"
```

### Data Cleaning Before Export
```sql
-- Clean old audit logs (older than 6 months)
DELETE FROM audit_logs WHERE timestamp < NOW() - INTERVAL '6 months';

-- Clean old usage logs (older than 1 year)  
DELETE FROM usage_logs WHERE created_at < NOW() - INTERVAL '1 year';

-- Vacuum to reclaim space
VACUUM ANALYZE;
```

## 🌐 Cross-Server Migration

### From Local to Cloud (e.g., NeonDB, AWS RDS)

#### Method 1: Direct Migration
```bash
# Export from local
pg_dump -d local_skycaster_db -f local_export.sql

# Import to cloud
psql -h cloud-host -U cloud-user -d cloud_db -f local_export.sql
```

#### Method 2: Using Cloud Tools
```bash
# For AWS RDS
aws s3 cp local_export.sql s3://your-bucket/
# Then use AWS Console to import

# For Google Cloud SQL
gcloud sql import sql instance-name gs://bucket/local_export.sql --database=cloud_db

# For Azure
az sql db import --server server-name --name db-name --storage-key key --storage-uri uri
```

#### Method 3: Schema Generator Approach
```bash
# On target server
export SCHEMA_DB_URL="postgresql://user:pass@new-server:5432/new_db"
python schema_generator.py --mode=create

# Then import data only
pg_dump -d source_db --data-only --inserts | psql -h new-server -U new-user -d new_db
```

### Migration Checklist

- [ ] Backup source database
- [ ] Test schema.sql on staging
- [ ] Verify all extensions are available on target
- [ ] Update connection strings in applications
- [ ] Test all application functionality
- [ ] Monitor performance after migration
- [ ] Update DNS/load balancer settings
- [ ] Verify scheduled backups on new server

## 🏭 Production Deployment

### Pre-Deployment Checklist
- [ ] PostgreSQL 12+ installed with required extensions
- [ ] Database user created with appropriate permissions
- [ ] Connection pooling configured (pgbouncer recommended)
- [ ] Backup strategy implemented
- [ ] Monitoring configured
- [ ] SSL/TLS configured for connections
- [ ] Performance tuning completed

### Production Schema Deployment
```bash
# 1. Create production database
createdb -E UTF8 production_skycaster_db

# 2. Enable required extensions
psql -d production_skycaster_db -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
psql -d production_skycaster_db -c "CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";"

# 3. Apply production schema
psql -d production_skycaster_db -f /app/schema.sql

# 4. Verify deployment
psql -d production_skycaster_db -c "\dt+"
```

### Production Configuration
```sql
-- Optimize for production
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Reload configuration
SELECT pg_reload_conf();
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Extension Not Available
```bash
# Error: extension "uuid-ossp" is not available
# Solution: Install postgresql-contrib
sudo apt-get install postgresql-contrib-12
```

#### 2. Permission Denied
```bash
# Error: permission denied to create extension
# Solution: Connect as superuser or grant permissions
sudo -u postgres psql -d your_db -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
```

#### 3. Enum Already Exists
```sql
-- Error: type "user_role" already exists
-- Solution: Use IF NOT EXISTS or drop and recreate
DROP TYPE IF EXISTS user_role CASCADE;
CREATE TYPE user_role AS ENUM ('user', 'admin');
```

#### 4. Foreign Key Violations During Import
```sql
-- Temporarily disable foreign key checks
SET session_replication_role = replica;

-- Import data
\i your_data.sql

-- Re-enable foreign key checks
SET session_replication_role = DEFAULT;
```

### Diagnostic Queries

#### Check Database Size
```sql
SELECT 
    pg_database.datname,
    pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database
ORDER BY pg_database_size(pg_database.datname) DESC;
```

#### Check Table Sizes
```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_total_relation_size(schemaname||'.'||tablename) AS raw_size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY raw_size DESC;
```

#### Check Index Usage
```sql
SELECT 
    indexrelname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

## ⚡ Performance Optimization

### Indexing Strategy
```sql
-- Add performance indexes for common queries
CREATE INDEX CONCURRENTLY idx_usage_logs_created_at_user_id 
ON usage_logs (created_at, user_id);

CREATE INDEX CONCURRENTLY idx_weather_requests_timestamp 
ON weather_requests (created_at) WHERE success = true;

CREATE INDEX CONCURRENTLY idx_audit_logs_activity_timestamp 
ON audit_logs (activity_type, timestamp);
```

### Partitioning Large Tables
```sql
-- Partition audit_logs by month
CREATE TABLE audit_logs_y2025m07 PARTITION OF audit_logs
FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');

-- Automatic partition creation
SELECT cron.schedule('create-monthly-partitions', '0 0 1 * *', 
'SELECT create_monthly_partition()');
```

### Query Optimization
```sql
-- Optimize common queries with materialized views
CREATE MATERIALIZED VIEW user_usage_summary AS
SELECT 
    user_id,
    COUNT(*) as total_requests,
    SUM(cost) as total_cost,
    MAX(created_at) as last_request
FROM usage_logs
GROUP BY user_id;

-- Refresh periodically
REFRESH MATERIALIZED VIEW user_usage_summary;
```

## 🔒 Security Best Practices

### Database Security
```sql
-- Create application user with limited permissions
CREATE USER skycaster_app WITH PASSWORD 'secure_password';

-- Grant only necessary permissions
GRANT CONNECT ON DATABASE skycaster_db TO skycaster_app;
GRANT USAGE ON SCHEMA public TO skycaster_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO skycaster_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO skycaster_app;

-- Row Level Security for multi-tenant data
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY usage_logs_policy ON usage_logs
FOR ALL TO skycaster_app
USING (user_id = current_setting('app.current_user_id')::uuid);
```

### Connection Security
```bash
# postgresql.conf
ssl = on
ssl_cert_file = '/path/to/server.crt'
ssl_key_file = '/path/to/server.key'
ssl_ciphers = 'HIGH:MEDIUM:+3DES:!aNULL'

# pg_hba.conf
hostssl all all 0.0.0.0/0 md5
```

### Backup Security
```bash
# Encrypted backups
pg_dump -d skycaster_db | gpg --cipher-algo AES256 --compress-algo 2 --symmetric --output backup.sql.gpg

# Restore encrypted backup
gpg --decrypt backup.sql.gpg | psql -d restore_db
```

## 📊 Monitoring & Maintenance

### Regular Maintenance Tasks
```bash
#!/bin/bash
# monthly_maintenance.sh

# Update statistics
psql -d skycaster_db -c "ANALYZE;"

# Reindex if needed
psql -d skycaster_db -c "REINDEX DATABASE skycaster_db;"

# Clean old logs
psql -d skycaster_db -c "DELETE FROM audit_logs WHERE timestamp < NOW() - INTERVAL '6 months';"

# Vacuum
psql -d skycaster_db -c "VACUUM ANALYZE;"
```

### Monitoring Queries
```sql
-- Active connections
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE state = 'active';

-- Long running queries
SELECT 
    pid,
    user,
    pg_stat_activity.query_start,
    now() - pg_stat_activity.query_start AS query_time,
    query
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';

-- Database locks
SELECT 
    bl.pid AS blocked_pid,
    bl.query as blocked_query,
    kl.pid AS blocking_pid,
    kl.query AS blocking_query
FROM pg_catalog.pg_locks bl
JOIN pg_catalog.pg_stat_activity bl_act ON bl.pid = bl_act.pid
JOIN pg_catalog.pg_locks kl ON bl.transactionid = kl.transactionid
JOIN pg_catalog.pg_stat_activity kl_act ON kl.pid = kl_act.pid
WHERE NOT bl.GRANTED AND bl.pid != kl.pid;
```

## 🆘 Emergency Procedures

### Database Recovery
```bash
# Point-in-time recovery
pg_restore -d skycaster_db -T timestamp backup.dump

# Restore from WAL files
pg_ctl start -D /var/lib/postgresql/data -o "-c recovery_target_time='2025-07-19 12:00:00'"
```

### Data Corruption Recovery
```sql
-- Check for corruption
SELECT * FROM pg_stat_database_conflicts;

-- Rebuild indexes
REINDEX DATABASE skycaster_db;

-- Check table integrity
SELECT * FROM pg_stat_user_tables WHERE n_tup_ins < 0;
```

### Emergency Contacts & Procedures
- **Database Admin**: [Contact information]
- **Application Team**: [Contact information]  
- **Infrastructure Team**: [Contact information]

### Escalation Matrix
1. **Level 1**: Application restart, basic diagnostics
2. **Level 2**: Database performance tuning, query optimization
3. **Level 3**: Database recovery, infrastructure changes
4. **Level 4**: Full disaster recovery, data restoration

---

## 📞 Support & Maintenance

For questions or issues with database management:

1. **Check this guide first** - Most common scenarios are covered
2. **Review logs** - Check PostgreSQL logs and application logs
3. **Test on staging** - Always test schema changes on non-production first
4. **Contact team** - Reach out to the development team for complex issues

---

**Last Updated**: July 2025  
**Version**: 2.0  
**Maintained by**: Skycaster Development Team