-- ===============================================
-- SKYCASTER WEATHER API SYSTEM - COMPLETE SQL SCHEMA
-- ===============================================
-- This file contains the complete database schema for the Skycaster Weather API system
-- Compatible with PostgreSQL and other SQL databases
-- Generated on 2025-07-19

-- Enable UUID extension for PostgreSQL
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===============================================
-- ENUMS AND TYPES
-- ===============================================

-- User role enum
CREATE TYPE user_role AS ENUM ('user', 'admin');

-- Subscription plan enum  
CREATE TYPE subscription_plan AS ENUM ('free', 'developer', 'business', 'enterprise');

-- Subscription status enum
CREATE TYPE subscription_status AS ENUM ('active', 'cancelled', 'past_due', 'incomplete', 'trialing');

-- Ticket status enum
CREATE TYPE ticket_status AS ENUM ('open', 'in_progress', 'resolved', 'closed');

-- Ticket priority enum
CREATE TYPE ticket_priority AS ENUM ('low', 'medium', 'high', 'urgent');

-- Invoice status enum
CREATE TYPE invoice_status AS ENUM ('draft', 'open', 'paid', 'void', 'uncollectible');

-- ===============================================
-- CORE USER MANAGEMENT TABLES
-- ===============================================

-- Users table - Core user management
CREATE TABLE users (
    id VARCHAR PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    role user_role DEFAULT 'user',
    
    -- Profile fields
    first_name VARCHAR,
    last_name VARCHAR,
    company VARCHAR,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    last_login TIMESTAMP WITH TIME ZONE,
    
    -- Email verification
    email_verification_token VARCHAR,
    email_verification_sent_at TIMESTAMP WITH TIME ZONE,
    
    -- Password reset
    password_reset_token VARCHAR,
    password_reset_sent_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for users table
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);

-- ===============================================
-- API KEY MANAGEMENT
-- ===============================================

-- API Keys table - Manages user API keys
CREATE TABLE api_keys (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    key VARCHAR UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Usage tracking
    total_requests INTEGER DEFAULT 0,
    last_used TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create indexes for api_keys table
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_key ON api_keys(key);
CREATE INDEX idx_api_keys_is_active ON api_keys(is_active);

-- ===============================================
-- SUBSCRIPTION AND BILLING
-- ===============================================

-- Subscriptions table - User subscription management
CREATE TABLE subscriptions (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    
    -- Subscription details
    plan subscription_plan NOT NULL DEFAULT 'free',
    status subscription_status NOT NULL DEFAULT 'active',
    
    -- Stripe details
    stripe_subscription_id VARCHAR,
    stripe_customer_id VARCHAR,
    stripe_price_id VARCHAR,
    
    -- Billing
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    
    -- Usage tracking
    current_month_usage INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create indexes for subscriptions table
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_plan ON subscriptions(plan);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);

-- Invoices table - Invoice management
CREATE TABLE invoices (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    subscription_id VARCHAR,
    
    -- Invoice details
    invoice_number VARCHAR UNIQUE NOT NULL,
    status invoice_status NOT NULL DEFAULT 'draft',
    
    -- Stripe details
    stripe_invoice_id VARCHAR,
    stripe_payment_intent_id VARCHAR,
    
    -- Amounts (in cents)
    subtotal INTEGER NOT NULL,
    tax INTEGER DEFAULT 0,
    total INTEGER NOT NULL,
    amount_paid INTEGER DEFAULT 0,
    amount_due INTEGER NOT NULL,
    
    -- Dates
    invoice_date TIMESTAMP WITH TIME ZONE NOT NULL,
    due_date TIMESTAMP WITH TIME ZONE NOT NULL,
    paid_at TIMESTAMP WITH TIME ZONE,
    
    -- Billing period
    period_start TIMESTAMP WITH TIME ZONE,
    period_end TIMESTAMP WITH TIME ZONE,
    
    -- Line items (JSON format)
    line_items JSON,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE SET NULL
);

-- Create indexes for invoices table
CREATE INDEX idx_invoices_user_id ON invoices(user_id);
CREATE INDEX idx_invoices_subscription_id ON invoices(subscription_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_invoice_number ON invoices(invoice_number);

-- ===============================================
-- WEATHER API CONFIGURATION
-- ===============================================

-- Pricing Configuration table - Dynamic pricing for weather variables
CREATE TABLE pricing_config (
    id VARCHAR PRIMARY KEY,
    
    -- Pricing details
    variable_name VARCHAR(100) UNIQUE NOT NULL,
    endpoint_type VARCHAR(20) NOT NULL,  -- omega, nova, arc
    base_price FLOAT NOT NULL DEFAULT 1.0,
    currency VARCHAR(5) NOT NULL DEFAULT 'INR',
    
    -- Tax configuration
    tax_rate FLOAT NOT NULL DEFAULT 0.0,
    tax_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    hsn_sac_code VARCHAR(20),
    
    -- Plan-based overrides
    free_plan_price FLOAT,
    developer_plan_price FLOAT,
    business_plan_price FLOAT,
    enterprise_plan_price FLOAT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,
    
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Create indexes for pricing_config table
CREATE INDEX idx_pricing_config_variable_name ON pricing_config(variable_name);
CREATE INDEX idx_pricing_config_endpoint_type ON pricing_config(endpoint_type);
CREATE INDEX idx_pricing_config_is_active ON pricing_config(is_active);

-- Currency Configuration table - Multi-currency support
CREATE TABLE currency_config (
    id VARCHAR PRIMARY KEY,
    
    -- Currency details
    currency_code VARCHAR(5) UNIQUE NOT NULL,
    currency_symbol VARCHAR(10) NOT NULL,
    currency_name VARCHAR(50) NOT NULL,
    
    -- Country mapping
    country_codes TEXT,  -- JSON array of country codes
    
    -- Exchange rate (base currency INR)
    exchange_rate FLOAT NOT NULL DEFAULT 1.0,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for currency_config table
CREATE INDEX idx_currency_config_currency_code ON currency_config(currency_code);
CREATE INDEX idx_currency_config_is_active ON currency_config(is_active);

-- Variable Mapping table - Maps variables to endpoints
CREATE TABLE variable_mapping (
    id VARCHAR PRIMARY KEY,
    
    -- Variable details
    variable_name VARCHAR(100) UNIQUE NOT NULL,
    endpoint_type VARCHAR(20) NOT NULL,  -- omega, nova, arc
    endpoint_url VARCHAR(200) NOT NULL,
    
    -- Variable metadata
    description TEXT,
    unit VARCHAR(20),
    data_type VARCHAR(20) NOT NULL DEFAULT 'float',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for variable_mapping table
CREATE INDEX idx_variable_mapping_variable_name ON variable_mapping(variable_name);
CREATE INDEX idx_variable_mapping_endpoint_type ON variable_mapping(endpoint_type);
CREATE INDEX idx_variable_mapping_is_active ON variable_mapping(is_active);

-- ===============================================
-- USAGE AND LOGGING
-- ===============================================

-- Usage Logs table - API usage tracking
CREATE TABLE usage_logs (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    api_key_id VARCHAR NOT NULL,
    
    -- Request details
    endpoint VARCHAR NOT NULL,
    method VARCHAR NOT NULL,
    request_params JSON,
    request_headers JSON,
    
    -- Response details
    response_status INTEGER NOT NULL,
    response_size INTEGER,  -- in bytes
    response_time FLOAT,  -- in seconds
    success BOOLEAN NOT NULL,
    
    -- Location and context
    ip_address VARCHAR,
    user_agent VARCHAR,
    location VARCHAR,  -- Weather location requested
    
    -- Billing
    cost FLOAT DEFAULT 0.0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE
);

-- Create indexes for usage_logs table
CREATE INDEX idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX idx_usage_logs_api_key_id ON usage_logs(api_key_id);
CREATE INDEX idx_usage_logs_endpoint ON usage_logs(endpoint);
CREATE INDEX idx_usage_logs_created_at ON usage_logs(created_at);

-- Weather Requests table - Detailed weather API request logging
CREATE TABLE weather_requests (
    id VARCHAR PRIMARY KEY,
    
    -- Request details
    user_id VARCHAR NOT NULL,
    api_key_id VARCHAR NOT NULL,
    
    -- Request parameters
    locations TEXT NOT NULL,  -- JSON array of [lat, lon] pairs
    variables TEXT NOT NULL,  -- JSON array of variable names
    timestamp VARCHAR(50) NOT NULL,
    timezone VARCHAR(50) NOT NULL DEFAULT 'Asia/Kolkata',
    
    -- Response details
    endpoints_called TEXT,  -- JSON array of endpoints called
    response_status INTEGER NOT NULL,
    response_time FLOAT NOT NULL,
    success BOOLEAN NOT NULL,
    
    -- Pricing details
    total_cost FLOAT NOT NULL DEFAULT 0.0,
    currency VARCHAR(5) NOT NULL DEFAULT 'INR',
    tax_applied FLOAT NOT NULL DEFAULT 0.0,
    final_amount FLOAT NOT NULL DEFAULT 0.0,
    
    -- Request metadata
    ip_address VARCHAR(50),
    user_agent VARCHAR(500),
    country_code VARCHAR(5),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE
);

-- Create indexes for weather_requests table
CREATE INDEX idx_weather_requests_user_id ON weather_requests(user_id);
CREATE INDEX idx_weather_requests_api_key_id ON weather_requests(api_key_id);
CREATE INDEX idx_weather_requests_created_at ON weather_requests(created_at);

-- ===============================================
-- ADVANCED AUDIT AND SECURITY LOGGING
-- ===============================================

-- Audit Logs table - Comprehensive audit logging
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Request Information
    request_id VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    endpoint VARCHAR(500) NOT NULL,
    full_url TEXT,
    
    -- User Context
    user_id UUID,
    user_email VARCHAR(255),
    api_key_id UUID,
    session_id VARCHAR(255),
    
    -- Request Details
    request_headers JSON,
    request_body TEXT,
    request_params JSON,
    request_size INTEGER DEFAULT 0,
    
    -- Response Details
    response_status_code INTEGER,
    response_headers JSON,
    response_body TEXT,
    response_size INTEGER DEFAULT 0,
    
    -- Performance Metrics
    processing_time_ms FLOAT,
    database_query_count INTEGER DEFAULT 0,
    database_query_time_ms FLOAT DEFAULT 0.0,
    
    -- Network Information
    client_ip VARCHAR(45),  -- IPv6 support
    user_agent TEXT,
    referer TEXT,
    
    -- Geographic Information
    country VARCHAR(2),
    region VARCHAR(100),
    city VARCHAR(100),
    
    -- Authentication & Security
    auth_method VARCHAR(50),  -- jwt, api_key, none
    auth_success BOOLEAN,
    rate_limit_applied BOOLEAN DEFAULT FALSE,
    rate_limit_remaining INTEGER,
    
    -- Timestamps
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Classification
    log_level VARCHAR(20) DEFAULT 'INFO',  -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    activity_type VARCHAR(50),  -- auth, api_call, admin, billing, etc.
    
    -- Additional Context
    extra_metadata JSON,
    tags JSON  -- Array of tags for categorization
);

-- Create indexes for audit_logs table
CREATE INDEX idx_audit_logs_request_id ON audit_logs(request_id);
CREATE INDEX idx_audit_logs_endpoint ON audit_logs(endpoint);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_user_email ON audit_logs(user_email);
CREATE INDEX idx_audit_logs_api_key_id ON audit_logs(api_key_id);
CREATE INDEX idx_audit_logs_session_id ON audit_logs(session_id);
CREATE INDEX idx_audit_logs_client_ip ON audit_logs(client_ip);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_logs_log_level ON audit_logs(log_level);
CREATE INDEX idx_audit_logs_activity_type ON audit_logs(activity_type);

-- Security Events table - Security-specific logging
CREATE TABLE security_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Event Classification
    event_type VARCHAR(100) NOT NULL,  -- login_failure, rate_limit_exceeded, etc.
    severity VARCHAR(20) DEFAULT 'LOW',  -- LOW, MEDIUM, HIGH, CRITICAL
    
    -- User Context
    user_id UUID,
    user_email VARCHAR(255),
    attempted_email VARCHAR(255),  -- For failed logins
    
    -- Request Context
    request_id VARCHAR(255),
    client_ip VARCHAR(45),
    user_agent TEXT,
    endpoint VARCHAR(500),
    
    -- Event Details
    description TEXT NOT NULL,
    details JSON,
    
    -- Timestamps
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Response Actions
    action_taken VARCHAR(100),  -- blocked, flagged, allowed, etc.
    automatic_response BOOLEAN DEFAULT FALSE
);

-- Create indexes for security_events table
CREATE INDEX idx_security_events_event_type ON security_events(event_type);
CREATE INDEX idx_security_events_severity ON security_events(severity);
CREATE INDEX idx_security_events_user_id ON security_events(user_id);
CREATE INDEX idx_security_events_user_email ON security_events(user_email);
CREATE INDEX idx_security_events_attempted_email ON security_events(attempted_email);
CREATE INDEX idx_security_events_request_id ON security_events(request_id);
CREATE INDEX idx_security_events_client_ip ON security_events(client_ip);
CREATE INDEX idx_security_events_timestamp ON security_events(timestamp);

-- User Activities table - User behavior tracking
CREATE TABLE user_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- User Context
    user_id UUID NOT NULL,
    session_id VARCHAR(255),
    
    -- Activity Details
    activity_type VARCHAR(100) NOT NULL,  -- login, api_call, subscription_change, etc.
    activity_name VARCHAR(255) NOT NULL,
    activity_description TEXT,
    
    -- Context
    endpoint VARCHAR(500),
    request_id VARCHAR(255),
    
    -- Metadata
    activity_data JSON,
    
    -- Performance
    duration_ms FLOAT,
    
    -- Timestamps
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Success/Failure
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

-- Create indexes for user_activities table
CREATE INDEX idx_user_activities_user_id ON user_activities(user_id);
CREATE INDEX idx_user_activities_session_id ON user_activities(session_id);
CREATE INDEX idx_user_activities_activity_type ON user_activities(activity_type);
CREATE INDEX idx_user_activities_request_id ON user_activities(request_id);
CREATE INDEX idx_user_activities_timestamp ON user_activities(timestamp);

-- Performance Metrics table - System performance tracking
CREATE TABLE performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Metric Classification
    metric_type VARCHAR(100) NOT NULL,  -- api_response_time, db_query_time, etc.
    metric_name VARCHAR(255) NOT NULL,
    
    -- Values
    value FLOAT NOT NULL,
    unit VARCHAR(50) NOT NULL,  -- ms, seconds, count, bytes, etc.
    
    -- Context
    endpoint VARCHAR(500),
    user_id UUID,
    request_id VARCHAR(255),
    
    -- Additional Data
    extra_metadata JSON,
    tags JSON,
    
    -- Timestamps
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance_metrics table
CREATE INDEX idx_performance_metrics_metric_type ON performance_metrics(metric_type);
CREATE INDEX idx_performance_metrics_metric_name ON performance_metrics(metric_name);
CREATE INDEX idx_performance_metrics_endpoint ON performance_metrics(endpoint);
CREATE INDEX idx_performance_metrics_user_id ON performance_metrics(user_id);
CREATE INDEX idx_performance_metrics_request_id ON performance_metrics(request_id);
CREATE INDEX idx_performance_metrics_timestamp ON performance_metrics(timestamp);

-- ===============================================
-- SUPPORT SYSTEM
-- ===============================================

-- Support Tickets table - Customer support management
CREATE TABLE support_tickets (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    
    -- Ticket details
    title VARCHAR NOT NULL,
    description TEXT NOT NULL,
    status ticket_status NOT NULL DEFAULT 'open',
    priority ticket_priority NOT NULL DEFAULT 'medium',
    
    -- Assignment
    assigned_to VARCHAR,  -- Admin user ID
    
    -- Resolution
    resolution TEXT,
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create indexes for support_tickets table
CREATE INDEX idx_support_tickets_user_id ON support_tickets(user_id);
CREATE INDEX idx_support_tickets_status ON support_tickets(status);
CREATE INDEX idx_support_tickets_priority ON support_tickets(priority);
CREATE INDEX idx_support_tickets_assigned_to ON support_tickets(assigned_to);

-- ===============================================
-- INITIAL DATA INSERTS
-- ===============================================

-- Insert default pricing configuration
INSERT INTO pricing_config (id, variable_name, endpoint_type, base_price, currency, tax_rate, tax_enabled, is_active) VALUES
('pc_001', 'ambient_temp(K)', 'omega', 1.18, 'INR', 18.0, true, true),
('pc_002', 'wind_10m', 'omega', 1.18, 'INR', 18.0, true, true),
('pc_003', 'wind_100m', 'omega', 1.18, 'INR', 18.0, true, true),
('pc_004', 'relative_humidity(%)', 'omega', 1.18, 'INR', 18.0, true, true),
('pc_005', 'temperature(K)', 'nova', 1.18, 'INR', 18.0, true, true),
('pc_006', 'surface_pressure(Pa)', 'nova', 1.18, 'INR', 18.0, true, true),
('pc_007', 'cumulus_precipitation(mm)', 'nova', 1.18, 'INR', 18.0, true, true),
('pc_008', 'ghi(W/m2)', 'nova', 1.18, 'INR', 18.0, true, true),
('pc_009', 'ghi_farms(W/m2)', 'nova', 1.18, 'INR', 18.0, true, true),
('pc_010', 'clear_sky_ghi_farms(W/m2)', 'nova', 1.18, 'INR', 18.0, true, true),
('pc_011', 'albedo', 'nova', 1.18, 'INR', 18.0, true, true),
('pc_012', 'ct', 'arc', 1.18, 'INR', 18.0, true, true),
('pc_013', 'pc', 'arc', 1.18, 'INR', 18.0, true, true),
('pc_014', 'pcph', 'arc', 1.18, 'INR', 18.0, true, true);

-- Insert variable mapping configuration
INSERT INTO variable_mapping (id, variable_name, endpoint_type, endpoint_url, description, unit, data_type, is_active) VALUES
('vm_001', 'ambient_temp(K)', 'omega', 'https://apidelta.skycaster.in/forecast/multiple/omega', 'Ambient temperature', 'Kelvin', 'float', true),
('vm_002', 'wind_10m', 'omega', 'https://apidelta.skycaster.in/forecast/multiple/omega', 'Wind speed at 10m height', 'm/s', 'float', true),
('vm_003', 'wind_100m', 'omega', 'https://apidelta.skycaster.in/forecast/multiple/omega', 'Wind speed at 100m height', 'm/s', 'float', true),
('vm_004', 'relative_humidity(%)', 'omega', 'https://apidelta.skycaster.in/forecast/multiple/omega', 'Relative humidity percentage', '%', 'float', true),
('vm_005', 'temperature(K)', 'nova', 'https://apidelta.skycaster.in/forecast/multiple/nova', 'Temperature', 'Kelvin', 'float', true),
('vm_006', 'surface_pressure(Pa)', 'nova', 'https://apidelta.skycaster.in/forecast/multiple/nova', 'Surface pressure', 'Pascal', 'float', true),
('vm_007', 'cumulus_precipitation(mm)', 'nova', 'https://apidelta.skycaster.in/forecast/multiple/nova', 'Cumulus precipitation', 'mm', 'float', true),
('vm_008', 'ghi(W/m2)', 'nova', 'https://apidelta.skycaster.in/forecast/multiple/nova', 'Global horizontal irradiance', 'W/m2', 'float', true),
('vm_009', 'ghi_farms(W/m2)', 'nova', 'https://apidelta.skycaster.in/forecast/multiple/nova', 'GHI for solar farms', 'W/m2', 'float', true),
('vm_010', 'clear_sky_ghi_farms(W/m2)', 'nova', 'https://apidelta.skycaster.in/forecast/multiple/nova', 'Clear sky GHI for farms', 'W/m2', 'float', true),
('vm_011', 'albedo', 'nova', 'https://apidelta.skycaster.in/forecast/multiple/nova', 'Surface albedo', 'ratio', 'float', true),
('vm_012', 'ct', 'arc', 'https://apidelta.skycaster.in/forecast/multiple/arc', 'Cloud type', 'categorical', 'string', true),
('vm_013', 'pc', 'arc', 'https://apidelta.skycaster.in/forecast/multiple/arc', 'Precipitation category', 'categorical', 'string', true),
('vm_014', 'pcph', 'arc', 'https://apidelta.skycaster.in/forecast/multiple/arc', 'Precipitation phase', 'categorical', 'string', true);

-- Insert currency configuration
INSERT INTO currency_config (id, currency_code, currency_symbol, currency_name, exchange_rate, is_active) VALUES
('cc_001', 'INR', '₹', 'Indian Rupee', 1.0, true),
('cc_002', 'USD', '$', 'US Dollar', 0.012, true),
('cc_003', 'EUR', '€', 'Euro', 0.011, true),
('cc_004', 'GBP', '£', 'British Pound', 0.0095, true);

-- ===============================================
-- NOTES AND DOCUMENTATION
-- ===============================================

-- SCHEMA VERSION: 1.0
-- CREATED: 2025-07-19
-- SYSTEM: Skycaster Weather API Platform
-- 
-- FEATURES INCLUDED:
-- ✅ User Management & Authentication
-- ✅ API Key Management
-- ✅ Subscription & Billing System
-- ✅ Weather API Configuration & Pricing
-- ✅ Usage Tracking & Analytics
-- ✅ Advanced Audit Logging
-- ✅ Security Event Monitoring
-- ✅ Performance Metrics
-- ✅ Support Ticket System
-- ✅ Multi-currency Support
-- ✅ Variable-based Dynamic Pricing
-- 
-- COMPATIBILITY: PostgreSQL, MySQL (with minor modifications), SQLite (with enum adjustments)
--
-- DEPLOYMENT NOTES:
-- 1. Enable UUID extension for PostgreSQL: CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- 2. Adjust enum types for other databases if needed
-- 3. Configure proper timezone settings
-- 4. Set up appropriate backup and archival policies for audit logs
-- 5. Consider partitioning large tables (audit_logs, user_activities) by date for performance
--
-- SECURITY CONSIDERATIONS:
-- 1. All sensitive data should be encrypted at rest
-- 2. API keys should be hashed before storage
-- 3. Implement proper access controls and row-level security
-- 4. Regular audit log analysis for security monitoring
-- 5. Implement data retention policies for compliance