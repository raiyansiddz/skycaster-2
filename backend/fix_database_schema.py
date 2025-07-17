#!/usr/bin/env python3
"""
Fix database schema by manually creating missing tables
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app.core.database import engine
from sqlalchemy import text

def fix_database_schema():
    """Create missing tables manually"""
    try:
        print("🔧 Creating missing core tables...")
        
        with engine.begin() as conn:
            # Create users table
            create_users_sql = """
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR NOT NULL PRIMARY KEY,
                email VARCHAR NOT NULL,
                hashed_password VARCHAR NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                is_verified BOOLEAN DEFAULT FALSE,
                role userrole DEFAULT 'USER',
                first_name VARCHAR,
                last_name VARCHAR,
                company VARCHAR,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE,
                last_login TIMESTAMP WITH TIME ZONE,
                email_verification_token VARCHAR,
                email_verification_sent_at TIMESTAMP WITH TIME ZONE,
                password_reset_token VARCHAR,
                password_reset_sent_at TIMESTAMP WITH TIME ZONE
            );
            """
            
            create_users_index_sql = """
            CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);
            """
            
            # Create api_keys table
            create_api_keys_sql = """
            CREATE TABLE IF NOT EXISTS api_keys (
                id VARCHAR NOT NULL PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                name VARCHAR NOT NULL,
                key VARCHAR NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                total_requests INTEGER DEFAULT 0,
                last_used TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
            
            create_api_keys_index_sql = """
            CREATE UNIQUE INDEX IF NOT EXISTS ix_api_keys_key ON api_keys (key);
            """
            
            # Create subscriptions table
            create_subscriptions_sql = """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id VARCHAR NOT NULL PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                plan subscriptionplan NOT NULL,
                status subscriptionstatus NOT NULL,
                stripe_subscription_id VARCHAR,
                stripe_customer_id VARCHAR,
                stripe_price_id VARCHAR,
                current_period_start TIMESTAMP WITH TIME ZONE,
                current_period_end TIMESTAMP WITH TIME ZONE,
                cancel_at_period_end BOOLEAN DEFAULT FALSE,
                current_month_usage INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
            
            # Create support_tickets table
            create_support_tickets_sql = """
            CREATE TABLE IF NOT EXISTS support_tickets (
                id VARCHAR NOT NULL PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                title VARCHAR NOT NULL,
                description TEXT NOT NULL,
                status ticketstatus NOT NULL,
                priority ticketpriority NOT NULL,
                assigned_to VARCHAR,
                resolution TEXT,
                resolved_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
            
            # Create invoices table
            create_invoices_sql = """
            CREATE TABLE IF NOT EXISTS invoices (
                id VARCHAR NOT NULL PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                subscription_id VARCHAR,
                invoice_number VARCHAR NOT NULL,
                status invoicestatus NOT NULL,
                stripe_invoice_id VARCHAR,
                stripe_payment_intent_id VARCHAR,
                subtotal INTEGER NOT NULL,
                tax INTEGER,
                total INTEGER NOT NULL,
                currency VARCHAR(3) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE,
                due_date TIMESTAMP WITH TIME ZONE,
                paid_at TIMESTAMP WITH TIME ZONE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
            
            # Create usage_logs table
            create_usage_logs_sql = """
            CREATE TABLE IF NOT EXISTS usage_logs (
                id VARCHAR NOT NULL PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                api_key_id VARCHAR NOT NULL,
                endpoint VARCHAR NOT NULL,
                method VARCHAR NOT NULL,
                request_data TEXT,
                response_status INTEGER NOT NULL,
                response_time FLOAT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                ip_address VARCHAR,
                user_agent VARCHAR,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (api_key_id) REFERENCES api_keys(id)
            );
            """
            
            # Execute all table creation statements
            conn.execute(text(create_users_sql))
            conn.execute(text(create_users_index_sql))
            print("✅ Created users table")
            
            conn.execute(text(create_api_keys_sql))
            conn.execute(text(create_api_keys_index_sql))
            print("✅ Created api_keys table")
            
            conn.execute(text(create_subscriptions_sql))
            print("✅ Created subscriptions table")
            
            conn.execute(text(create_support_tickets_sql))
            print("✅ Created support_tickets table")
            
            conn.execute(text(create_invoices_sql))
            print("✅ Created invoices table")
            
            conn.execute(text(create_usage_logs_sql))
            print("✅ Created usage_logs table")
            
            # Verify all tables exist
            result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"))
            tables = [row[0] for row in result]
            print(f"✅ All tables created: {tables}")
            
        print("🎉 Database schema fixed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to fix database schema: {e}")
        return False

if __name__ == "__main__":
    success = fix_database_schema()
    sys.exit(0 if success else 1)