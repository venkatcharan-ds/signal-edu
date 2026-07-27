-- SIGNAL EDU — Initial Schema
-- Run via: psql $DATABASE_URL -f 001_initial_schema.sql
-- Or apply via Supabase dashboard SQL editor

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_id       BIGINT UNIQUE NOT NULL,
    github_username VARCHAR(255) UNIQUE NOT NULL,
    github_email    VARCHAR(255),
    github_avatar   TEXT,
    full_name       VARCHAR(255),
    institution     VARCHAR(255),
    resume_skills   JSONB DEFAULT '[]'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- GitHub Repositories
CREATE TABLE IF NOT EXISTS repositories (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    github_repo_id          BIGINT UNIQUE NOT NULL,
    name                    VARCHAR(255) NOT NULL,
    full_name               VARCHAR(255) NOT NULL,
    description             TEXT,
    url                     TEXT NOT NULL,
    languages               JSONB DEFAULT '{}'::jsonb,
    commit_count            INTEGER DEFAULT 0,
    last_commit_at          TIMESTAMPTZ,
    has_readme              BOOLEAN DEFAULT FALSE,
    readme_content          TEXT,
    readme_word_count       INTEGER DEFAULT 0,
    has_tests               BOOLEAN DEFAULT FALSE,
    has_ci                  BOOLEAN DEFAULT FALSE,
    has_deployment_config   BOOLEAN DEFAULT FALSE,
    is_fork                 BOOLEAN DEFAULT FALSE,
    stars                   INTEGER DEFAULT 0,
    raw_github_data         JSONB,
    fetched_at              TIMESTAMPTZ DEFAULT NOW()
);

-- Uploaded Artifacts
CREATE TABLE IF NOT EXISTS artifacts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type        VARCHAR(50) NOT NULL CHECK (type IN ('pdf', 'link', 'certificate')),
    title       VARCHAR(500),
    url         TEXT,
    raw_text    TEXT,
    metadata    JSONB DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Analysis Jobs
CREATE TABLE IF NOT EXISTS analysis_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status          VARCHAR(50) DEFAULT 'queued'
                        CHECK (status IN ('queued','github_fetch','evidence_extract','ai_analysis','scoring','complete','failed')),
    current_step    VARCHAR(100),
    progress_pct    INTEGER DEFAULT 0 CHECK (progress_pct BETWEEN 0 AND 100),
    error_message   TEXT,
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

-- Role Templates
CREATE TABLE IF NOT EXISTS role_templates (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug                VARCHAR(100) UNIQUE NOT NULL,
    title               VARCHAR(255) NOT NULL,
    te_threshold        NUMERIC(3,1) NOT NULL,
    pc_threshold        NUMERIC(3,1) NOT NULL,
    cq_threshold        NUMERIC(3,1) NOT NULL,
    required_signals    JSONB DEFAULT '[]'::jsonb,
    description         TEXT
);

-- Capability Profiles
CREATE TABLE IF NOT EXISTS capability_profiles (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id                  UUID REFERENCES analysis_jobs(id),
    is_current              BOOLEAN DEFAULT TRUE,
    technical_execution     NUMERIC(3,1) CHECK (technical_execution BETWEEN 1.0 AND 9.0),
    problem_complexity      NUMERIC(3,1) CHECK (problem_complexity BETWEEN 1.0 AND 9.0),
    communication_quality   NUMERIC(3,1) CHECK (communication_quality BETWEEN 1.0 AND 9.0),
    te_confidence           NUMERIC(3,2) CHECK (te_confidence BETWEEN 0.0 AND 1.0),
    pc_confidence           NUMERIC(3,2) CHECK (pc_confidence BETWEEN 0.0 AND 1.0),
    cq_confidence           NUMERIC(3,2) CHECK (cq_confidence BETWEEN 0.0 AND 1.0),
    objective_signals       JSONB,
    te_percentile           INTEGER CHECK (te_percentile BETWEEN 0 AND 100),
    pc_percentile           INTEGER CHECK (pc_percentile BETWEEN 0 AND 100),
    cq_percentile           INTEGER CHECK (cq_percentile BETWEEN 0 AND 100),
    verified_capabilities   JSONB DEFAULT '[]'::jsonb,
    raw_ai_response         JSONB,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- Evidence Citations
CREATE TABLE IF NOT EXISTS evidence_citations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id          UUID NOT NULL REFERENCES capability_profiles(id) ON DELETE CASCADE,
    dimension           VARCHAR(50) NOT NULL
                            CHECK (dimension IN ('technical_execution','problem_complexity','communication_quality')),
    citation_text       TEXT NOT NULL,
    artifact_type       VARCHAR(50) CHECK (artifact_type IN ('repository','pdf','link')),
    artifact_ref        TEXT,
    score_contribution  NUMERIC(3,1),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Gap Analyses
CREATE TABLE IF NOT EXISTS gap_analyses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id      UUID NOT NULL REFERENCES capability_profiles(id) ON DELETE CASCADE,
    role_id         UUID NOT NULL REFERENCES role_templates(id),
    te_gap          NUMERIC(3,1),
    pc_gap          NUMERIC(3,1),
    cq_gap          NUMERIC(3,1),
    overall_ready   BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Recommendations
CREATE TABLE IF NOT EXISTS recommendations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gap_analysis_id     UUID NOT NULL REFERENCES gap_analyses(id) ON DELETE CASCADE,
    dimension           VARCHAR(50) NOT NULL
                            CHECK (dimension IN ('technical_execution','problem_complexity','communication_quality')),
    priority            INTEGER NOT NULL,
    title               VARCHAR(500) NOT NULL,
    description         TEXT NOT NULL,
    evidence_type       VARCHAR(100),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Profile Views
CREATE TABLE IF NOT EXISTS profile_views (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    viewer_ip       VARCHAR(45),
    is_logged_in    BOOLEAN DEFAULT FALSE,
    viewed_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_capability_profiles_user_current ON capability_profiles(user_id, is_current);
CREATE INDEX IF NOT EXISTS idx_evidence_citations_profile ON evidence_citations(profile_id, dimension);
CREATE INDEX IF NOT EXISTS idx_repositories_user ON repositories(user_id);
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_user_status ON analysis_jobs(user_id, status);
CREATE INDEX IF NOT EXISTS idx_profile_views_user_time ON profile_views(user_id, viewed_at);
CREATE INDEX IF NOT EXISTS idx_gap_analyses_profile ON gap_analyses(profile_id);
