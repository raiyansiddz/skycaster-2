#!/usr/bin/env python3
"""
Skycaster Weather API - Schema Generator Script
===============================================

This script connects to a PostgreSQL database and auto-generates/creates
all tables, enums, and constraints based on existing SQLAlchemy models.

Features:
- Connects to PostgreSQL using environment variables
- Auto-generates schema from SQLAlchemy models
- Drops existing tables if needed (DEV MODE ONLY)
- Creates all enums, tables, relationships, and constraints
- Comprehensive logging for each operation
- Validates schema after creation

Usage:
    # Set database URL (required)
    export SCHEMA_DB_URL="postgresql://user:password@host:port/database"
    
    # Run the generator
    python schema_generator.py
    
    # Or with parameters
    python schema_generator.py --mode=create --validate=true

Author: Skycaster Team
Version: 2.0
Created: July 2025
"""

import os
import sys
import logging
import argparse
from typing import Optional
from datetime import datetime

try:
    from sqlalchemy import create_engine, text, inspect
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.pool import NullPool
except ImportError as e:
    print(f"❌ Error: Missing required dependencies: {e}")
    print("Install with: pip install sqlalchemy psycopg2-binary")
    sys.exit(1)

# Add the backend path to sys.path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir)
sys.path.insert(0, backend_dir)

try:
    from app.models import Base
    from app.models.user import User, UserRole
    from app.models.api_key import ApiKey
    from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionPlan
    from app.models.usage_log import UsageLog
    from app.models.invoice import Invoice, InvoiceStatus
    from app.models.support_ticket import SupportTicket, TicketStatus, TicketPriority
    from app.models.pricing_config import PricingConfig, CurrencyConfig, VariableMapping, WeatherRequest
    from app.models.audit_log import AuditLog, SecurityEvent, UserActivity, PerformanceMetric
except ImportError as e:
    print(f"❌ Error: Could not import models: {e}")
    print("Make sure you're running this script from the backend directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('schema_generator.log')
    ]
)
logger = logging.getLogger(__name__)

class SchemaGenerator:
    """
    Schema Generator for Skycaster Weather API
    """
    
    def __init__(self, database_url: str, mode: str = "create"):
        self.database_url = database_url
        self.mode = mode.lower()
        self.engine = None
        self.session = None
        
        # Validate mode
        if self.mode not in ["create", "recreate", "validate"]:
            raise ValueError("Mode must be 'create', 'recreate', or 'validate'")
    
    def connect_database(self) -> bool:
        """
        Establish database connection
        """
        try:
            logger.info(f"🔗 Connecting to database: {self.database_url.split('@')[1] if '@' in self.database_url else 'localhost'}")
            
            # Create engine with optimized settings for schema operations
            self.engine = create_engine(
                self.database_url,
                echo=True,  # Show SQL queries
                pool_pre_ping=True,
                poolclass=NullPool,  # Disable connection pooling for schema operations
                connect_args={
                    "application_name": "skycaster_schema_generator",
                    "options": "-c default_transaction_isolation=read_committed"
                }
            )
            
            # Test connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                logger.info(f"✅ Connected successfully to: {version}")
            
            # Create session
            SessionLocal = sessionmaker(bind=self.engine)
            self.session = SessionLocal()
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error during connection: {e}")
            return False
    
    def enable_extensions(self) -> bool:
        """
        Enable required PostgreSQL extensions
        """
        try:
            logger.info("🔧 Enabling PostgreSQL extensions...")
            
            extensions = [
                'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"',
                'CREATE EXTENSION IF NOT EXISTS "pgcrypto"'
            ]
            
            with self.engine.connect() as conn:
                for ext_sql in extensions:
                    conn.execute(text(ext_sql))
                    logger.info(f"✅ Extension enabled: {ext_sql}")
                conn.commit()
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Failed to enable extensions: {e}")
            return False
    
    def create_enums(self) -> bool:
        """
        Create custom enum types
        """
        try:
            logger.info("📝 Creating enum types...")
            
            enums = [
                "CREATE TYPE user_role AS ENUM ('user', 'admin')",
                "CREATE TYPE subscription_plan AS ENUM ('free', 'developer', 'business', 'enterprise')",
                "CREATE TYPE subscription_status AS ENUM ('active', 'cancelled', 'past_due', 'incomplete', 'trialing')",
                "CREATE TYPE ticket_status AS ENUM ('open', 'in_progress', 'resolved', 'closed')",
                "CREATE TYPE ticket_priority AS ENUM ('low', 'medium', 'high', 'urgent')",
                "CREATE TYPE invoice_status AS ENUM ('draft', 'open', 'paid', 'void', 'uncollectible')"
            ]
            
            with self.engine.connect() as conn:
                for enum_sql in enums:
                    try:
                        conn.execute(text(enum_sql))
                        enum_name = enum_sql.split("CREATE TYPE ")[1].split(" AS")[0]
                        logger.info(f"✅ Enum created: {enum_name}")
                    except SQLAlchemyError as e:
                        if "already exists" in str(e):
                            enum_name = enum_sql.split("CREATE TYPE ")[1].split(" AS")[0]
                            logger.info(f"⚠️  Enum already exists: {enum_name}")
                        else:
                            raise e
                conn.commit()
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Failed to create enums: {e}")
            return False
    
    def drop_tables(self) -> bool:
        """
        Drop all existing tables (USE WITH CAUTION)
        """
        try:
            logger.warning("⚠️  DROPPING ALL EXISTING TABLES...")
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("🗑️  All tables dropped successfully")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Failed to drop tables: {e}")
            return False
    
    def create_tables(self) -> bool:
        """
        Create all tables from SQLAlchemy models
        """
        try:
            logger.info("🏗️  Creating tables from SQLAlchemy models...")
            
            # Get all tables from metadata
            tables = Base.metadata.sorted_tables
            logger.info(f"📊 Found {len(tables)} tables to create:")
            
            for table in tables:
                logger.info(f"   - {table.name}")
            
            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ All tables created successfully")
            
            # Verify table creation
            inspector = inspect(self.engine)
            created_tables = inspector.get_table_names()
            logger.info(f"🔍 Verified {len(created_tables)} tables in database:")
            
            for table_name in sorted(created_tables):
                logger.info(f"   ✓ {table_name}")
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Failed to create tables: {e}")
            return False
    
    def insert_initial_data(self) -> bool:
        """
        Insert essential initial data
        """
        try:
            logger.info("📊 Inserting initial configuration data...")
            
            # Initial pricing config data
            pricing_data = [
                ("pc_001", "ambient_temp(K)", "omega", 1.18, "INR", 18.0, True, True),
                ("pc_002", "wind_10m", "omega", 1.18, "INR", 18.0, True, True),
                ("pc_003", "wind_100m", "omega", 1.18, "INR", 18.0, True, True),
                ("pc_004", "relative_humidity(%)", "omega", 1.18, "INR", 18.0, True, True),
                ("pc_005", "temperature(K)", "nova", 1.18, "INR", 18.0, True, True),
                ("pc_006", "surface_pressure(Pa)", "nova", 1.18, "INR", 18.0, True, True),
                ("pc_007", "cumulus_precipitation(mm)", "nova", 1.18, "INR", 18.0, True, True),
                ("pc_008", "ghi(W/m2)", "nova", 1.18, "INR", 18.0, True, True),
                ("pc_009", "ghi_farms(W/m2)", "nova", 1.18, "INR", 18.0, True, True),
                ("pc_010", "clear_sky_ghi_farms(W/m2)", "nova", 1.18, "INR", 18.0, True, True),
                ("pc_011", "albedo", "nova", 1.18, "INR", 18.0, True, True),
                ("pc_012", "ct", "arc", 1.18, "INR", 18.0, True, True),
                ("pc_013", "pc", "arc", 1.18, "INR", 18.0, True, True),
                ("pc_014", "pcph", "arc", 1.18, "INR", 18.0, True, True)
            ]
            
            # Insert pricing configuration
            existing_pricing = self.session.query(PricingConfig).count()
            if existing_pricing == 0:
                for data in pricing_data:
                    config = PricingConfig(
                        id=data[0],
                        variable_name=data[1],
                        endpoint_type=data[2],
                        base_price=data[3],
                        currency=data[4],
                        tax_rate=data[5],
                        tax_enabled=data[6],
                        is_active=data[7]
                    )
                    self.session.add(config)
                
                self.session.commit()
                logger.info(f"✅ Inserted {len(pricing_data)} pricing configurations")
            else:
                logger.info(f"⚠️  Pricing configurations already exist ({existing_pricing} records)")
            
            # Insert currency configurations
            currency_data = [
                ("cc_001", "INR", "₹", "Indian Rupee", 1.0, True),
                ("cc_002", "USD", "$", "US Dollar", 0.012, True),
                ("cc_003", "EUR", "€", "Euro", 0.011, True),
                ("cc_004", "GBP", "£", "British Pound", 0.0095, True)
            ]
            
            existing_currency = self.session.query(CurrencyConfig).count()
            if existing_currency == 0:
                for data in currency_data:
                    config = CurrencyConfig(
                        id=data[0],
                        currency_code=data[1],
                        currency_symbol=data[2],
                        currency_name=data[3],
                        exchange_rate=data[4],
                        is_active=data[5]
                    )
                    self.session.add(config)
                
                self.session.commit()
                logger.info(f"✅ Inserted {len(currency_data)} currency configurations")
            else:
                logger.info(f"⚠️  Currency configurations already exist ({existing_currency} records)")
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Failed to insert initial data: {e}")
            self.session.rollback()
            return False
    
    def validate_schema(self) -> bool:
        """
        Validate the created schema
        """
        try:
            logger.info("🔍 Validating schema...")
            
            inspector = inspect(self.engine)
            
            # Check tables
            tables = inspector.get_table_names()
            expected_tables = [table.name for table in Base.metadata.sorted_tables]
            
            missing_tables = set(expected_tables) - set(tables)
            if missing_tables:
                logger.error(f"❌ Missing tables: {missing_tables}")
                return False
            
            logger.info(f"✅ All {len(expected_tables)} expected tables exist")
            
            # Check foreign keys
            fk_count = 0
            for table_name in tables:
                fks = inspector.get_foreign_keys(table_name)
                fk_count += len(fks)
                
                for fk in fks:
                    logger.debug(f"   FK: {table_name}.{fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
            
            logger.info(f"✅ Found {fk_count} foreign key constraints")
            
            # Check indexes
            index_count = 0
            for table_name in tables:
                indexes = inspector.get_indexes(table_name)
                index_count += len(indexes)
            
            logger.info(f"✅ Found {index_count} indexes")
            
            # Test basic operations
            test_user_count = self.session.query(User).count()
            logger.info(f"✅ Schema validation successful (test query returned {test_user_count} users)")
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Schema validation failed: {e}")
            return False
    
    def generate_schema_report(self) -> str:
        """
        Generate a comprehensive schema report
        """
        try:
            logger.info("📋 Generating schema report...")
            
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            
            report = []
            report.append("=" * 80)
            report.append("SKYCASTER WEATHER API - SCHEMA REPORT")
            report.append("=" * 80)
            report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report.append(f"Database: {self.database_url.split('@')[1] if '@' in self.database_url else 'localhost'}")
            report.append(f"Total Tables: {len(tables)}")
            report.append("")
            
            total_columns = 0
            total_indexes = 0
            total_fks = 0
            
            for table_name in sorted(tables):
                report.append(f"TABLE: {table_name}")
                report.append("-" * 40)
                
                # Columns
                columns = inspector.get_columns(table_name)
                report.append(f"  Columns ({len(columns)}):")
                for col in columns:
                    col_type = str(col['type'])
                    nullable = "NULL" if col['nullable'] else "NOT NULL"
                    default = f" DEFAULT {col['default']}" if col['default'] else ""
                    report.append(f"    - {col['name']}: {col_type} {nullable}{default}")
                total_columns += len(columns)
                
                # Indexes
                indexes = inspector.get_indexes(table_name)
                if indexes:
                    report.append(f"  Indexes ({len(indexes)}):")
                    for idx in indexes:
                        unique = "UNIQUE " if idx['unique'] else ""
                        report.append(f"    - {unique}{idx['name']}: {idx['column_names']}")
                total_indexes += len(indexes)
                
                # Foreign Keys
                fks = inspector.get_foreign_keys(table_name)
                if fks:
                    report.append(f"  Foreign Keys ({len(fks)}):")
                    for fk in fks:
                        report.append(f"    - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
                total_fks += len(fks)
                
                report.append("")
            
            # Summary
            report.append("SUMMARY:")
            report.append(f"  Total Tables: {len(tables)}")
            report.append(f"  Total Columns: {total_columns}")
            report.append(f"  Total Indexes: {total_indexes}")
            report.append(f"  Total Foreign Keys: {total_fks}")
            report.append("")
            report.append("STATUS: ✅ Schema Generated Successfully")
            report.append("=" * 80)
            
            report_text = "\n".join(report)
            
            # Save to file
            with open("schema_report.txt", "w") as f:
                f.write(report_text)
            
            logger.info("✅ Schema report generated: schema_report.txt")
            return report_text
            
        except Exception as e:
            logger.error(f"❌ Failed to generate schema report: {e}")
            return ""
    
    def run(self) -> bool:
        """
        Main execution method
        """
        success = True
        
        try:
            logger.info("🚀 Starting Skycaster Schema Generator")
            logger.info(f"Mode: {self.mode.upper()}")
            
            # Connect to database
            if not self.connect_database():
                return False
            
            # Enable extensions
            if not self.enable_extensions():
                success = False
            
            # Create enums
            if not self.create_enums():
                success = False
            
            # Handle different modes
            if self.mode == "recreate":
                if not self.drop_tables():
                    success = False
            
            if self.mode in ["create", "recreate"]:
                # Create tables
                if not self.create_tables():
                    success = False
                
                # Insert initial data
                if not self.insert_initial_data():
                    success = False
            
            # Always validate
            if not self.validate_schema():
                success = False
            
            # Generate report
            self.generate_schema_report()
            
            if success:
                logger.info("🎉 Schema generation completed successfully!")
            else:
                logger.error("❌ Schema generation completed with errors")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Unexpected error during schema generation: {e}")
            return False
        
        finally:
            # Cleanup
            if self.session:
                self.session.close()
            if self.engine:
                self.engine.dispose()
            logger.info("🔌 Database connection closed")

def main():
    """
    Main entry point
    """
    parser = argparse.ArgumentParser(description="Skycaster Weather API Schema Generator")
    parser.add_argument(
        "--database-url",
        default=os.getenv("SCHEMA_DB_URL"),
        help="Database URL (default: SCHEMA_DB_URL environment variable)"
    )
    parser.add_argument(
        "--mode",
        default="create",
        choices=["create", "recreate", "validate"],
        help="Operation mode (default: create)"
    )
    parser.add_argument(
        "--validate",
        default=True,
        type=bool,
        help="Validate schema after creation (default: True)"
    )
    
    args = parser.parse_args()
    
    # Check database URL
    if not args.database_url:
        print("❌ Error: Database URL is required")
        print("Set SCHEMA_DB_URL environment variable or use --database-url parameter")
        print("\nExample:")
        print("export SCHEMA_DB_URL='postgresql://user:password@localhost:5432/skycaster_db'")
        print("python schema_generator.py")
        sys.exit(1)
    
    # Validate database URL format
    if not args.database_url.startswith("postgresql://"):
        print("❌ Error: Only PostgreSQL databases are supported")
        print("Database URL must start with 'postgresql://'")
        sys.exit(1)
    
    # Run schema generator
    generator = SchemaGenerator(args.database_url, args.mode)
    success = generator.run()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()