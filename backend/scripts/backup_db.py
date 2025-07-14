#!/usr/bin/env python3
"""
PostgreSQL Backup Script for SKYCASTER Weather API
This script creates daily backups of the PostgreSQL database using SQLAlchemy
"""
import asyncio
import sys
import os
import json
import gzip
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import engine
from app.models import User, ApiKey, Subscription, UsageLog, Invoice, SupportTicket
from sqlalchemy import select, text

async def backup_database():
    """Create a backup of the database"""
    try:
        # Create backup directory
        backup_dir = Path("/app/backend/backups")
        backup_dir.mkdir(exist_ok=True)
        
        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"skycaster_backup_{timestamp}.json"
        backup_path = backup_dir / backup_filename
        
        print(f"🔧 Starting database backup to: {backup_path}")
        
        backup_data = {
            "backup_timestamp": timestamp,
            "database_version": None,
            "schema_version": None,
            "tables": {}
        }
        
        async with engine.begin() as conn:
            # Get database version
            result = await conn.execute(text("SELECT version()"))
            backup_data["database_version"] = result.scalar()
            
            # Get schema version from alembic
            try:
                result = await conn.execute(text("SELECT version_num FROM alembic_version"))
                backup_data["schema_version"] = result.scalar()
            except:
                backup_data["schema_version"] = "unknown"
        
        # Backup each table in separate transactions
        tables = [
            ("users", User),
            ("api_keys", ApiKey),
            ("subscriptions", Subscription),
            ("usage_logs", UsageLog),
            ("invoices", Invoice),
            ("support_tickets", SupportTicket)
        ]
        
        for table_name, model_class in tables:
            print(f"  📋 Backing up {table_name}...")
            
            async with engine.begin() as conn:
                # Get all records
                result = await conn.execute(select(model_class))
                records = result.fetchall()
                
                # Convert to JSON-serializable format
                table_data = []
                for record in records:
                    record_dict = {}
                    for column in model_class.__table__.columns:
                        value = getattr(record, column.name)
                        if value is not None:
                            if hasattr(value, 'isoformat'):  # datetime objects
                                record_dict[column.name] = value.isoformat()
                            else:
                                record_dict[column.name] = value
                        else:
                            record_dict[column.name] = None
                    table_data.append(record_dict)
                
                backup_data["tables"][table_name] = {
                    "count": len(table_data),
                    "data": table_data
                }
                
                print(f"    ✅ {len(table_data)} records backed up")
        
        # Save backup to file
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2, default=str)
        
        print(f"✅ Backup saved to: {backup_path}")
        
        # Compress backup
        compressed_path = backup_path.with_suffix('.json.gz')
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                f_out.writelines(f_in)
        
        # Remove uncompressed file
        backup_path.unlink()
        
        print(f"✅ Backup compressed to: {compressed_path}")
        
        # Show file size
        size_mb = compressed_path.stat().st_size / (1024 * 1024)
        print(f"📊 Backup size: {size_mb:.2f} MB")
        
        # Clean up old backups (keep only last 7 days)
        cutoff_date = datetime.now() - timedelta(days=7)
        for old_backup in backup_dir.glob("skycaster_backup_*.json.gz"):
            if old_backup.stat().st_mtime < cutoff_date.timestamp():
                old_backup.unlink()
                print(f"🗑️  Deleted old backup: {old_backup.name}")
        
        # List current backups
        backups = list(backup_dir.glob("skycaster_backup_*.json.gz"))
        print(f"📚 Current backups ({len(backups)} files):")
        for backup in sorted(backups):
            size_mb = backup.stat().st_size / (1024 * 1024)
            mod_time = datetime.fromtimestamp(backup.stat().st_mtime)
            print(f"  - {backup.name} ({size_mb:.2f} MB, {mod_time.strftime('%Y-%m-%d %H:%M:%S')})")
        
        print("🎉 Database backup completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database backup failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(backup_database())
    sys.exit(0 if success else 1)