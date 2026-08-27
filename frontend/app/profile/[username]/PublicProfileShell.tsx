"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Stagger, FadeUp } from "@/components/ui/motion";
import {
  DIMENSION_LABELS,
  SCORE_BAND,
  SCORE_BAND_LABEL,
  signalComposite,
  type Dimension,
  type PublicProfile,
} from "@/types/signal";
import { Share2, ExternalLink, UserX, Zap } from "lucide-react";
import { cn, asFiniteNumber } from "@/lib/utils";

const DIMENSIONS: Dimension[] = [
  "technical_execution",
  "problem_complexity",
  "communication_quality",
];

const DIM_COLOR: Record<Dimension, string> = {
  technical_execution:   "bg-signal",
  problem_complexity:    "bg-violet-500",
  communication_quality: "bg-emerald-500",
};

interface Props {
  username: string;
  data: PublicProfile | null;
}

export function PublicProfileShell({ username, data }: Props) {
  const handleShare = () => {
    navigator.clipboard?.writeText(window.location.href);
  };

  // ── 404 state ──────────────────────────────────────────────────────────────
  if (!data) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center px-6 text-center gap-6">
        <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/8 flex items-center justify-center">
          <UserX className="w-8 h-8 text-muted-foreground/40" />
        </div>
        <div className="space-y-2">
          <h1 className="text-xl font-semibold">Profile not found</h1>
          <p className="text-sm text-muted-foreground max-w-sm">
            <span className="font-mono text-foreground">@{username}</span> hasn't generated a SIGNAL capability profile yet.
          </p>
        </div>
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <Button asChild className="rounded-lg bg-signal text-white hover:bg-signal/90 gap-1.5">
            <Link href="/login">
              <Zap className="w-3.5 h-3.5" />
              Get your profile
            </Link>
          </Button>
          <Button asChild variant="outline" size="sm" className="rounded-lg border-white/10">
            <Link href="/">Back to SIGNAL</Link>
          </Button>
        </div>
      </main>
    );
  }

  // ── No profile generated yet ───────────────────────────────────────────────
  if (!data.profile) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center px-6 text-center gap-6">
        <div className="space-y-2">
          <h1 className="text-xl font-semibold">@{data.github_username}</h1>
          <p className="text-sm text-muted-foreground">
            This user hasn&apos;t run a capability analysis yet.
          </p>
        </div>
        <Button asChild className="rounded-lg bg-signal text-white hover:bg-signal/90 gap-1.5">
          <Link href="/login">
            <Zap className="w-3.5 h-3.5" />
            Get your profile
          </Link>
        </Button>
      </main>
    );
  }

  const profile = data.profile;
  const composite = signalComposite(profile);
  const displayName = data.full_name ?? `@${data.github_username}`;

  // ── Full profile ───────────────────────────────────────────────────────────
  return (
    <main className="min-h-screen pb-20">
      {/* Header */}
      <header className="border-b border-white/5 px-6 py-4 flex items-center justify-between">
        <Link href="/" className="text-sm font-semibold tracking-tight">SIGNAL</Link>
        <Button
          onClick={handleShare}
          variant="ghost"
          size="sm"
          className="text-xs text-muted-foreground hover:text-foreground gap-1.5 h-8 rounded-lg"
        >
          <Share2 className="w-3.5 h-3.5" />
          Copy link
        </Button>
      </header>

      <div className="max-w-3xl mx-auto px-6 pt-12 space-y-12">

        {/* Identity */}
        <FadeUp>
          <div className="flex items-start gap-4">
            {data.github_avatar ? (
              <Image
                src={data.github_avatar}
                alt={displayName}
                width={56}
                height={56}
                className="rounded-full shrink-0"
              />
            ) : (
              <div className="w-14 h-14 rounded-full bg-signal-dim border border-signal/20 flex items-center justify-center text-xl font-semibold text-signal shrink-0">
                {displayName[0].toUpperCase()}
              </div>
            )}
            <div className="space-y-1 min-w-0">
              <h1 className="text-2xl font-semibold tracking-tight">{displayName}</h1>
              {data.institution && (
                <p className="text-sm text-muted-foreground">{data.institution}</p>
              )}
              <div className="flex items-center gap-2 pt-1 flex-wrap">
                {composite != null && (
                  <Badge
                    variant="secondary"
                    className="text-[11px] bg-signal-dim text-signal border border-signal/20 rounded-full px-2.5"
                  >
                    SIGNAL {composite}/9.0
                  </Badge>
                )}
                <Badge
                  variant="secondary"
                  className="text-[11px] bg-white/5 border border-white/8 rounded-full px-2.5"
                >
                  {data.verified_capability_count} verified capabilities
                </Badge>
              </div>
            </div>
          </div>
        </FadeUp>

        {/* Dimension scores */}
        <div className="space-y-4">
          <FadeUp delay={0.06}>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-widest">
              Capability Scores
            </p>
          </FadeUp>
          <Stagger className="grid sm:grid-cols-3 gap-3">
            {DIMENSIONS.map((dim) => {
              const score = asFiniteNumber(profile[dim as keyof typeof profile] as number | null);
              if (score == null) return null;
              const band = SCORE_BAND(score);
              return (
                <motion.div
                  key={dim}
                  variants={{
                    hidden: { opacity: 0, y: 16 },
                    show:   { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] } },
                  }}
                  className="rounded-2xl border border-white/5 bg-card p-5 space-y-3"
                >
                  <p className="text-xs text-muted-foreground">{DIMENSION_LABELS[dim]}</p>
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-3xl font-semibold tabular-nums text-foreground">
                      {score.toFixed(1)}
                    </span>
                    <span className="text-sm text-muted-foreground">/ 9.0</span>
                  </div>
                  <div className="space-y-1.5">
                    <div className="h-1 rounded-full bg-white/5 overflow-hidden">
                      <motion.div
                        className={cn("h-full rounded-full", DIM_COLOR[dim])}
                        initial={{ width: 0 }}
                        whileInView={{ width: `${(score / 9) * 100}%` }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.8, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
                      />
                    </div>
                    <Badge
                      variant="secondary"
                      className="text-[10px] bg-white/5 border border-white/8 rounded-full px-2"
                    >
                      {SCORE_BAND_LABEL[band]}
                    </Badge>
                  </div>
                </motion.div>
              );
            })}
          </Stagger>
        </div>

        {/* Evidence citations */}
        {profile.evidence_citations.length > 0 && (
          <div className="space-y-4">
            <FadeUp delay={0.12}>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-widest">
                Evidence Citations
              </p>
            </FadeUp>
            <Stagger className="space-y-3">
              {DIMENSIONS.map((dim) => {
                const cits = profile.evidence_citations.filter((c) => c.dimension === dim);
                if (!cits.length) return null;
                return (
                  <motion.div
                    key={dim}
                    variants={{
                      hidden: { opacity: 0, x: -12 },
                      show:   { opacity: 1, x: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } },
                    }}
                    className="space-y-2"
                  >
                    <p className="text-xs text-muted-foreground font-medium">
                      {DIMENSION_LABELS[dim]}
                    </p>
                    {cits.map((c) => (
                      <div
                        key={c.id}
                        className="flex gap-3 p-3 rounded-xl bg-white/3 border border-white/5 text-sm"
                      >
                        <span className="text-signal mt-0.5 shrink-0">↳</span>
                        <p className="text-muted-foreground leading-relaxed">
                          {c.citation_text}
                          {c.artifact_ref && (
                            <span className="ml-2 font-mono text-[11px] text-muted-foreground/50">
                              {c.artifact_ref}
                            </span>
                          )}
                        </p>
                      </div>
                    ))}
                  </motion.div>
                );
              })}
            </Stagger>
          </div>
        )}

        {/* Verified capabilities */}
        {profile.verified_capabilities.length > 0 && (
          <FadeUp delay={0.18}>
            <div className="space-y-4">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-widest">
                Verified Capabilities
              </p>
              <div className="flex flex-wrap gap-2">
                {profile.verified_capabilities.map((cap) => (
                  <Badge
                    key={cap}
                    variant="secondary"
                    className="text-xs bg-white/5 border border-white/8 text-foreground rounded-full px-3 py-1"
                  >
                    {cap}
                  </Badge>
                ))}
              </div>
            </div>
          </FadeUp>
        )}

        {/* Footer CTA */}
        <FadeUp delay={0.22}>
          <div className="rounded-2xl border border-white/5 bg-card p-6 flex flex-col sm:flex-row items-start sm:items-center gap-4 justify-between">
            <div className="space-y-1">
              <p className="text-sm font-medium">Get your capability profile</p>
              <p className="text-xs text-muted-foreground">Connect your GitHub. Free for students.</p>
            </div>
            <Button asChild size="sm" className="rounded-lg bg-signal text-white hover:bg-signal/90 shrink-0 gap-1.5">
              <Link href="/login">
                <ExternalLink className="w-3.5 h-3.5" />
                Start for free
              </Link>
            </Button>
          </div>
        </FadeUp>
      </div>
    </main>
  );
}
