"use client";

import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { ScoreBar } from "@/components/ui/score-ring";
import { DIMENSION_LABELS, SCORE_BAND, SCORE_BAND_LABEL, type Dimension } from "@/types/signal";
import { cn, asFiniteNumber } from "@/lib/utils";
import { Code2, Target, MessageSquare } from "lucide-react";

interface Props {
  dimension: Dimension;
  score: number | null;
  confidence: number | null;
  percentile: number | null;
  narrative?: string | null;
}

const BAND_STYLE = {
  emerging:   "bg-amber-500/10 text-amber-400 border border-amber-500/15",
  developing: "bg-signal/10 text-signal border border-signal/15",
  advanced:   "bg-emerald-500/10 text-emerald-400 border border-emerald-500/15",
};

const DIM_ICON: Record<Dimension, React.ElementType> = {
  technical_execution:   Code2,
  problem_complexity:    Target,
  communication_quality: MessageSquare,
};

const DIM_COLOR: Record<Dimension, string> = {
  technical_execution:   "text-signal",
  problem_complexity:    "text-violet-400",
  communication_quality: "text-emerald-400",
};

export function CapabilityScoreCard({ dimension, score: scoreProp, confidence: confidenceProp, percentile: percentileProp, narrative }: Props) {
  const score      = asFiniteNumber(scoreProp);
  const confidence = asFiniteNumber(confidenceProp);
  const percentile = asFiniteNumber(percentileProp);
  const label  = DIMENSION_LABELS[dimension];
  const band   = score != null ? SCORE_BAND(score) : null;
  const Icon   = DIM_ICON[dimension];
  const iconCn = DIM_COLOR[dimension];

  return (
    <div className="rounded-2xl border border-white/5 bg-card p-5 space-y-4 hover-border-glow transition-all">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Icon className={cn("w-3.5 h-3.5", iconCn)} />
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
      </div>

      {/* Score */}
      <div className="flex items-baseline gap-2">
        {score != null ? (
          <motion.span
            className="text-4xl font-semibold tabular-nums leading-none score-glow"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
          >
            {score.toFixed(1)}
          </motion.span>
        ) : (
          <span className="text-4xl font-semibold text-muted-foreground/30 leading-none">—</span>
        )}
        <span className="text-sm text-muted-foreground">/ 9.0</span>
      </div>

      {/* Progress bar */}
      <ScoreBar score={score} />

      {/* Badges row */}
      <div className="flex flex-wrap items-center gap-2">
        {band && (
          <Badge className={cn("text-[11px] rounded-full px-2.5 py-0.5 font-medium", BAND_STYLE[band])}>
            {SCORE_BAND_LABEL[band]}
          </Badge>
        )}
        {confidence != null && (
          <span className="text-[11px] text-muted-foreground ml-auto">
            {Math.round(confidence * 100)}% confidence
          </span>
        )}
        {percentile != null && (
          <span className="text-[11px] text-muted-foreground">
            Top {100 - percentile}%
          </span>
        )}
      </div>

      {/* Narrative */}
      {narrative && (
        <p className="text-xs text-muted-foreground leading-relaxed border-t border-white/5 pt-3">
          {narrative}
        </p>
      )}
    </div>
  );
}
