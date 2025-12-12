-- =====================================================
-- Recruitment Management System - Database Schema
-- PostgreSQL Database Schema
-- =====================================================

-- Drop existing tables if recreating
DROP TABLE IF EXISTS vacancy_recommendations CASCADE;
DROP TABLE IF EXISTS screening_history CASCADE;
DROP TABLE IF EXISTS screening_results CASCADE;
DROP TABLE IF EXISTS email_logs CASCADE;
DROP TABLE IF EXISTS analytics_metrics CASCADE;
DROP TABLE IF EXISTS job_descriptions CASCADE;
DROP TABLE IF EXISTS candidates CASCADE;

-- =====================================================
-- 1. CANDIDATES TABLE
-- =====================================================
CREATE TABLE candidates (
    id SERIAL PRIMARY KEY,
    
    -- Basic Information
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    
    -- Parsed Resume Data
    summary TEXT,
    education TEXT,
    experience TEXT,
    skills TEXT,
    projects TEXT,
    certifications TEXT,
    others TEXT,
    
    -- Metadata
    source_file VARCHAR(500) NOT NULL,
    resume_file BYTEA,  -- Original resume stored as binary
    text_content TEXT,  -- Full extracted text for searching
    
    -- Embeddings for ML matching
    profile_embedding BYTEA,  -- Serialized numpy array for semantic search
    
    -- Duplicate Detection
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of INTEGER REFERENCES candidates(id),
    duplicate_confidence FLOAT,
    
    -- Experience tracking
    experience_years INTEGER DEFAULT 0,
    
    -- Source tracking
    source_type VARCHAR(50) DEFAULT 'upload',  -- 'email', 'upload', 'manual'
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    CONSTRAINT unique_email UNIQUE(email)
);

CREATE INDEX idx_candidates_email ON candidates(email);
CREATE INDEX idx_candidates_name ON candidates(name);
CREATE INDEX idx_candidates_created_at ON candidates(created_at);
CREATE INDEX idx_candidates_is_duplicate ON candidates(is_duplicate);

-- =====================================================
-- 2. JOB DESCRIPTIONS TABLE
-- =====================================================
CREATE TABLE job_descriptions (
    id SERIAL PRIMARY KEY,
    
    -- Job Details
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    department VARCHAR(100),
    location VARCHAR(100),
    
    -- Requirements
    required_skills TEXT,  -- Comma-separated or JSON
    required_experience_min INTEGER DEFAULT 0,
    required_experience_max INTEGER,
    required_certifications TEXT,
    
    -- Matching Configuration (JSON format)
    matching_config JSONB DEFAULT '{
        "semantic_weight": 0.7,
        "skill_weight": 0.3,
        "experience_weight": 0.0,
        "min_score_threshold": 50,
        "longlist_percentage": 0.5,
        "shortlist_percentage": 0.2
    }'::jsonb,
    
    -- Embeddings
    jd_embedding BYTEA,
    
    -- Status
    status VARCHAR(50) DEFAULT 'active',  -- 'active', 'closed', 'on_hold'
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100)
);

CREATE INDEX idx_jd_status ON job_descriptions(status);
CREATE INDEX idx_jd_created_at ON job_descriptions(created_at);

-- =====================================================
-- 3. SCREENING RESULTS TABLE
-- =====================================================
CREATE TABLE screening_results (
    id SERIAL PRIMARY KEY,
    
    -- Foreign Keys
    job_description_id INTEGER NOT NULL REFERENCES job_descriptions(id) ON DELETE CASCADE,
    candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    
    -- Scores
    final_score FLOAT NOT NULL,
    semantic_score FLOAT,
    skill_match_score FLOAT,
    experience_score FLOAT,
    
    -- Matching Details
    matched_skills TEXT,  -- Skills that matched
    missing_skills TEXT,  -- Skills candidate lacks
    experience_gap INTEGER,  -- Years difference from requirement
    
    -- List Classification
    in_longlist BOOLEAN DEFAULT FALSE,
    in_shortlist BOOLEAN DEFAULT FALSE,
    rank_position INTEGER,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'reviewed', 'rejected', 'hired'
    reviewer_notes TEXT,
    
    -- Timestamps
    screened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewed_by VARCHAR(100),
    
    -- Composite unique constraint
    CONSTRAINT unique_screening UNIQUE(job_description_id, candidate_id)
);

CREATE INDEX idx_screening_jd ON screening_results(job_description_id);
CREATE INDEX idx_screening_candidate ON screening_results(candidate_id);
CREATE INDEX idx_screening_score ON screening_results(final_score DESC);
CREATE INDEX idx_screening_shortlist ON screening_results(in_shortlist);

-- =====================================================
-- 4. SCREENING HISTORY TABLE (Audit Trail)
-- =====================================================
CREATE TABLE screening_history (
    id SERIAL PRIMARY KEY,
    
    job_description_id INTEGER NOT NULL REFERENCES job_descriptions(id),
    
    -- Batch Info
    batch_id VARCHAR(100) NOT NULL,
    total_candidates INTEGER,
    longlist_count INTEGER,
    shortlist_count INTEGER,
    
    -- Performance Metrics
    avg_score FLOAT,
    max_score FLOAT,
    min_score FLOAT,
    processing_time_seconds FLOAT,
    
    -- Configuration Used
    config_snapshot JSONB,
    
    -- Timestamps
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_by VARCHAR(100)
);

CREATE INDEX idx_history_jd ON screening_history(job_description_id);
CREATE INDEX idx_history_executed_at ON screening_history(executed_at);

-- =====================================================
-- 5. VACANCY RECOMMENDATIONS TABLE
-- =====================================================
CREATE TABLE vacancy_recommendations (
    id SERIAL PRIMARY KEY,
    
    -- Foreign Keys
    job_description_id INTEGER NOT NULL REFERENCES job_descriptions(id),
    candidate_id INTEGER NOT NULL REFERENCES candidates(id),
    
    -- Recommendation Score
    recommendation_score FLOAT NOT NULL,
    match_reasoning TEXT,
    
    -- Status Tracking
    was_contacted BOOLEAN DEFAULT FALSE,
    candidate_response VARCHAR(50),  -- 'interested', 'not_interested', 'no_response'
    
    -- Timestamps
    recommended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    contacted_at TIMESTAMP,
    
    CONSTRAINT unique_recommendation UNIQUE(job_description_id, candidate_id)
);

CREATE INDEX idx_recommendations_jd ON vacancy_recommendations(job_description_id);
CREATE INDEX idx_recommendations_score ON vacancy_recommendations(recommendation_score DESC);

-- =====================================================
-- 6. EMAIL LOGS TABLE
-- =====================================================
CREATE TABLE email_logs (
    id SERIAL PRIMARY KEY,
    
    -- Email Details
    email_id VARCHAR(100),
    subject TEXT,
    sender VARCHAR(255),
    received_at TIMESTAMP,
    
    -- Processing
    has_attachment BOOLEAN DEFAULT FALSE,
    attachments_count INTEGER DEFAULT 0,
    resumes_extracted INTEGER DEFAULT 0,
    
    -- Status
    processing_status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'processed', 'failed'
    error_message TEXT,
    
    -- Timestamps
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

CREATE INDEX idx_email_logs_status ON email_logs(processing_status);
CREATE INDEX idx_email_logs_fetched_at ON email_logs(fetched_at);

-- =====================================================
-- 7. ANALYTICS METRICS TABLE
-- =====================================================
CREATE TABLE analytics_metrics (
    id SERIAL PRIMARY KEY,
    
    -- Metric Type
    metric_name VARCHAR(100) NOT NULL,
    metric_category VARCHAR(50),  -- 'candidates', 'screening', 'performance', 'duplicates'
    
    -- Metric Values
    metric_value FLOAT,
    metric_count INTEGER,
    metric_data JSONB,  -- Flexible storage for complex metrics
    
    -- Time Period
    period_start DATE,
    period_end DATE,
    
    -- Timestamps
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_analytics_metric_name ON analytics_metrics(metric_name);
CREATE INDEX idx_analytics_category ON analytics_metrics(metric_category);
CREATE INDEX idx_analytics_period ON analytics_metrics(period_start, period_end);

-- =====================================================
-- 8. SYSTEM CONFIGURATION TABLE
-- =====================================================
CREATE TABLE system_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default configuration
INSERT INTO system_config (config_key, config_value, description) VALUES
('duplicate_threshold', '{"name_similarity": 85, "phone_similarity": 90}'::jsonb, 'Thresholds for duplicate detection'),
('default_screening_weights', '{"semantic": 0.7, "skill": 0.3, "experience": 0.0}'::jsonb, 'Default scoring weights'),
('email_fetch_config', '{"fetch_interval_hours": 1, "mark_as_read": false}'::jsonb, 'Email fetching configuration'),
('ui_settings', '{"items_per_page": 50, "theme": "light"}'::jsonb, 'UI preferences');

-- =====================================================
-- VIEWS FOR COMMON QUERIES
-- =====================================================

-- View: Active Candidates (non-duplicates)
CREATE OR REPLACE VIEW active_candidates AS
SELECT 
    id,
    name,
    email,
    phone,
    skills,
    experience_years,
    source_type,
    created_at
FROM candidates
WHERE is_duplicate = FALSE
ORDER BY created_at DESC;

-- View: Latest Screening Summary
CREATE OR REPLACE VIEW latest_screening_summary AS
SELECT 
    jd.title as job_title,
    jd.id as job_id,
    COUNT(sr.id) as total_screened,
    COUNT(CASE WHEN sr.in_shortlist THEN 1 END) as shortlisted,
    COUNT(CASE WHEN sr.in_longlist THEN 1 END) as longlisted,
    AVG(sr.final_score) as avg_score,
    MAX(sr.screened_at) as last_screened
FROM job_descriptions jd
LEFT JOIN screening_results sr ON jd.id = sr.job_description_id
WHERE jd.status = 'active'
GROUP BY jd.id, jd.title;

-- View: Duplicate Candidates Report
CREATE OR REPLACE VIEW duplicate_candidates_report AS
SELECT 
    c1.id as duplicate_id,
    c1.name as duplicate_name,
    c1.email as duplicate_email,
    c2.id as original_id,
    c2.name as original_name,
    c2.email as original_email,
    c1.duplicate_confidence,
    c1.created_at as duplicate_created_at
FROM candidates c1
JOIN candidates c2 ON c1.duplicate_of = c2.id
WHERE c1.is_duplicate = TRUE;

-- =====================================================
-- FUNCTIONS & TRIGGERS
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_candidates_updated_at BEFORE UPDATE ON candidates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_job_descriptions_updated_at BEFORE UPDATE ON job_descriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- GRANTS (Adjust as needed)
-- =====================================================
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_user;

-- =====================================================
-- END OF SCHEMA
-- =====================================================
