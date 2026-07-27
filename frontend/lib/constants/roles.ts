import type { RoleTemplate } from "@/types/signal";

// Deterministic seed data — matches backend seed.py exactly.
// Avoids needing an API call for static role metadata.
export const ROLE_TEMPLATES: RoleTemplate[] = [
  {
    id:            "10000000-0000-4000-8000-000000000001",
    slug:          "data-scientist",
    title:         "Data Scientist",
    te_threshold:  5.5,
    pc_threshold:  6.5,
    cq_threshold:  5.5,
    description:   "Transforms raw data into actionable insight through statistical modelling, hypothesis testing, and clear communication of findings.",
  },
  {
    id:            "10000000-0000-4000-8000-000000000002",
    slug:          "ml-engineer",
    title:         "ML Engineer",
    te_threshold:  6.5,
    pc_threshold:  6.5,
    cq_threshold:  5.0,
    description:   "Designs, trains, and ships machine learning models to production at scale.",
  },
  {
    id:            "10000000-0000-4000-8000-000000000003",
    slug:          "ai-engineer",
    title:         "AI Engineer",
    te_threshold:  6.0,
    pc_threshold:  5.5,
    cq_threshold:  5.5,
    description:   "Builds AI-powered products by integrating LLMs, embedding models, and retrieval systems into production applications.",
  },
  {
    id:            "10000000-0000-4000-8000-000000000004",
    slug:          "data-analyst",
    title:         "Data Analyst",
    te_threshold:  4.0,
    pc_threshold:  4.5,
    cq_threshold:  6.0,
    description:   "Extracts insight from structured data using SQL, Python or R, and BI tooling.",
  },
  {
    id:            "10000000-0000-4000-8000-000000000005",
    slug:          "backend-engineer",
    title:         "Backend Engineer",
    te_threshold:  6.5,
    pc_threshold:  5.5,
    cq_threshold:  4.5,
    description:   "Designs and operates server-side systems: REST/gRPC APIs, relational databases, message queues, and caching layers.",
  },
  {
    id:            "10000000-0000-4000-8000-000000000006",
    slug:          "full-stack-developer",
    title:         "Full Stack Developer",
    te_threshold:  5.5,
    pc_threshold:  5.0,
    cq_threshold:  5.0,
    description:   "Delivers end-to-end web features across frontend and backend. Breadth is the expectation.",
  },
  {
    id:            "10000000-0000-4000-8000-000000000007",
    slug:          "devops-engineer",
    title:         "DevOps Engineer",
    te_threshold:  6.5,
    pc_threshold:  5.5,
    cq_threshold:  5.5,
    description:   "Builds and operates the infrastructure that lets engineering teams ship safely and quickly.",
  },
  {
    id:            "10000000-0000-4000-8000-000000000008",
    slug:          "product-manager",
    title:         "Product Manager",
    te_threshold:  3.0,
    pc_threshold:  4.5,
    cq_threshold:  7.0,
    description:   "Defines what gets built and why. Communication Quality is the primary signal.",
  },
  {
    id:            "10000000-0000-4000-8000-000000000009",
    slug:          "research-engineer",
    title:         "Research Engineer",
    te_threshold:  7.0,
    pc_threshold:  7.5,
    cq_threshold:  6.0,
    description:   "Implements novel algorithms at the boundary between research and engineering.",
  },
  {
    id:            "10000000-0000-4000-8000-00000000000a",
    slug:          "software-engineer",
    title:         "Software Engineer",
    te_threshold:  5.0,
    pc_threshold:  4.5,
    cq_threshold:  4.5,
    description:   "The generalist entry point for professional software development.",
  },
];

export const ROLE_BY_SLUG = Object.fromEntries(
  ROLE_TEMPLATES.map((r) => [r.slug, r])
) as Record<string, RoleTemplate>;
