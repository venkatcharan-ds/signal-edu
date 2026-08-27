"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, GitBranch, FileText, GitCommit, Workflow, Container, Code2, ExternalLink } from "lucide-react";
import { cn, asFiniteNumber } from "@/lib/utils";
import type { EvidenceCitation as EvidenceCitationType } from "@/types/signal";

interface Props {
  citation: EvidenceCitationType;
  compact?: boolean;
}

const ARTIFACT_META: Record<string, { icon: React.ElementType; label: string; color: string }> = {
  github_repo:        { icon: GitBranch,  label: "Repository",       color: "text-signal" },
  repository:         { icon: GitBranch,  label: "Repository",       color: "text-signal" },
  readme:             { icon: FileText,   label: "README",           color: "text-emerald-400" },
  commit_history:     { icon: GitCommit,  label: "Commit History",   color: "text-violet-400" },
  ci_workflow:        { icon: Workflow,   label: "CI Workflow",      color: "text-blue-400" },
  deployment_config:  { icon: Container, label: "Deployment",       color: "text-orange-400" },
  language_signal:    { icon: Code2,      label: "Language Signal",  color: "text-pink-400" },
  pdf:                { icon: FileText,   label: "Document",         color: "text-amber-400" },
  link:               { icon: ExternalLink, label: "Link",           color: "text-cyan-400" },
};

const DEFAULT_META = { icon: FileText, label: "Evidence", color: "text-muted-foreground" };

export function EvidenceCitation({ citation, compact = false }: Props) {
  const [expanded, setExpanded] = useState(false);
  const meta = ARTIFACT_META[citation.artifact_type ?? ""] ?? DEFAULT_META;
  const Icon = meta.icon;
  const scoreContrib = asFiniteNumber(citation.score_contribution);

  const hasDetails = !!(citation.artifact_ref || scoreContrib != null);

  return (
    <div
      className={cn(
        "rounded-xl border border-white/5 bg-white/[0.02] transition-colors",
        hasDetails && !compact && "cursor-pointer hover:border-white/10 hover:bg-white/[0.03]"
      )}
      onClick={() => hasDetails && !compact && setExpanded((p) => !p)}
      role={hasDetails && !compact ? "button" : undefined}
      aria-expanded={expanded}
    >
      <div className="flex items-start gap-3 px-4 py-3">
        {/* Artifact type icon */}
        <div className="mt-0.5 shrink-0">
          <Icon className={cn("w-3.5 h-3.5", meta.color)} />
        </div>

        {/* Citation text */}
        <p className="flex-1 text-xs text-foreground/80 leading-relaxed">
          {citation.citation_text}
        </p>

        {/* Expand toggle */}
        {hasDetails && !compact && (
          <ChevronDown
            className={cn(
              "w-3.5 h-3.5 text-muted-foreground/40 shrink-0 mt-0.5 transition-transform",
              expanded && "rotate-180"
            )}
          />
        )}
      </div>

      {/* Expanded details */}
      <AnimatePresence>
        {expanded && hasDetails && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="border-t border-white/5 px-4 py-3 flex items-center gap-4">
              <span className={cn("text-[11px] font-medium uppercase tracking-widest", meta.color)}>
                {meta.label}
              </span>
              {citation.artifact_ref && (
                <span className="text-[11px] text-muted-foreground font-mono truncate">
                  {citation.artifact_ref}
                </span>
              )}
              {scoreContrib != null && scoreContrib > 0 && (
                <span className="ml-auto text-[11px] text-signal shrink-0">
                  +{scoreContrib.toFixed(2)} pts
                </span>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
