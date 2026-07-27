"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { DIMENSION_LABELS, type Recommendation } from "@/types/signal";
import { Code2, Target, MessageSquare, Zap } from "lucide-react";

interface Props {
  recommendation: Recommendation;
  index?: number;
}

const DIM_ICON = {
  technical_execution:   Code2,
  problem_complexity:    Target,
  communication_quality: MessageSquare,
} as const;

const DIM_COLOR = {
  technical_execution:   "text-signal bg-signal/10 border-signal/15",
  problem_complexity:    "text-violet-400 bg-violet-400/10 border-violet-400/15",
  communication_quality: "text-emerald-400 bg-emerald-400/10 border-emerald-400/15",
} as const;

const PRIORITY_COLOR = ["text-signal", "text-violet-400", "text-emerald-400"];

export function RecommendationCard({ recommendation, index = 0 }: Props) {
  const Icon = DIM_ICON[recommendation.dimension] ?? Zap;
  const dimColor = DIM_COLOR[recommendation.dimension];
  const numColor = PRIORITY_COLOR[Math.min(index, PRIORITY_COLOR.length - 1)];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1], delay: index * 0.06 }}
      className="group relative rounded-2xl border border-white/5 bg-card hover:border-white/10 transition-all hover-border-glow"
    >
      <div className="flex gap-5 p-5">
        {/* Priority number */}
        <div className="shrink-0 flex flex-col items-center gap-2 pt-0.5">
          <span className={cn("text-3xl font-semibold tabular-nums leading-none", numColor)}>
            {index + 1}
          </span>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-3">
          {/* Badges */}
          <div className="flex flex-wrap items-center gap-2">
            <span className={cn(
              "inline-flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-full border",
              dimColor
            )}>
              <Icon className="w-3 h-3" />
              {DIMENSION_LABELS[recommendation.dimension]}
            </span>
            {recommendation.evidence_type && (
              <span className="text-[11px] text-muted-foreground px-2 py-0.5 rounded-full bg-white/4 border border-white/5">
                {recommendation.evidence_type.replace(/_/g, " ")}
              </span>
            )}
          </div>

          {/* Title */}
          <h3 className="text-sm font-semibold leading-snug">{recommendation.title}</h3>

          {/* Description */}
          <p className="text-xs text-muted-foreground leading-relaxed">
            {recommendation.description}
          </p>
        </div>
      </div>
    </motion.div>
  );
}
