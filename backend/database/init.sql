-- SKYCASTER Database Initialization Script
-- This script creates all the necessary tables and indexes for the SKYCASTER platform

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create users table
\i schemas/user.sql

-- Create api_keys table
\i schemas/api_key.sql

-- Create subscriptions table
\i schemas/subscription.sql

-- Create usage_logs table
\i schemas/usage_log.sql

-- Create invoices table
\i schemas/invoice.sql

-- Create support_tickets table
\i schemas/support_ticket.sql

-- Create admin user
INSERT INTO users (
    id, 
    email, 
    hashed_password, 
    is_active, 
    is_verified, 
    role,
    first_name,
    last_name,
    created_at
) VALUES (
    'admin-' || uuid_generate_v4()::text,
    'admin@skycaster.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj7YcyYqP8Q2',  -- admin123
    TRUE,
    TRUE,
    'admin',
    'Admin',
    'User',
    NOW()
) ON CONFLICT (email) DO NOTHING;

-- Create sample subscription plans data
INSERT INTO subscriptions (
    id,
    user_id,
    plan,
    status,
    current_period_start,
    current_period_end,
    current_month_usage,
    created_at
) 
SELECT 
    'sub-' || uuid_generate_v4()::text,
    id,
    'free',
    'active',
    NOW(),
    NOW() + INTERVAL '1 month',
    0,
    NOW()
FROM users 
WHERE email = 'admin@skycaster.com'
ON CONFLICT DO NOTHING;

-- Create initial API key for admin
INSERT INTO api_keys (
    id,
    user_id,
    name,
    key,
    is_active,
    total_requests,
    created_at
)
SELECT
    'key-' || uuid_generate_v4()::text,
    id,
    'Admin Default Key',
    'sk_admin_' || substr(md5(random()::text), 1, 32),
    TRUE,
    0,
    NOW()
FROM users
WHERE email = 'admin@skycaster.com'
ON CONFLICT DO NOTHING;

-- Create views for analytics
CREATE OR REPLACE VIEW v_user_usage_summary AS
SELECT 
    u.id as user_id,
    u.email,
    u.role,
    s.plan,
    s.status as subscription_status,
    s.current_month_usage,
    COUNT(ul.id) as total_requests,
    COUNT(CASE WHEN ul.success = TRUE THEN 1 END) as successful_requests,
    COUNT(CASE WHEN ul.success = FALSE THEN 1 END) as failed_requests,
    SUM(ul.cost) as total_cost,
    MAX(ul.created_at) as last_request_at
FROM users u
LEFT JOIN subscriptions s ON u.id = s.user_id
LEFT JOIN usage_logs ul ON u.id = ul.user_id
GROUP BY u.id, u.email, u.role, s.plan, s.status, s.current_month_usage;

CREATE OR REPLACE VIEW v_api_key_usage AS
SELECT
    ak.id as api_key_id,
    ak.name as api_key_name,
    ak.user_id,
    u.email as user_email,
    ak.total_requests,
    ak.last_used,
    ak.is_active,
    COUNT(ul.id) as logged_requests,
    SUM(ul.cost) as total_cost
FROM api_keys ak
JOIN users u ON ak.user_id = u.id
LEFT JOIN usage_logs ul ON ak.id = ul.api_key_id
GROUP BY ak.id, ak.name, ak.user_id, u.email, ak.total_requests, ak.last_used, ak.is_active;

CREATE OR REPLACE VIEW v_monthly_usage_stats AS
SELECT
    DATE_TRUNC('month', ul.created_at) as month,
    COUNT(*) as total_requests,
    COUNT(CASE WHEN ul.success = TRUE THEN 1 END) as successful_requests,
    COUNT(CASE WHEN ul.success = FALSE THEN 1 END) as failed_requests,
    COUNT(DISTINCT ul.user_id) as unique_users,
    SUM(ul.cost) as total_cost,
    AVG(ul.response_time) as avg_response_time
FROM usage_logs ul
GROUP BY DATE_TRUNC('month', ul.created_at)
ORDER BY month DESC;

-- Create functions for usage tracking
CREATE OR REPLACE FUNCTION update_api_key_usage()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE api_keys 
    SET 
        total_requests = total_requests + 1,
        last_used = NEW.created_at
    WHERE id = NEW.api_key_id;
    
    UPDATE subscriptions 
    SET current_month_usage = current_month_usage + 1
    WHERE user_id = NEW.user_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for usage tracking
DROP TRIGGER IF EXISTS trigger_update_api_key_usage ON usage_logs;
CREATE TRIGGER trigger_update_api_key_usage
    AFTER INSERT ON usage_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_api_key_usage();

-- Create function for monthly usage reset
CREATE OR REPLACE FUNCTION reset_monthly_usage()
RETURNS void AS $$
BEGIN
    UPDATE subscriptions 
    SET current_month_usage = 0
    WHERE current_period_end < NOW();
END;
$$ LANGUAGE plpgsql;

-- Show completion message
SELECT 'SKYCASTER database initialization completed successfully!' as message;