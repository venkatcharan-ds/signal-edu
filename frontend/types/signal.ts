// Core SIGNAL domain types — shared across all components
import { asFiniteNumber } from "@/lib/utils";

export type Dimension = "technical_execution" | "problem_complexity" | "communication_quality";

export interface EvidenceCitation {
  id: string;
  dimension: Dimension;
  citation_text: string;
  artifact_type: "github_repo" | "readme" | "commit_history" | "ci_workflow" | "deployment_config" | "language_signal" | "repository" | "pdf" | "link" | null;
  artifact_ref: string | null;
  score_contribution: number | null;
}

export interface CapabilityProfile {
  id: string;
  user_id: string;
  is_current: boolean;
  technical_execution: number | null;
  problem_complexity: number | null;
  communication_quality: number | null;
  te_confidence: number | null;
  pc_confidence: number | null;
  cq_confidence: number | null;
  te_percentile: number | null;
  pc_percentile: number | null;
  cq_percentile: number | null;
  te_narrative: string | null;
  pc_narrative: string | null;
  cq_narrative: string | null;
  verified_capabilities: string[];
  evidence_citations: EvidenceCitation[];
  created_at: string;
}

export interface PublicProfile {
  github_username: string;
  full_name: string | null;
  github_avatar: string | null;
  institution: string | null;
  profile: CapabilityProfile | null;
  resume_skills: string[];
  verified_capability_count: number;
  resume_skill_count: number;
}

export interface AnalysisQuota {
  used_today: number;
  limit: number;
  remaining: number;
  has_active_job: boolean;
}

export interface AnalysisJob {
  id: string;
  user_id: string;
  status: "queued" | "github_fetch" | "evidence_extract" | "ai_analysis" | "scoring" | "complete" | "failed";
  current_step: string | null;
  progress_pct: number;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface AnalysisProgressEvent {
  step: string;
  label: string;
  progress: number;
  queue_position: number;
  detail: string | null;
  error: string | null;
}

export interface RoleTemplate {
  id: string;
  slug: string;
  title: string;
  te_threshold: number;
  pc_threshold: number;
  cq_threshold: number;
  description: string | null;
}

export interface Recommendation {
  id: string;
  dimension: Dimension;
  priority: number;
  title: string;
  description: string;
  evidence_type: string | null;
}

export interface GapAnalysis {
  id: string;
  profile_id?: string;
  role_slug: string;
  role_title: string;
  te_gap: number | null;
  pc_gap: number | null;
  cq_gap: number | null;
  overall_ready: boolean;
  missing_signals?: string[];
  recommendations: Recommendation[];
  created_at?: string;
}

// ── Project Intelligence types ────────────────────────────────────────────────

export type CapabilityStatus = "demonstrated" | "inferred" | "claimed" | "not_demonstrated";
export type AcademicVsRealworld = "academic" | "real_world" | "mixed";
export type ProjectLevel = "Beginner" | "Intermediate" | "Advanced";
export type RoleRelevance = "high" | "medium" | "low" | "none";

export interface ProjectTechnology {
  name: string;
  status: CapabilityStatus;
  evidence: string;
}

export interface ProjectDimensionScores {
  code_quality: number;
  documentation: number;
  architecture: number;
  testing: number;
  deployment_readiness: number;
  complexity: number;
  real_world_impact: number;
}

export interface ProjectRepo {
  repo_full_name: string;
  summary: string;
  classification: string;
  level: ProjectLevel;
  overall_score: number;
  dimension_scores: ProjectDimensionScores;
  academic_vs_realworld: AcademicVsRealworld;
  primary_technologies: ProjectTechnology[];
  role_relevance: Record<string, RoleRelevance>;
  improvement_recommendations: string[];
  // V2 fields — empty string/array for pre-V2 profiles
  how_it_works: string;
  capabilities_demonstrated: string[];
  real_world_comparison: string;
}

export const PROJECT_DIMENSION_LABELS: Record<keyof ProjectDimensionScores, string> = {
  code_quality:         "Code Quality",
  documentation:        "Documentation",
  architecture:         "Architecture",
  testing:              "Testing",
  deployment_readiness: "Deployment Readiness",
  complexity:           "Complexity",
  real_world_impact:    "Real-World Impact",
};

export const CAPABILITY_STATUS_LABELS: Record<CapabilityStatus, string> = {
  demonstrated:      "Demonstrated",
  inferred:          "Inferred",
  claimed:           "Claimed",
  not_demonstrated:  "Not Demonstrated",
};

// ── UI helpers ────────────────────────────────────────────────────────────────

export const DIMENSION_LABELS: Record<Dimension, string> = {
  technical_execution:   "Technical Execution",
  problem_complexity:    "Problem Complexity",
  communication_quality: "Communication Quality",
};

export const DIMENSION_SHORT: Record<Dimension, string> = {
  technical_execution:   "TE",
  problem_complexity:    "PC",
  communication_quality: "CQ",
};

export const SCORE_BAND = (score: number): "emerging" | "developing" | "advanced" => {
  if (score <= 3) return "emerging";
  if (score <= 6) return "developing";
  return "advanced";
};

export const SCORE_BAND_LABEL: Record<string, string> = {
  emerging:   "Emerging",
  developing: "Developing",
  advanced:   "Advanced",
};

export function signalComposite(profile: Pick<CapabilityProfile, "technical_execution" | "problem_complexity" | "communication_quality">): number | null {
  const te = asFiniteNumber(profile.technical_execution);
  const pc = asFiniteNumber(profile.problem_complexity);
  const cq = asFiniteNumber(profile.communication_quality);
  if (te == null || pc == null || cq == null) return null;
  return Math.round(((te + pc + cq) / 3) * 10) / 10;
}
