"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Stagger, FadeUp } from "@/components/ui/motion";
import { useGapAnalyses } from "@/lib/hooks/useGapAnalyses";
import { useProfile } from "@/lib/hooks/useProfile";
import { ROLE_TEMPLATES } from "@/lib/constants/roles";
import { signalComposite, DIMENSION_LABELS } from "@/types/signal";
import type { GapAnalysis, RoleTemplate } from "@/types/signal";
import {
  CheckCircle, XCircle, Target, ArrowRight, Lightbulb, Zap,
  TrendingUp, TrendingDown, Minus,
} from "lucide-react";
import Link from "next/link";
import { cn, asFiniteNumber } from "@/lib/utils";

function GapValue({ value: valueProp }: { value: number | null }) {
  const value = asFiniteNumber(valueProp);
  if (value == null) return <span className="text-muted-foreground/40">—</span>;
  const isPositive = value >= 0;
  const abs = Math.abs(value).toFixed(1);
  return (
    <span className={cn("font-semibold tabular-nums", isPositive ? "text-emerald-400" : "text-amber-400")}>
      {isPositive ? "+" : "−"}{abs}
    </span>
  );
}

function DimGapBar({ value: valueProp, threshold }: { value: number | null; threshold: number }) {
  const value = asFiniteNumber(valueProp);
  if (value == null) return null;
  const score = value + threshold; // gap = score − threshold → score = gap + threshold
  const isPositive = value >= 0;
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{threshold.toFixed(1)} needed</span>
        <span className={cn("font-medium", isPositive ? "text-emerald-400" : "text-amber-400")}>
          {score.toFixed(1)} yours
        </span>
      </div>
      <div className="relative h-1.5 rounded-full bg-white/5 overflow-hidden">
        {/* Threshold marker */}
        <div
          className="absolute top-0 bottom-0 w-px bg-white/20 z-10"
          style={{ left: `${(threshold / 9) * 100}%` }}
        />
        {/* Score fill */}
        <motion.div
          className={cn("absolute top-0 bottom-0 rounded-full", isPositive ? "bg-emerald-400" : "bg-amber-400")}
          style={{ width: `${(score / 9) * 100}%` }}
          initial={{ width: 0 }}
          animate={{ width: `${(score / 9) * 100}%` }}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
        />
      </div>
    </div>
  );
}

function RoleCard({
  role,
  gap,
  selected,
  onClick,
}: {
  role: RoleTemplate;
  gap: GapAnalysis | undefined;
  selected: boolean;
  onClick: () => void;
}) {
  const hasGap = !!gap;
  const ready  = gap?.overall_ready ?? false;

  return (
    <motion.button
      variants={{
        hidden: { opacity: 0, scale: 0.97 },
        show:   { opacity: 1, scale: 1, transition: { duration: 0.3, ease: [0.22, 1, 0.36, 1] } },
      }}
      onClick={onClick}
      className={cn(
        "w-full flex items-center justify-between p-4 rounded-xl border text-left transition-all",
        selected
          ? "border-signal/30 bg-signal-dim"
          : "border-white/5 bg-card hover:border-white/10 hover:bg-card/80"
      )}
    >
      <div className="flex items-center gap-3 min-w-0">
        {hasGap ? (
          ready
            ? <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
            : <XCircle    className="w-4 h-4 text-amber-400 shrink-0" />
        ) : (
          <div className="w-4 h-4 rounded-full border border-white/15 shrink-0" />
        )}
        <span className="text-sm font-medium truncate">{role.title}</span>
      </div>
      <div className="flex items-center gap-2 shrink-0 ml-3">
        {hasGap && (
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <GapValue value={gap?.te_gap ?? null} />
            <span className="text-white/15">/</span>
            <GapValue value={gap?.pc_gap ?? null} />
            <span className="text-white/15">/</span>
            <GapValue value={gap?.cq_gap ?? null} />
          </div>
        )}
        {!hasGap && (
          <span className="text-[11px] text-muted-foreground">
            {role.te_threshold}/{role.pc_threshold}/{role.cq_threshold}
          </span>
        )}
        <Target className={cn("w-3.5 h-3.5 transition-transform", selected ? "text-signal rotate-90" : "text-muted-foreground/30")} />
      </div>
    </motion.button>
  );
}

export function GapsView() {
  const { gaps, isLoading, isError } = useGapAnalyses();
  const { profile } = useProfile();
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);

  const gapBySlug = Object.fromEntries(gaps.map((g) => [g.role_slug, g]));
  const selectedRole = ROLE_TEMPLATES.find((r) => r.slug === selectedSlug);
  const selectedGap  = selectedSlug ? gapBySlug[selectedSlug] : undefined;

  const readyCount = gaps.filter((g) => g.overall_ready).length;
  const composite  = profile ? signalComposite(profile) : null;

  const noProfile = !isLoading && !isError && gaps.length === 0 && !profile;
  const noGaps    = !isLoading && !isError && gaps.length === 0 && !!profile;

  return (
    <div className="space-y-10">
      <FadeUp>
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Gap Analysis</h1>
          <p className="text-muted-foreground text-sm">
            Compare your capability profile against 10 target roles and see exactly what to build.
          </p>
        </div>
      </FadeUp>

      {/* Summary band — if gaps exist */}
      {gaps.length > 0 && (
        <FadeUp delay={0.04}>
          <div className="flex items-center gap-6 px-6 py-4 rounded-2xl border border-white/5 bg-card">
            <div>
              <p className="text-2xl font-semibold tabular-nums">{readyCount}<span className="text-muted-foreground text-lg font-normal"> / 10</span></p>
              <p className="text-xs text-muted-foreground">roles you meet</p>
            </div>
            <div className="h-8 w-px bg-white/8" />
            {composite && (
              <div>
                <p className="text-2xl font-semibold tabular-nums text-signal score-glow">{composite.toFixed(1)}</p>
                <p className="text-xs text-muted-foreground">SIGNAL score</p>
              </div>
            )}
            <div className="ml-auto">
              <Button asChild size="sm" variant="outline" className="rounded-lg border-white/10 hover:bg-white/5 gap-2 h-8 text-xs">
                <Link href="/recommendations">
                  <Lightbulb className="w-3.5 h-3.5" />
                  View recommendations
                  <ArrowRight className="w-3 h-3" />
                </Link>
              </Button>
            </div>
          </div>
        </FadeUp>
      )}

      {/* No profile CTA */}
      {noProfile && (
        <FadeUp delay={0.06}>
          <div className="rounded-2xl border border-white/5 bg-card p-8 text-center space-y-4">
            <Target className="w-10 h-10 text-muted-foreground/30 mx-auto" />
            <div className="space-y-1">
              <p className="font-medium">No profile yet</p>
              <p className="text-sm text-muted-foreground">Run an analysis first to see your gap against these roles.</p>
            </div>
            <Button asChild className="rounded-xl bg-signal text-white hover:bg-signal/90">
              <Link href="/analysis"><Zap className="mr-2 w-4 h-4" />Start analysis</Link>
            </Button>
          </div>
        </FadeUp>
      )}

      {/* Profile exists but analysis didn't compute gaps yet */}
      {noGaps && (
        <FadeUp delay={0.06}>
          <div className="rounded-2xl border border-white/5 bg-card p-8 text-center space-y-4">
            <Target className="w-10 h-10 text-muted-foreground/30 mx-auto" />
            <div className="space-y-1">
              <p className="font-medium">Gaps computing...</p>
              <p className="text-sm text-muted-foreground">Gaps are calculated after your analysis completes.</p>
            </div>
          </div>
        </FadeUp>
      )}

      {/* Role grid */}
      {(isLoading || gaps.length > 0 || !!profile) && (
        <div className="space-y-3">
          <FadeUp delay={0.06}>
            <p className="text-xs text-muted-foreground">
              {gaps.length > 0
                ? "Select a role to see your detailed gap breakdown."
                : "Select a role to see thresholds — run analysis first to unlock your gaps."}
            </p>
          </FadeUp>

          {isLoading ? (
            <div className="grid sm:grid-cols-2 gap-2">
              {Array.from({ length: 10 }).map((_, i) => (
                <Skeleton key={i} className="h-14 rounded-xl" />
              ))}
            </div>
          ) : (
            <Stagger className="grid sm:grid-cols-2 gap-2">
              {ROLE_TEMPLATES.map((role) => (
                <RoleCard
                  key={role.slug}
                  role={role}
                  gap={gapBySlug[role.slug]}
                  selected={selectedSlug === role.slug}
                  onClick={() => setSelectedSlug(prev => prev === role.slug ? null : role.slug)}
                />
              ))}
            </Stagger>
          )}
        </div>
      )}

      {/* Detail panel */}
      <AnimatePresence>
        {selectedRole && (
          <motion.div
            key={selectedRole.slug}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="space-y-6"
          >
            {/* Readiness banner */}
            {selectedGap ? (
              <div className={cn(
                "flex items-center gap-3 p-5 rounded-2xl border",
                selectedGap.overall_ready
                  ? "border-emerald-500/20 bg-emerald-500/5"
                  : "border-amber-500/15 bg-amber-500/5"
              )}>
                {selectedGap.overall_ready
                  ? <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />
                  : <XCircle    className="w-5 h-5 text-amber-400 shrink-0" />
                }
                <div>
                  <p className="text-sm font-medium">
                    {selectedGap.overall_ready
                      ? `You meet the ${selectedRole.title} bar`
                      : `${selectedRole.title} — gaps identified`}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {selectedGap.overall_ready
                      ? "Your profile satisfies all three dimension thresholds."
                      : "Build the recommended projects to close the gap."}
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-3 p-5 rounded-2xl border border-white/5 bg-card">
                <Target className="w-5 h-5 text-muted-foreground shrink-0" />
                <div>
                  <p className="text-sm font-medium">{selectedRole.title}</p>
                  <p className="text-xs text-muted-foreground">Run an analysis to see your gap against this role.</p>
                </div>
                <Button asChild size="sm" className="ml-auto rounded-lg bg-signal text-white hover:bg-signal/90 h-8 text-xs">
                  <Link href="/analysis"><Zap className="mr-1 w-3 h-3" />Analyze</Link>
                </Button>
              </div>
            )}

            {/* Dimension breakdown */}
            <div className="grid sm:grid-cols-3 gap-3">
              {[
                { key: "te", label: "Technical Execution",   gap: selectedGap?.te_gap, threshold: selectedRole.te_threshold },
                { key: "pc", label: "Problem Complexity",    gap: selectedGap?.pc_gap, threshold: selectedRole.pc_threshold },
                { key: "cq", label: "Communication Quality", gap: selectedGap?.cq_gap, threshold: selectedRole.cq_threshold },
              ].map(({ key, label, gap: dimGap, threshold }) => {
                const value   = dimGap ?? null;
                const isAbove = value != null && value >= 0;
                const Icon    = value == null ? Minus : isAbove ? TrendingUp : TrendingDown;
                return (
                  <div key={key} className="rounded-xl border border-white/5 bg-card p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <p className="text-[11px] text-muted-foreground">{label}</p>
                      <Icon className={cn("w-3.5 h-3.5", value == null ? "text-muted-foreground/30" : isAbove ? "text-emerald-400" : "text-amber-400")} />
                    </div>
                    <div className="flex items-baseline gap-1">
                      <GapValue value={value} />
                      <span className="text-xs text-muted-foreground">vs {threshold}</span>
                    </div>
                    <DimGapBar value={value} threshold={threshold} />
                  </div>
                );
              })}
            </div>

            {/* Recommendations preview */}
            {selectedGap && selectedGap.recommendations.length > 0 && (
              <div className="flex items-center justify-between p-4 rounded-xl border border-white/5 bg-card">
                <div className="flex items-center gap-3">
                  <Lightbulb className="w-4 h-4 text-signal shrink-0" />
                  <div>
                    <p className="text-sm font-medium">{selectedGap.recommendations.length} targeted recommendations</p>
                    <p className="text-xs text-muted-foreground">Specific projects to close your gap.</p>
                  </div>
                </div>
                <Button asChild size="sm" variant="outline" className="rounded-lg border-white/10 hover:bg-white/5 h-8 text-xs">
                  <Link href="/recommendations">
                    View all <ArrowRight className="ml-1 w-3 h-3" />
                  </Link>
                </Button>
              </div>
            )}

            {/* Role description */}
            {selectedRole.description && (
              <p className="text-xs text-muted-foreground leading-relaxed px-1">
                {selectedRole.description}
              </p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
