"use client";

import { motion } from "framer-motion";
import type { AnalysisProgressEvent } from "@/types/signal";
import { CheckCircle, Circle } from "lucide-react";

interface Props {
  events: AnalysisProgressEvent[];
  progress: number;
  latestLabel: string | null;
}

export function AnalysisProgress({ events }: Props) {
  if (!events.length) return null;

  return (
    <div className="space-y-2">
      {events.map((event, i) => {
        const isDone = i < events.length - 1;
        return (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="flex items-start gap-3"
          >
            {isDone ? (
              <CheckCircle className="w-3.5 h-3.5 text-signal mt-0.5 shrink-0" />
            ) : (
              <Circle className="w-3.5 h-3.5 text-muted-foreground/30 mt-0.5 shrink-0 animate-pulse" />
            )}
            <div>
              <p className={`text-xs ${isDone ? "text-muted-foreground" : "text-foreground"}`}>
                {event.label}
              </p>
              {event.detail && (
                <p className="text-[11px] text-muted-foreground/60 mt-0.5">{event.detail}</p>
              )}
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
