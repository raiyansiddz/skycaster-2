#!/usr/bin/env python3
"""
Test script to verify PostgreSQL database connection
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import engine, get_db
from app.models import User
from sqlalchemy import text

def test_connection():
    """Test database connection and basic operations"""
    try:
        print("🔧 Testing PostgreSQL connection...")
        
        # Test basic connection
        with engine.begin() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Connected to PostgreSQL: {version}")
            
            # Test table exists
            result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'users'"))
            count = result.scalar()
            print(f"✅ Users table exists: {count > 0}")
            
            # Test table structure
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' ORDER BY ordinal_position"))
            columns = [row[0] for row in result]
            print(f"✅ Users table columns: {columns}")
            
            # Test all core tables
            core_tables = ['users', 'api_keys', 'subscriptions', 'pricing_config', 'variable_mapping', 'weather_requests']
            for table in core_tables:
                result = conn.execute(text(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table}'"))
                exists = result.scalar() > 0
                print(f"✅ {table} table exists: {exists}")
            
        print("🎉 Database connection test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)