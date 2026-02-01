-- ============================================
-- Mount Abu E-Token System - Database Init
-- ============================================
-- This script runs automatically when PostgreSQL
-- container is first initialized.
-- ============================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- Grant permissions (if using different user)
GRANT ALL PRIVILEGES ON DATABASE mountabu_etoken TO etoken_user;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Mount Abu E-Token database initialized successfully!';
END $$;
