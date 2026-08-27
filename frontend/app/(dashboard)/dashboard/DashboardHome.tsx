"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { ScoreRing, ScoreBar } from "@/components/ui/score-ring";
import { Stagger, FadeUp } from "@/components/ui/motion";
import { useProfile } from "@/lib/hooks/useProfile";
import { useAnalysisHistory } from "@/lib/hooks/useAnalysisHistory";
import { useGapAnalyses } from "@/lib/hooks/useGapAnalyses";
import { signalComposite, DIMENSION_LABELS, type Dimension } from "@/types/signal";
import { Zap, Target, Lightbulb, ArrowRight, CheckCircle, Clock, AlertCircle, Loader2 } from "lucide-react";
import { cn, asFiniteNumber } from "@/lib/utils";

const DIMS: Dimension[] = [
  "technical_execution",
  "problem_complexity",
  "communication_quality",
];

function formatDate(iso: string) {
  return new Intl.RelativeTimeFormat("en", { numeric: "auto" }).format(
    Math.round((new Date(iso).getTime() - Date.now()) / (1000 * 60 * 60 * 24)),
    "day"
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; icon: React.ElementType; cn: string }> = {
    complete: { label: "Complete",   icon: CheckCircle,  cn: "text-emerald-400 bg-emerald-400/10" },
    failed:   { label: "Failed",     icon: AlertCircle,  cn: "text-red-400 bg-red-400/10" },
    queued:   { label: "Queued",     icon: Clock,        cn: "text-muted-foreground bg-white/5" },
  };
  const s = map[status] ?? { label: status, icon: Loader2, cn: "text-signal bg-signal/10" };
  const Icon = s.icon;
  return (
    <span className={cn("inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full", s.cn)}>
      <Icon className="w-3 h-3" />
      {s.label}
    </span>
  );
}

interface Props { firstName: string }

export function DashboardHome({ firstName }: Props) {
  const { profile, isLoading: profileLoading } = useProfile();
  const { history, isLoading: historyLoading } = useAnalysisHistory();
  const { readyCount } = useGapAnalyses();

  const composite = profile ? signalComposite(profile) : null;
  const hasProfile = !!profile;

  return (
    <div className="space-y-10">
      {/* Greeting */}
      <FadeUp>
        <div className="space-y-1">
          <h1 className="text-3xl font-semibold tracking-tight">
            Welcome back, {firstName}.
          </h1>
          <p className="text-muted-foreground text-sm">
            {hasProfile
              ? "Your capability profile is active."
              : "Run your first analysis to generate a capability profile."}
          </p>
        </div>
      </FadeUp>

      {/* Score hero — show if profile exists */}
      {!profileLoading && (
        <FadeUp delay={0.05}>
          {hasProfile ? (
            <div className="rounded-2xl border border-white/5 bg-card p-8">
              <div className="flex flex-col md:flex-row md:items-center gap-8">
                {/* SIGNAL ring */}
                <div className="flex flex-col items-center gap-2 shrink-0">
                  <ScoreRing score={composite} size={164} label="SIGNAL" sublabel="/ 9.0" />
                  <p className="text-[11px] text-muted-foreground/50 text-center">
                    {profile.verified_capabilities.length} verified capabilities
                  </p>
                </div>

                {/* Dimension breakdown */}
                <div className="flex-1 space-y-5">
                  {DIMS.map((key) => {
                    const score = asFiniteNumber(profile[key as keyof typeof profile] as number | null);
                    return (
                      <div key={key} className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-medium text-muted-foreground">
                            {DIMENSION_LABELS[key]}
                          </span>
                          <span className="text-sm font-semibold tabular-nums">
                            {score != null ? score.toFixed(1) : "—"}
                          </span>
                        </div>
                        <ScoreBar score={score} />
                      </div>
                    );
                  })}

                  {/* Stats row */}
                  <div className="flex items-center gap-6 pt-2 border-t border-white/5">
                    <div>
                      <p className="text-xs text-muted-foreground">Role readiness</p>
                      <p className="text-sm font-semibold">{readyCount} / 10 roles</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Evidence citations</p>
                      <p className="text-sm font-semibold">{profile.evidence_citations.length}</p>
                    </div>
                    <Button asChild size="sm" className="ml-auto rounded-lg bg-signal text-white hover:bg-signal/90 h-8 px-4">
                      <Link href="/profile">View profile <ArrowRight className="ml-1 w-3 h-3" /></Link>
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* No profile CTA */
            <div className="relative overflow-hidden rounded-2xl border border-signal/20 bg-signal-dim p-8">
              <div className="absolute inset-0 gradient-mesh opacity-50 pointer-events-none" />
              <div className="relative flex flex-col md:flex-row md:items-center gap-6 justify-between">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-signal" />
                    <span className="text-xs font-medium text-signal uppercase tracking-widest">Ready to analyze</span>
                  </div>
                  <h2 className="text-xl font-semibold">Generate your capability profile</h2>
                  <p className="text-sm text-muted-foreground max-w-md">
                    SIGNAL will analyze your GitHub repositories and produce a scored capability profile with evidence citations — in under 4 minutes.
                  </p>
                </div>
                <Button asChild className="shrink-0 h-11 px-6 rounded-xl bg-signal text-white hover:bg-signal/90 shadow-[0_0_24px_oklch(0.65_0.19_259/20%)]">
                  <Link href="/analysis">
                    Start analysis
                    <ArrowRight className="ml-2 w-4 h-4" />
                  </Link>
                </Button>
              </div>
            </div>
          )}
        </FadeUp>
      )}

      {/* Quick actions */}
      <div className="space-y-4">
        <FadeUp delay={0.1}>
          <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-widest">Quick access</h2>
        </FadeUp>
        <Stagger className="grid md:grid-cols-3 gap-4">
          {QUICK_ACTIONS.map((action) => {
            const Icon = action.icon;
            return (
              <motion.div
                key={action.title}
                variants={{
                  hidden: { opacity: 0, y: 20 },
                  show:   { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] } },
                }}
              >
                <Link
                  href={action.href}
                  className="flex flex-col gap-4 p-6 rounded-2xl border border-white/5 bg-card hover:border-white/10 hover:bg-card/80 transition-all group h-full"
                >
                  <div className="w-9 h-9 rounded-xl bg-white/5 flex items-center justify-center group-hover:bg-signal-dim group-hover:border group-hover:border-signal/20 transition-all">
                    <Icon className="w-4 h-4 text-muted-foreground group-hover:text-signal transition-colors" />
                  </div>
                  <div className="space-y-1.5">
                    <p className="text-sm font-medium">{action.title}</p>
                    <p className="text-xs text-muted-foreground leading-relaxed">{action.desc}</p>
                  </div>
                  <div className="mt-auto flex items-center gap-1 text-xs text-signal opacity-0 group-hover:opacity-100 transition-opacity">
                    <span>{action.cta}</span>
                    <ArrowRight className="w-3 h-3" />
                  </div>
                </Link>
              </motion.div>
            );
          })}
        </Stagger>
      </div>

      {/* Recent analyses */}
      {!historyLoading && history.length > 0 && (
        <FadeUp delay={0.18}>
          <div className="space-y-3">
            <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-widest">Analysis history</h2>
            <div className="rounded-2xl border border-white/5 bg-card divide-y divide-white/5 overflow-hidden">
              {history.slice(0, 5).map((job) => (
                <div key={job.id} className="flex items-center justify-between px-5 py-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <Zap className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                    <span className="text-xs text-muted-foreground truncate font-mono">
                      {job.id.slice(0, 8)}…
                    </span>
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    <span className="text-[11px] text-muted-foreground/60">
                      {formatDate(job.started_at)}
                    </span>
                    <StatusBadge status={job.status} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </FadeUp>
      )}
    </div>
  );
}

const QUICK_ACTIONS = [
  { icon: Zap,       title: "Run analysis",     desc: "Analyze your GitHub repositories and score your capability dimensions.",               href: "/analysis",        cta: "Start now"     },
  { icon: Target,    title: "Gap analysis",      desc: "Compare your profile against 10 roles — ML Engineer, Data Scientist, and more.",      href: "/gaps",            cta: "Select a role" },
  { icon: Lightbulb, title: "Recommendations",   desc: "Evidence-backed projects to close the gap between where you are and where you want.", href: "/recommendations", cta: "View all"      },
];
