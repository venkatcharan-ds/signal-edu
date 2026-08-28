"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Skeleton } from "@/components/ui/skeleton";
import { Stagger, FadeUp } from "@/components/ui/motion";
import { useProjects } from "@/lib/hooks/useProjects";
import {
  ProjectRepo,
  ProjectDimensionScores,
  PROJECT_DIMENSION_LABELS,
  CapabilityStatus,
  AcademicVsRealworld,
} from "@/types/signal";
import {
  GitBranch, Zap, ChevronDown,
  CheckCircle2, CircleDot, Info, XCircle, ExternalLink,
  Lightbulb, BarChart3, Code2, Briefcase, Sparkles,
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

// ── Score helpers ─────────────────────────────────────────────────────────────

function scoreBand(score: number): "low" | "mid" | "high" {
  if (score < 4) return "low";
  if (score < 7) return "mid";
  return "high";
}

function ScorePill({ score }: { score: number }) {
  const band = scoreBand(score);
  return (
    <span
      className={cn(
        "tabular-nums font-bold text-sm",
        band === "high" ? "text-emerald-400" :
        band === "mid"  ? "text-signal"      : "text-amber-400"
      )}
    >
      {score.toFixed(1)}
    </span>
  );
}

function MiniScoreBar({ score }: { score: number }) {
  const band = scoreBand(score);
  return (
    <div className="h-1 rounded-full bg-white/5 overflow-hidden w-full">
      <motion.div
        className={cn(
          "h-full rounded-full",
          band === "high" ? "bg-emerald-400" :
          band === "mid"  ? "bg-signal"      : "bg-amber-400"
        )}
        initial={{ width: 0 }}
        animate={{ width: `${(score / 10) * 100}%` }}
        transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
      />
    </div>
  );
}

// ── Capability status chip ────────────────────────────────────────────────────

const STATUS_META: Record<CapabilityStatus, { label: string; icon: React.ElementType; cn: string }> = {
  demonstrated:     { label: "Demonstrated",     icon: CheckCircle2, cn: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20" },
  inferred:         { label: "Inferred",         icon: CircleDot,    cn: "text-signal bg-signal/10 border-signal/20" },
  claimed:          { label: "Claimed",           icon: Info,         cn: "text-amber-400 bg-amber-400/10 border-amber-400/20" },
  not_demonstrated: { label: "Not Demonstrated", icon: XCircle,      cn: "text-muted-foreground bg-white/4 border-white/8" },
};

function StatusChip({ status }: { status: CapabilityStatus }) {
  const meta = STATUS_META[status] ?? STATUS_META.claimed;
  const Icon = meta.icon;
  return (
    <span className={cn("inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full border", meta.cn)}>
      <Icon className="w-3 h-3" />
      {meta.label}
    </span>
  );
}

// ── Academic vs real-world badge ──────────────────────────────────────────────

const RW_META: Record<AcademicVsRealworld, { label: string; cn: string }> = {
  real_world: { label: "Real-World",  cn: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20" },
  mixed:      { label: "Mixed",       cn: "text-signal bg-signal/10 border-signal/20" },
  academic:   { label: "Academic",    cn: "text-muted-foreground bg-white/5 border-white/10" },
};

function RWBadge({ value }: { value: AcademicVsRealworld }) {
  const meta = RW_META[value] ?? RW_META.mixed;
  return (
    <span className={cn("text-[11px] font-medium px-2 py-0.5 rounded-full border", meta.cn)}>
      {meta.label}
    </span>
  );
}

// ── Level badge ───────────────────────────────────────────────────────────────

const LEVEL_CN: Record<string, string> = {
  Beginner:     "text-muted-foreground bg-white/5 border-white/10",
  Intermediate: "text-signal bg-signal/10 border-signal/20",
  Advanced:     "text-violet-400 bg-violet-400/10 border-violet-400/20",
};

function LevelBadge({ level }: { level: string }) {
  return (
    <span className={cn("text-[11px] font-medium px-2 py-0.5 rounded-full border", LEVEL_CN[level] ?? LEVEL_CN.Intermediate)}>
      {level}
    </span>
  );
}

// ── Role relevance dots ───────────────────────────────────────────────────────

const ROLE_LABELS: Record<string, string> = {
  backend_engineer:  "Backend",
  ml_engineer:       "ML",
  data_scientist:    "Data Sci",
  frontend_engineer: "Frontend",
  devops_engineer:   "DevOps",
};

const RELEVANCE_CN: Record<string, string> = {
  high:   "bg-emerald-400",
  medium: "bg-signal",
  low:    "bg-white/20",
  none:   "bg-white/8",
};

function RoleRelevanceDots({ relevance }: { relevance: Record<string, string> }) {
  return (
    <div className="flex flex-wrap gap-2">
      {Object.entries(ROLE_LABELS).map(([key, label]) => {
        const level = relevance[key] ?? "none";
        return (
          <div key={key} className="flex items-center gap-1.5">
            <div className={cn("w-2 h-2 rounded-full", RELEVANCE_CN[level] ?? RELEVANCE_CN.none)} />
            <span className="text-[11px] text-muted-foreground">{label}</span>
          </div>
        );
      })}
    </div>
  );
}

// ── Dimension radar (horizontal bars) ─────────────────────────────────────────

function DimensionBreakdown({ scores }: { scores: ProjectDimensionScores }) {
  const dims = Object.keys(PROJECT_DIMENSION_LABELS) as (keyof ProjectDimensionScores)[];
  return (
    <div className="space-y-2.5">
      {dims.map((dim) => {
        const score = scores[dim];
        return (
          <div key={dim} className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-muted-foreground">{PROJECT_DIMENSION_LABELS[dim]}</span>
              <ScorePill score={score} />
            </div>
            <MiniScoreBar score={score} />
          </div>
        );
      })}
    </div>
  );
}

// ── Repository card ───────────────────────────────────────────────────────────

function RepoCard({ repo }: { repo: ProjectRepo }) {
  const [expanded, setExpanded] = useState(false);
  const repoName = repo.repo_full_name.split("/")[1] ?? repo.repo_full_name;
  const githubUrl = `https://github.com/${repo.repo_full_name}`;

  return (
    <div className="rounded-2xl border border-white/5 bg-card overflow-hidden">
      {/* Header */}
      <button
        className="w-full flex items-start gap-4 p-5 text-left hover:bg-white/[0.02] transition-colors"
        onClick={() => setExpanded((p) => !p)}
      >
        {/* Left: icon + name */}
        <div className="w-9 h-9 rounded-xl bg-white/5 flex items-center justify-center shrink-0 mt-0.5">
          <GitBranch className="w-4 h-4 text-signal" />
        </div>

        <div className="flex-1 min-w-0 space-y-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold truncate">{repoName}</span>
            <LevelBadge level={repo.level} />
            <RWBadge value={repo.academic_vs_realworld} />
            <span className="text-[11px] text-muted-foreground">{repo.classification}</span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">{repo.summary}</p>
        </div>

        {/* Right: score + chevron */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="text-right">
            <p className="text-xl font-bold tabular-nums score-glow">
              <ScorePill score={repo.overall_score} />
              <span className="text-[11px] text-muted-foreground font-normal"> /10</span>
            </p>
          </div>
          <ChevronDown
            className={cn("w-4 h-4 text-muted-foreground/50 transition-transform", expanded && "rotate-180")}
          />
        </div>
      </button>

      {/* Expanded content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="border-t border-white/5 p-5 space-y-6">

              {/* How It Works */}
              {repo.how_it_works && (
                <div>
                  <h4 className="text-[11px] font-medium text-muted-foreground uppercase tracking-widest mb-2 flex items-center gap-1.5">
                    <Code2 className="w-3 h-3" />
                    How It Works
                  </h4>
                  <p className="text-xs text-foreground/80 leading-relaxed">{repo.how_it_works}</p>
                </div>
              )}

              {/* Capabilities Demonstrated */}
              {repo.capabilities_demonstrated.length > 0 && (
                <div>
                  <h4 className="text-[11px] font-medium text-muted-foreground uppercase tracking-widest mb-2 flex items-center gap-1.5">
                    <Sparkles className="w-3 h-3" />
                    What This Project Demonstrates
                  </h4>
                  <p className="text-[11px] text-muted-foreground mb-2">
                    Specific engineering capabilities backed by evidence in the repository:
                  </p>
                  <ul className="space-y-1.5">
                    {repo.capabilities_demonstrated.map((cap, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-foreground/80">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0 mt-0.5" />
                        {cap}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Technologies */}
              {repo.primary_technologies.length > 0 && (
                <div>
                  <h4 className="text-[11px] font-medium text-muted-foreground uppercase tracking-widest mb-2">
                    Technologies &amp; Evidence
                  </h4>
                  <p className="text-[11px] text-muted-foreground mb-2.5">
                    Each technology is classified by what the repository actually contains — not what the README claims.
                  </p>
                  <div className="space-y-2.5">
                    {repo.primary_technologies.map((tech) => (
                      <div key={tech.name} className="flex items-start gap-3">
                        <div className="shrink-0 pt-0.5">
                          <StatusChip status={tech.status} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <span className="text-xs font-semibold">{tech.name}</span>
                          <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed">{tech.evidence}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-muted-foreground/60">
                    <span><span className="text-emerald-400">●</span> Demonstrated = confirmed by a file or language stat</span>
                    <span><span className="text-signal">●</span> Inferred = language detected, framework unconfirmed</span>
                    <span><span className="text-amber-400">●</span> Claimed = README-only, not in repo structure</span>
                  </div>
                </div>
              )}

              {/* Dimension breakdown */}
              <div>
                <h4 className="text-[11px] font-medium text-muted-foreground uppercase tracking-widest mb-2">
                  7-Dimension Scores
                </h4>
                <p className="text-[11px] text-muted-foreground mb-3">
                  Each dimension scored 1–10. Overall score is the arithmetic mean — computed from these seven values, not estimated separately.
                </p>
                <DimensionBreakdown scores={repo.dimension_scores} />
              </div>

              {/* Real-World Comparison */}
              {repo.real_world_comparison && (
                <div>
                  <h4 className="text-[11px] font-medium text-muted-foreground uppercase tracking-widest mb-2 flex items-center gap-1.5">
                    <Briefcase className="w-3 h-3" />
                    How This Compares
                  </h4>
                  <p className="text-[11px] text-muted-foreground mb-2">
                    Compared against a typical college assignment, a strong internship-level project, and a production system:
                  </p>
                  <p className="text-xs text-foreground/80 leading-relaxed">{repo.real_world_comparison}</p>
                </div>
              )}

              {/* Role relevance */}
              {Object.keys(repo.role_relevance).length > 0 && (
                <div>
                  <h4 className="text-[11px] font-medium text-muted-foreground uppercase tracking-widest mb-2">
                    Relevant Job Roles
                  </h4>
                  <p className="text-[11px] text-muted-foreground mb-2.5">
                    How well this project supports each engineering specialisation on a job application:
                  </p>
                  <RoleRelevanceDots relevance={repo.role_relevance} />
                  <div className="mt-2.5 flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-muted-foreground/60">
                    <span><span className="text-emerald-400">●</span> High</span>
                    <span><span className="text-signal">●</span> Medium</span>
                    <span><span className="text-white/20">●</span> Low / None</span>
                  </div>
                </div>
              )}

              {/* Recommendations */}
              {repo.improvement_recommendations.length > 0 && (
                <div>
                  <h4 className="text-[11px] font-medium text-muted-foreground uppercase tracking-widest mb-2">
                    Top Improvements
                  </h4>
                  <p className="text-[11px] text-muted-foreground mb-2.5">
                    Specific changes that would meaningfully improve this project&#39;s signal to employers:
                  </p>
                  <ul className="space-y-2">
                    {repo.improvement_recommendations.map((rec, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                        <Lightbulb className="w-3 h-3 text-signal shrink-0 mt-0.5" />
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* GitHub link */}
              <div className="pt-1 border-t border-white/5">
                <a
                  href={githubUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  <GitBranch className="w-3 h-3" />
                  {repo.repo_full_name}
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Main view ─────────────────────────────────────────────────────────────────

export function ProjectsView() {
  const { projects, isLoading, isError } = useProjects();

  if (isLoading) return <ProjectsSkeleton />;

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[40vh] text-center space-y-4">
        <BarChart3 className="w-10 h-10 text-muted-foreground/30" />
        <div className="space-y-1">
          <p className="font-medium">Could not load projects</p>
          <p className="text-sm text-muted-foreground">Check your connection and try again.</p>
        </div>
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div className="space-y-10">
        <FadeUp>
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">Project Intelligence</h1>
            <p className="text-sm text-muted-foreground">
              Per-repository analysis — classification, scoring, and evidence-backed technology assessment.
            </p>
          </div>
        </FadeUp>
        <FadeUp delay={0.04}>
          <div className="rounded-2xl border border-white/5 bg-card p-10 text-center space-y-4">
            <GitBranch className="w-10 h-10 text-muted-foreground/30 mx-auto" />
            <div className="space-y-1">
              <p className="font-medium">No project analysis yet</p>
              <p className="text-sm text-muted-foreground">
                Run a new analysis to generate per-repository intelligence for your top projects.
              </p>
            </div>
            <Link
              href="/analysis"
              className="inline-flex items-center gap-2 mt-2 px-5 py-2.5 rounded-xl bg-signal text-white text-sm font-medium hover:bg-signal/90 transition-colors"
            >
              <Zap className="w-4 h-4" />
              Run analysis
            </Link>
          </div>
        </FadeUp>
      </div>
    );
  }

  const avgScore = projects.reduce((sum, p) => sum + p.overall_score, 0) / projects.length;
  const topProject = [...projects].sort((a, b) => b.overall_score - a.overall_score)[0];
  const realWorldCount = projects.filter((p) => p.academic_vs_realworld === "real_world").length;

  return (
    <div className="space-y-10">
      {/* Header */}
      <FadeUp>
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Project Intelligence</h1>
          <p className="text-sm text-muted-foreground">
            Evidence-backed analysis of your top {projects.length} repositories.
          </p>
        </div>
      </FadeUp>

      {/* Summary band */}
      <FadeUp delay={0.04}>
        <div className="grid grid-cols-3 gap-4">
          <div className="rounded-2xl border border-white/5 bg-card px-5 py-4">
            <p className="text-xs text-muted-foreground mb-1">Avg. Project Score</p>
            <p className="text-2xl font-bold tabular-nums">
              <ScorePill score={avgScore} />
              <span className="text-xs text-muted-foreground font-normal"> /10</span>
            </p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-card px-5 py-4">
            <p className="text-xs text-muted-foreground mb-1">Best Project</p>
            <p className="text-sm font-semibold truncate">
              {topProject?.repo_full_name.split("/")[1] ?? "—"}
            </p>
            <p className="text-[11px] text-muted-foreground">{topProject?.classification}</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-card px-5 py-4">
            <p className="text-xs text-muted-foreground mb-1">Real-World Projects</p>
            <p className="text-2xl font-bold tabular-nums">
              {realWorldCount}
              <span className="text-xs text-muted-foreground font-normal"> / {projects.length}</span>
            </p>
          </div>
        </div>
      </FadeUp>

      {/* Repository cards */}
      <Stagger className="space-y-3">
        {projects.map((repo) => (
          <motion.div
            key={repo.repo_full_name}
            variants={{
              hidden: { opacity: 0, y: 16 },
              show:   { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } },
            }}
          >
            <RepoCard repo={repo} />
          </motion.div>
        ))}
      </Stagger>
    </div>
  );
}

function ProjectsSkeleton() {
  return (
    <div className="space-y-10">
      <div className="space-y-2">
        <Skeleton className="h-7 w-56" />
        <Skeleton className="h-4 w-80" />
      </div>
      <div className="grid grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-20 rounded-2xl" />)}
      </div>
      <div className="space-y-3">
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-28 rounded-2xl" />)}
      </div>
    </div>
  );
}
