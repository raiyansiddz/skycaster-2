-- Usage logs table schema
CREATE TABLE IF NOT EXISTS usage_logs (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    api_key_id VARCHAR NOT NULL,
    
    -- Request details
    endpoint VARCHAR NOT NULL,
    method VARCHAR NOT NULL,
    request_params JSONB,
    request_headers JSONB,
    
    -- Response details
    response_status INTEGER NOT NULL,
    response_size INTEGER,
    response_time FLOAT,
    success BOOLEAN NOT NULL,
    
    -- Location and context
    ip_address VARCHAR,
    user_agent VARCHAR,
    location VARCHAR,
    
    -- Billing
    cost FLOAT DEFAULT 0.0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Foreign key constraints
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_api_key_id ON usage_logs(api_key_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_endpoint ON usage_logs(endpoint);
CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at ON usage_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_usage_logs_success ON usage_logs(success);
CREATE INDEX IF NOT EXISTS idx_usage_logs_location ON usage_logs(location);

-- Partitioning by month for better performance
CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at_month ON usage_logs(date_trunc('month', created_at));