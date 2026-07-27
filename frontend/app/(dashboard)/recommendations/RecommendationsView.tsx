"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { FadeUp } from "@/components/ui/motion";
import { RecommendationCard } from "@/components/gap/RecommendationCard";
import { useGapAnalyses } from "@/lib/hooks/useGapAnalyses";
import { DIMENSION_LABELS, type Dimension, type Recommendation } from "@/types/signal";
import { Lightbulb, Zap, Code2, Target, MessageSquare } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

type FilterDim = "all" | Dimension;

const FILTER_TABS: { key: FilterDim; label: string; icon: React.ElementType }[] = [
  { key: "all",                  label: "All",           icon: Lightbulb    },
  { key: "technical_execution",   label: "Technical",    icon: Code2        },
  { key: "problem_complexity",    label: "Complexity",   icon: Target       },
  { key: "communication_quality", label: "Communication",icon: MessageSquare },
];

interface RichRecommendation extends Recommendation {
  role_title: string;
  role_slug:  string;
}

export function RecommendationsView() {
  const { gaps, isLoading, isError } = useGapAnalyses();
  const [filter, setFilter] = useState<FilterDim>("all");

  // Flatten all recs from all gap analyses, tag with role info
  const allRecs: RichRecommendation[] = gaps
    .flatMap((g) =>
      g.recommendations.map((r) => ({
        ...r,
        role_title: g.role_title,
        role_slug:  g.role_slug,
      }))
    )
    .sort((a, b) => a.priority - b.priority);

  const filtered = filter === "all"
    ? allRecs
    : allRecs.filter((r) => r.dimension === filter);

  const counts: Record<FilterDim, number> = {
    all:                  allRecs.length,
    technical_execution:  allRecs.filter((r) => r.dimension === "technical_execution").length,
    problem_complexity:   allRecs.filter((r) => r.dimension === "problem_complexity").length,
    communication_quality: allRecs.filter((r) => r.dimension === "communication_quality").length,
  };

  return (
    <div className="space-y-10">
      <FadeUp>
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Recommendations</h1>
          <p className="text-muted-foreground text-sm">
            Evidence-backed projects to close the gap between where you are and your target role.
          </p>
        </div>
      </FadeUp>

      {/* Stats band */}
      {!isLoading && allRecs.length > 0 && (
        <FadeUp delay={0.04}>
          <div className="grid grid-cols-3 gap-3">
            {(["technical_execution", "problem_complexity", "communication_quality"] as Dimension[]).map((dim) => {
              const count = counts[dim];
              const icons: Record<Dimension, React.ElementType> = { technical_execution: Code2, problem_complexity: Target, communication_quality: MessageSquare };
              const colors: Record<Dimension, string> = { technical_execution: "text-signal", problem_complexity: "text-violet-400", communication_quality: "text-emerald-400" };
              const Icon = icons[dim];
              return (
                <button
                  key={dim}
                  onClick={() => setFilter(dim)}
                  className={cn(
                    "rounded-xl border p-4 text-left transition-all",
                    filter === dim ? "border-white/15 bg-white/5" : "border-white/5 bg-card hover:border-white/10"
                  )}
                >
                  <Icon className={cn("w-4 h-4 mb-2", colors[dim])} />
                  <p className="text-xl font-semibold tabular-nums">{count}</p>
                  <p className="text-[11px] text-muted-foreground mt-0.5">{DIMENSION_LABELS[dim]}</p>
                </button>
              );
            })}
          </div>
        </FadeUp>
      )}

      {/* Filter tabs */}
      {!isLoading && allRecs.length > 0 && (
        <FadeUp delay={0.07}>
          <div className="flex items-center gap-1 p-1 rounded-xl bg-white/4 border border-white/5 w-fit">
            {FILTER_TABS.map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setFilter(key)}
                className={cn(
                  "relative flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors",
                  filter === key ? "text-foreground" : "text-muted-foreground hover:text-foreground"
                )}
              >
                {filter === key && (
                  <motion.div
                    layoutId="rec-tab"
                    className="absolute inset-0 bg-white/8 rounded-lg"
                    transition={{ type: "spring", bounce: 0.15, duration: 0.3 }}
                  />
                )}
                <Icon className="relative w-3.5 h-3.5" />
                <span className="relative">{label}</span>
                {counts[key] > 0 && (
                  <span className="relative text-[10px] text-muted-foreground/60 tabular-nums">
                    {counts[key]}
                  </span>
                )}
              </button>
            ))}
          </div>
        </FadeUp>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-2xl" />
          ))}
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="rounded-2xl border border-destructive/20 bg-destructive/5 p-8 text-center">
          <p className="text-sm text-muted-foreground">Failed to load recommendations.</p>
        </div>
      )}

      {/* No profile */}
      {!isLoading && !isError && allRecs.length === 0 && (
        <FadeUp delay={0.06}>
          <div className="rounded-2xl border border-white/5 bg-card p-12 text-center space-y-4">
            <Lightbulb className="w-10 h-10 text-muted-foreground/30 mx-auto" />
            <div className="space-y-1">
              <p className="font-medium">No recommendations yet</p>
              <p className="text-sm text-muted-foreground">
                Recommendations are generated after your capability analysis completes.
              </p>
            </div>
            <Button asChild className="rounded-xl bg-signal text-white hover:bg-signal/90">
              <Link href="/analysis"><Zap className="mr-2 w-4 h-4" />Start analysis</Link>
            </Button>
          </div>
        </FadeUp>
      )}

      {/* Recommendation list */}
      <AnimatePresence mode="wait">
        {!isLoading && filtered.length > 0 && (
          <motion.div
            key={filter}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="space-y-3"
          >
            {/* Role group headers if showing all */}
            {filter === "all" ? (
              (() => {
                // Group by role
                const byRole: Record<string, RichRecommendation[]> = {};
                for (const r of filtered) {
                  if (!byRole[r.role_slug]) byRole[r.role_slug] = [];
                  byRole[r.role_slug].push(r);
                }
                return Object.entries(byRole).map(([slug, recs]) => (
                  <div key={slug} className="space-y-2">
                    <p className="text-xs text-muted-foreground/60 font-medium uppercase tracking-widest px-1">
                      {recs[0].role_title}
                    </p>
                    {recs.map((rec, i) => (
                      <RecommendationCard key={rec.id} recommendation={rec} index={i} />
                    ))}
                  </div>
                ));
              })()
            ) : (
              filtered.map((rec, i) => (
                <RecommendationCard key={rec.id} recommendation={rec} index={i} />
              ))
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
