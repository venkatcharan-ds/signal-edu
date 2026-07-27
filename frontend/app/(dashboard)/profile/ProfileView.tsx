"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ScoreRing, ScoreBar } from "@/components/ui/score-ring";
import { Stagger, FadeUp } from "@/components/ui/motion";
import { CapabilityScoreCard } from "@/components/capability/CapabilityScoreCard";
import { EvidenceCitation } from "@/components/capability/EvidenceCitation";
import { useProfile } from "@/lib/hooks/useProfile";
import { signalComposite, DIMENSION_LABELS, type Dimension } from "@/types/signal";
import { Share2, ExternalLink, Zap, Code2, Target, MessageSquare } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

const DIMENSIONS: Dimension[] = ["technical_execution", "problem_complexity", "communication_quality"];

const DIM_ICON: Record<Dimension, React.ElementType> = {
  technical_execution:   Code2,
  problem_complexity:    Target,
  communication_quality: MessageSquare,
};

const CONFIDENCE_KEY: Record<Dimension, string> = {
  technical_execution:   "te_confidence",
  problem_complexity:    "pc_confidence",
  communication_quality: "cq_confidence",
};

const NARRATIVE_KEY: Record<Dimension, string> = {
  technical_execution:   "te_narrative",
  problem_complexity:    "pc_narrative",
  communication_quality: "cq_narrative",
};

type Tab = "scores" | "evidence" | "capabilities";

export function ProfileView() {
  const { profile, isLoading, isError } = useProfile();
  const [activeTab, setActiveTab] = useState<Tab>("scores");

  if (isLoading) return <ProfileSkeleton />;

  if (isError || !profile) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[40vh] text-center space-y-4">
        <div className="w-16 h-16 rounded-full bg-white/4 flex items-center justify-center mb-2">
          <Zap className="w-7 h-7 text-muted-foreground/40" />
        </div>
        <div className="space-y-1">
          <p className="font-medium">No profile yet</p>
          <p className="text-sm text-muted-foreground">Run your first analysis to generate a scored capability profile.</p>
        </div>
        <Button asChild className="rounded-xl bg-signal text-white hover:bg-signal/90 mt-2">
          <Link href="/analysis">
            <Zap className="mr-2 w-4 h-4" />
            Run analysis
          </Link>
        </Button>
      </div>
    );
  }

  const composite = signalComposite(profile);
  const verifiedCount = profile.verified_capabilities.length;
  const citationCount = profile.evidence_citations.length;

  return (
    <div className="space-y-10">
      {/* Header */}
      <FadeUp>
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">Capability Profile</h1>
            <p className="text-xs text-muted-foreground">
              Generated {new Date(profile.created_at).toLocaleDateString("en", { dateStyle: "medium" })}
              {" · "}
              {citationCount} evidence citation{citationCount !== 1 ? "s" : ""}
            </p>
          </div>
          <div className="flex gap-2 shrink-0">
            <Button variant="outline" size="sm" className="rounded-lg border-white/10 hover:bg-white/5 gap-2 h-8 text-xs">
              <Share2 className="w-3.5 h-3.5" />
              Share
            </Button>
            <Button variant="outline" size="sm" asChild className="rounded-lg border-white/10 hover:bg-white/5 gap-2 h-8 text-xs">
              <Link href={`/profile/${profile.user_id}`}>
                <ExternalLink className="w-3.5 h-3.5" />
                Public
              </Link>
            </Button>
          </div>
        </div>
      </FadeUp>

      {/* Score hero */}
      <FadeUp delay={0.04}>
        <div className="rounded-2xl border border-white/5 bg-card p-8">
          <div className="flex flex-col md:flex-row md:items-center gap-8">
            {/* Composite ring */}
            <div className="flex flex-col items-center gap-2 shrink-0">
              <ScoreRing score={composite} size={172} label="SIGNAL" sublabel="composite" />
              <div className="flex items-center gap-3 text-[11px] text-muted-foreground/60">
                <span>{verifiedCount} capabilities</span>
                <span>·</span>
                <span>{citationCount} citations</span>
              </div>
            </div>

            {/* Dimension bars */}
            <div className="flex-1 space-y-5">
              {DIMENSIONS.map((dim) => {
                const score = profile[dim as keyof typeof profile] as number | null;
                const Icon = DIM_ICON[dim];
                return (
                  <div key={dim} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <Icon className="w-3 h-3" />
                        {DIMENSION_LABELS[dim]}
                      </span>
                      <span className="text-sm font-semibold tabular-nums">
                        {score != null ? score.toFixed(1) : "—"}
                        <span className="text-muted-foreground font-normal"> / 9.0</span>
                      </span>
                    </div>
                    <ScoreBar score={score} />
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </FadeUp>

      {/* Verified capabilities highlight */}
      {verifiedCount > 0 && (
        <FadeUp delay={0.07}>
          <div className="rounded-2xl border border-signal/15 bg-signal-dim px-6 py-5">
            <div className="flex items-center gap-4">
              <div className="text-3xl font-bold text-signal score-glow tabular-nums shrink-0">
                {verifiedCount}
              </div>
              <div>
                <p className="text-sm font-medium">verified capabilities found in your work</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Extracted from your actual GitHub repositories — not self-reported.
                </p>
              </div>
            </div>
          </div>
        </FadeUp>
      )}

      {/* Tab navigation */}
      <FadeUp delay={0.1}>
        <div className="flex items-center gap-1 p-1 rounded-xl bg-white/4 border border-white/5 w-fit">
          {(["scores", "evidence", "capabilities"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                "relative px-4 py-1.5 rounded-lg text-xs font-medium transition-colors",
                activeTab === tab ? "text-foreground" : "text-muted-foreground hover:text-foreground"
              )}
            >
              {activeTab === tab && (
                <motion.div
                  layoutId="profile-tab"
                  className="absolute inset-0 bg-white/8 rounded-lg"
                  transition={{ type: "spring", bounce: 0.15, duration: 0.3 }}
                />
              )}
              <span className="relative capitalize">{tab}</span>
            </button>
          ))}
        </div>
      </FadeUp>

      {/* Tab content */}
      <AnimatePresence mode="wait">
        {activeTab === "scores" && (
          <motion.div
            key="scores"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          >
            <Stagger className="grid md:grid-cols-3 gap-4">
              {DIMENSIONS.map((dim) => (
                <motion.div
                  key={dim}
                  variants={{
                    hidden: { opacity: 0, y: 16 },
                    show:   { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] } },
                  }}
                >
                  <CapabilityScoreCard
                    dimension={dim}
                    score={profile[dim as keyof typeof profile] as number | null}
                    confidence={profile[CONFIDENCE_KEY[dim] as keyof typeof profile] as number | null}
                    percentile={null}
                    narrative={profile[NARRATIVE_KEY[dim] as keyof typeof profile] as string | null}
                  />
                </motion.div>
              ))}
            </Stagger>
          </motion.div>
        )}

        {activeTab === "evidence" && (
          <motion.div
            key="evidence"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="space-y-8"
          >
            {profile.evidence_citations.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-12">
                No evidence citations on this profile.
              </p>
            ) : (
              DIMENSIONS.map((dim) => {
                const dimCitations = profile.evidence_citations.filter((c) => c.dimension === dim);
                if (!dimCitations.length) return null;
                const Icon = DIM_ICON[dim];
                return (
                  <div key={dim} className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Icon className="w-3.5 h-3.5 text-muted-foreground" />
                      <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest">
                        {DIMENSION_LABELS[dim]}
                      </h3>
                      <span className="text-[11px] text-muted-foreground/50 ml-auto">
                        {dimCitations.length} citation{dimCitations.length !== 1 ? "s" : ""}
                      </span>
                    </div>
                    <div className="space-y-1.5">
                      {dimCitations.map((c) => (
                        <EvidenceCitation key={c.id} citation={c} />
                      ))}
                    </div>
                  </div>
                );
              })
            )}
          </motion.div>
        )}

        {activeTab === "capabilities" && (
          <motion.div
            key="capabilities"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          >
            {profile.verified_capabilities.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-12">
                No verified capabilities yet.
              </p>
            ) : (
              <div className="space-y-4">
                <p className="text-xs text-muted-foreground">
                  {verifiedCount} specific capabilities extracted from your GitHub repositories.
                </p>
                <div className="flex flex-wrap gap-2">
                  {profile.verified_capabilities.map((cap, i) => (
                    <motion.div
                      key={cap}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: i * 0.03, duration: 0.3 }}
                    >
                      <Badge
                        variant="secondary"
                        className="text-xs bg-white/5 text-foreground border border-white/8 rounded-full px-3 py-1.5 hover:bg-white/8 transition-colors"
                      >
                        {cap}
                      </Badge>
                    </motion.div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function ProfileSkeleton() {
  return (
    <div className="space-y-10">
      <div className="space-y-2">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-3.5 w-64" />
      </div>
      <Skeleton className="h-56 w-full rounded-2xl" />
      <Skeleton className="h-16 w-full rounded-2xl" />
      <div className="flex gap-2">
        {[1,2,3].map(i => <Skeleton key={i} className="h-7 w-24 rounded-lg" />)}
      </div>
      <div className="grid md:grid-cols-3 gap-4">
        {[0,1,2].map(i => <Skeleton key={i} className="h-48 rounded-2xl" />)}
      </div>
    </div>
  );
}
