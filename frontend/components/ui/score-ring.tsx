"use client";

import { motion } from "framer-motion";
import { asFiniteNumber } from "@/lib/utils";

interface ScoreRingProps {
  score: number | null;
  size?: number;      // px, default 160
  strokeWidth?: number;
  label?: string;
  sublabel?: string;
  className?: string;
}

export function ScoreRing({
  score: scoreProp,
  size = 160,
  strokeWidth = 10,
  label,
  sublabel,
  className = "",
}: ScoreRingProps) {
  const score = asFiniteNumber(scoreProp);
  const R   = (size - strokeWidth * 2) / 2;
  const C   = 2 * Math.PI * R;
  const pct = score != null ? score / 9 : 0;
  const fill = pct * C;

  const cx = size / 2;
  const cy = size / 2;

  // Color: emerald for advanced, signal blue for developing, orange for emerging
  const trackColor = "oklch(1 0 0 / 6%)";
  const arcColor = score == null
    ? "oklch(1 0 0 / 15%)"
    : score > 6
      ? "oklch(0.76 0.18 155)"   // emerald
      : score > 3
        ? "oklch(0.65 0.19 259)"  // signal blue
        : "oklch(0.73 0.19 53)";  // amber

  return (
    <div className={`relative inline-flex items-center justify-center ${className}`} style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ transform: "rotate(-90deg)" }}
        aria-hidden
      >
        {/* Track */}
        <circle
          cx={cx}
          cy={cy}
          r={R}
          fill="none"
          stroke={trackColor}
          strokeWidth={strokeWidth}
        />
        {/* Arc */}
        {score != null && (
          <motion.circle
            cx={cx}
            cy={cy}
            r={R}
            fill="none"
            stroke={arcColor}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={`${fill} ${C}`}
            initial={{ strokeDasharray: `0 ${C}` }}
            animate={{ strokeDasharray: `${fill} ${C}` }}
            transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
          />
        )}
      </svg>

      {/* Center content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        {score != null ? (
          <motion.span
            className="font-semibold tabular-nums leading-none"
            style={{ fontSize: size * 0.22 }}
            initial={{ opacity: 0, scale: 0.7 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1], delay: 0.35 }}
          >
            {score.toFixed(1)}
          </motion.span>
        ) : (
          <span className="text-muted-foreground/30 font-semibold" style={{ fontSize: size * 0.22 }}>—</span>
        )}
        {label && (
          <span
            className="text-muted-foreground mt-1 font-medium tracking-wide"
            style={{ fontSize: size * 0.07 }}
          >
            {label}
          </span>
        )}
        {sublabel && (
          <span
            className="text-muted-foreground/50"
            style={{ fontSize: size * 0.06 }}
          >
            {sublabel}
          </span>
        )}
      </div>
    </div>
  );
}

// Mini horizontal bar variant for dimension rows
export function ScoreBar({
  score: scoreProp,
  max = 9,
  color,
}: {
  score: number | null;
  max?: number;
  color?: string;
}) {
  const score = asFiniteNumber(scoreProp);
  const pct = score != null ? (score / max) * 100 : 0;
  const barColor = color ?? (
    score == null ? undefined
    : score > 6   ? "bg-emerald-400"
    : score > 3   ? "bg-signal"
    :               "bg-amber-400"
  );

  return (
    <div className="h-1 w-full rounded-full bg-white/5 overflow-hidden">
      <motion.div
        className={`h-full rounded-full ${barColor}`}
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1], delay: 0.2 }}
      />
    </div>
  );
}
