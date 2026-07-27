-- SIGNAL EDU — Role Template Seed Data
-- 10 industry roles with TE / PC / CQ thresholds (1.0 – 9.0 scale)
--
-- Safe to run multiple times (ON CONFLICT … DO UPDATE).
-- Deterministic UUIDs so rows are stable across environments.
--
-- Threshold rationale:
--   TE  Technical Execution   — code quality, tooling, deployment
--   PC  Problem Complexity    — scope and depth of problems solved
--   CQ  Communication Quality — documentation, README, project clarity
--
-- required_signals values:
--   "has_tests"             test suite detected via file-path patterns
--   "has_ci"                CI workflow detected (.github/workflows etc.)
--   "has_deployment_config" Dockerfile / fly.toml / Procfile etc.
--   "has_readme"            README present in repository

INSERT INTO role_templates
    (id, slug, title,
     te_threshold, pc_threshold, cq_threshold,
     required_signals, description)
VALUES

-- 1. Data Scientist
(
    '10000000-0000-4000-8000-000000000001',
    'data-scientist',
    'Data Scientist',
    5.5, 6.5, 5.5,
    '["has_readme","has_tests"]',
    'Transforms raw data into actionable insight through statistical modelling, '
    'hypothesis testing, and clear communication of findings. Requires Python or R '
    'proficiency, reproducible analysis workflows, and the ability to explain '
    'complex results to non-technical audiences.'
),

-- 2. Machine Learning Engineer
(
    '10000000-0000-4000-8000-000000000002',
    'ml-engineer',
    'Machine Learning Engineer',
    6.5, 6.5, 5.0,
    '["has_tests","has_ci","has_deployment_config"]',
    'Designs, trains, and ships machine learning models to production at scale. '
    'Requires strong software engineering foundations, MLOps practices (versioning, '
    'monitoring, CI), and experience with distributed training frameworks such as '
    'PyTorch or JAX.'
),

-- 3. AI Engineer
(
    '10000000-0000-4000-8000-000000000003',
    'ai-engineer',
    'AI Engineer',
    6.0, 5.5, 5.5,
    '["has_readme","has_tests"]',
    'Builds AI-powered products by integrating LLMs, embedding models, and retrieval '
    'systems into production applications. Requires API design skills, prompt '
    'engineering discipline, evaluation frameworks, and the ability to document '
    'AI behaviour and limitations clearly.'
),

-- 4. Data Analyst
(
    '10000000-0000-4000-8000-000000000004',
    'data-analyst',
    'Data Analyst',
    4.0, 4.5, 6.0,
    '["has_readme"]',
    'Extracts insight from structured data using SQL, Python or R, and BI tooling. '
    'Communication quality is the primary differentiator: dashboards, reports, and '
    'data stories must be clear, accurate, and targeted at business stakeholders.'
),

-- 5. Backend Engineer
(
    '10000000-0000-4000-8000-000000000005',
    'backend-engineer',
    'Backend Engineer',
    6.5, 5.5, 4.5,
    '["has_tests","has_ci"]',
    'Designs and operates server-side systems: REST/gRPC APIs, relational databases, '
    'message queues, and caching layers. Requires test-driven development, CI '
    'pipelines, and the ability to reason about performance, reliability, and '
    'security under production load.'
),

-- 6. Full Stack Developer
(
    '10000000-0000-4000-8000-000000000006',
    'full-stack-developer',
    'Full Stack Developer',
    5.5, 5.0, 5.0,
    '["has_readme","has_deployment_config"]',
    'Delivers end-to-end web features across frontend (React/Vue/Svelte) and backend '
    '(Node/Python/Go). Breadth is the expectation: ability to ship a complete '
    'user-facing feature from database schema to deployed UI without handing off '
    'at layer boundaries.'
),

-- 7. DevOps Engineer
(
    '10000000-0000-4000-8000-000000000007',
    'devops-engineer',
    'DevOps Engineer',
    6.5, 5.5, 5.5,
    '["has_ci","has_deployment_config"]',
    'Builds and operates the infrastructure that lets engineering teams ship safely '
    'and quickly. Core competencies: container orchestration (Docker/Kubernetes), '
    'CI/CD pipelines, infrastructure-as-code (Terraform/Pulumi), and incident '
    'runbook authoring.'
),

-- 8. Product Manager
(
    '10000000-0000-4000-8000-000000000008',
    'product-manager',
    'Product Manager',
    3.0, 4.5, 7.0,
    '["has_readme"]',
    'Defines what gets built and why. Technical literacy enables credible '
    'conversations with engineers, but Communication Quality is the primary signal: '
    'PRDs, user-research docs, roadmaps, and stakeholder updates must be precise, '
    'structured, and persuasive.'
),

-- 9. Research Engineer
(
    '10000000-0000-4000-8000-000000000009',
    'research-engineer',
    'Research Engineer',
    7.0, 7.5, 6.0,
    '["has_tests","has_readme"]',
    'Implements novel algorithms and systems at the boundary between research and '
    'engineering. Requires advanced programming skills (low-level systems or '
    'high-performance computing), the ability to tackle genuinely open problems, and '
    'paper-quality written communication of methods and results.'
),

-- 10. Software Engineer
(
    '10000000-0000-4000-8000-00000000000a',
    'software-engineer',
    'Software Engineer',
    5.0, 4.5, 4.5,
    '["has_tests"]',
    'The generalist entry point for professional software development. Requires solid '
    'programming fundamentals, data structure and algorithm knowledge, readable code '
    'with tests, and the ability to collaborate effectively through pull requests and '
    'code review.'
)

ON CONFLICT (slug) DO UPDATE SET
    title            = EXCLUDED.title,
    te_threshold     = EXCLUDED.te_threshold,
    pc_threshold     = EXCLUDED.pc_threshold,
    cq_threshold     = EXCLUDED.cq_threshold,
    required_signals = EXCLUDED.required_signals,
    description      = EXCLUDED.description;
