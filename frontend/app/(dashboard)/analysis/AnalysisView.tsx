"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { AnalysisProgress } from "@/components/analysis/AnalysisProgress";
import { useAnalysisStatus } from "@/lib/hooks/useAnalysisStatus";
import { useAnalysisHistory } from "@/lib/hooks/useAnalysisHistory";
import { useAnalysisQuota } from "@/lib/hooks/useAnalysisQuota";
import { startAnalysis, RateLimitError } from "@/lib/api";
import { FadeUp } from "@/components/ui/motion";
import { Zap, CheckCircle, AlertCircle, Clock, Loader2, Lock } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

type Stage = "idle" | "running" | "complete" | "failed" | "rate_limited";

function formatDate(iso: string) {
  return new Intl.RelativeTimeFormat("en", { numeric: "auto" }).format(
    Math.round((new Date(iso).getTime() - Date.now()) / (1000 * 60 * 60 * 24)),
    "day"
  );
}

function formatSecondsUntilReset(seconds: number): string {
  if (seconds <= 0) return "now";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

const STATUS_ICON: Record<string, React.ElementType> = {
  complete: CheckCircle,
  failed:   AlertCircle,
  queued:   Clock,
};

const STATUS_CLASS: Record<string, string> = {
  complete: "text-emerald-400",
  failed:   "text-red-400",
  queued:   "text-muted-foreground",
};

export function AnalysisView() {
  const [stage, setStage] = useState<Stage>("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [rateLimitMsg, setRateLimitMsg] = useState<string>("");
  const [retryAfterSecs, setRetryAfterSecs] = useState<number | null>(null);

  const { events, progress, isComplete, isFailed, latestLabel } = useAnalysisStatus(jobId);
  const { history, isLoading: historyLoading, refresh } = useAnalysisHistory();
  const { quota, isLoading: quotaLoading, canStart, refresh: refreshQuota } = useAnalysisQuota();

  const handleStart = async () => {
    setStage("running");
    try {
      const job = await startAnalysis();
      setJobId(job.id);
      refreshQuota();
    } catch (err) {
      if (err instanceof RateLimitError) {
        setRateLimitMsg(err.message);
        setRetryAfterSecs(err.retryAfter);
        setStage("rate_limited");
      } else {
        setStage("failed");
      }
    }
  };

  if (isComplete && stage === "running") { setStage("complete"); refresh(); refreshQuota(); }
  if (isFailed   && stage === "running") setStage("failed");

  const buttonDisabled = !canStart || stage === "running" || quotaLoading;

  return (
    <div className="space-y-10">
      <FadeUp>
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">Capability Analysis</h1>
          <p className="text-muted-foreground text-sm">
            SIGNAL analyzes your public GitHub repositories and generates an evidence-based capability profile.
          </p>
        </div>
      </FadeUp>

      {/* State machine */}
      <AnimatePresence mode="wait">
        {stage === "idle" && (
          <motion.div
            key="idle"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="space-y-6"
          >
            <div className="rounded-2xl border border-white/5 bg-card p-8 space-y-6">
              <h2 className="text-sm font-medium">What will be analyzed</h2>
              <div className="space-y-3">
                {ANALYSIS_ITEMS.map((item) => (
                  <div key={item.label} className="flex items-start gap-3">
                    <span className="w-1.5 h-1.5 rounded-full bg-signal mt-2 shrink-0" />
                    <div>
                      <p className="text-sm font-medium">{item.label}</p>
                      <p className="text-xs text-muted-foreground">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="pt-2 border-t border-white/5 text-xs text-muted-foreground/60 space-y-1">
                <p>• Only public repositories are analyzed</p>
                <p>• No write access to your GitHub account</p>
                <p>• Estimated time: 90–120 seconds</p>
              </div>
            </div>

            {/* Quota indicator */}
            {!quotaLoading && quota && (
              <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
                <span>
                  Daily quota: <span className="font-medium text-foreground">{quota.used_today}/{quota.limit}</span> used
                </span>
                <span className={cn(
                  "font-medium",
                  quota.remaining === 0 ? "text-red-400" : quota.remaining === 1 ? "text-amber-400" : "text-emerald-400"
                )}>
                  {quota.remaining} remaining
                </span>
              </div>
            )}

            <Button
              onClick={handleStart}
              disabled={buttonDisabled}
              className="w-full h-12 rounded-xl bg-signal text-white hover:bg-signal/90 font-medium shadow-[0_0_24px_oklch(0.65_0.19_259/20%)] disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
            >
              {quota?.has_active_job ? (
                <><Loader2 className="mr-2 w-4 h-4 animate-spin" />Analysis in progress</>
              ) : quota?.remaining === 0 ? (
                <><Lock className="mr-2 w-4 h-4" />Daily limit reached</>
              ) : (
                <><Zap className="mr-2 w-4 h-4" />Start analysis</>
              )}
            </Button>
          </motion.div>
        )}

        {stage === "running" && (
          <motion.div
            key="running"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="rounded-2xl border border-white/5 bg-card p-8 space-y-6"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-signal-dim border border-signal/20 flex items-center justify-center">
                <Zap className="w-4 h-4 text-signal animate-pulse" />
              </div>
              <div>
                <p className="text-sm font-medium">Analyzing your GitHub...</p>
                <p className="text-xs text-muted-foreground">Do not close this tab</p>
              </div>
              <span className="ml-auto text-sm font-semibold tabular-nums text-signal">{progress}%</span>
            </div>
            <Progress value={progress} className="h-1.5" />
            {latestLabel && (
              <p className="text-xs text-muted-foreground">{latestLabel}</p>
            )}
            <AnalysisProgress events={events} progress={progress} latestLabel={latestLabel} />
          </motion.div>
        )}

        {stage === "complete" && (
          <motion.div
            key="complete"
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
            className="rounded-2xl border border-signal/20 bg-signal-dim p-8 space-y-6 text-center"
          >
            <div className="flex justify-center">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.1, type: "spring", bounce: 0.4 }}
              >
                <CheckCircle className="w-12 h-12 text-signal" />
              </motion.div>
            </div>
            <div className="space-y-2">
              <h2 className="text-xl font-semibold">Analysis complete</h2>
              <p className="text-sm text-muted-foreground">
                Your capability profile has been generated with evidence citations.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button asChild className="rounded-xl bg-signal text-white hover:bg-signal/90">
                <Link href="/profile">View your profile</Link>
              </Button>
              <Button asChild variant="outline" className="rounded-xl border-white/10 hover:bg-white/5">
                <Link href="/gaps">Run gap analysis</Link>
              </Button>
            </div>
          </motion.div>
        )}

        {stage === "rate_limited" && (
          <motion.div
            key="rate_limited"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-8 space-y-4 text-center"
          >
            <Lock className="w-10 h-10 text-amber-400 mx-auto" />
            <div className="space-y-1">
              <p className="font-medium">Daily limit reached</p>
              <p className="text-sm text-muted-foreground">{rateLimitMsg}</p>
              {retryAfterSecs && (
                <p className="text-xs text-muted-foreground/60 mt-2">
                  Resets in {formatSecondsUntilReset(retryAfterSecs)}
                </p>
              )}
            </div>
            <Button
              onClick={() => { setStage("idle"); setJobId(null); }}
              variant="outline"
              className="rounded-xl border-white/10"
            >
              Back
            </Button>
          </motion.div>
        )}

        {stage === "failed" && (
          <motion.div
            key="failed"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-2xl border border-destructive/20 bg-destructive/5 p-8 space-y-4 text-center"
          >
            <AlertCircle className="w-10 h-10 text-destructive mx-auto" />
            <div className="space-y-1">
              <p className="font-medium">Analysis failed</p>
              <p className="text-sm text-muted-foreground">Something went wrong. Please try again.</p>
            </div>
            <Button onClick={() => { setStage("idle"); setJobId(null); }} variant="outline" className="rounded-xl border-white/10">
              Try again
            </Button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* History */}
      {!historyLoading && history.length > 0 && (
        <FadeUp delay={0.1}>
          <div className="space-y-3">
            <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-widest">History</h2>
            <div className="rounded-2xl border border-white/5 bg-card overflow-hidden divide-y divide-white/5">
              {history.map((job) => {
                const Icon = STATUS_ICON[job.status] ?? Loader2;
                const iconCn = STATUS_CLASS[job.status] ?? "text-signal";
                return (
                  <div key={job.id} className="flex items-center gap-4 px-5 py-3.5">
                    <Icon className={cn("w-4 h-4 shrink-0", iconCn, job.status === "queued" && "animate-pulse")} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-mono text-muted-foreground/70 truncate">{job.id.slice(0, 8)}…</p>
                      {job.current_step && (
                        <p className="text-[11px] text-muted-foreground/50 truncate">{job.current_step}</p>
                      )}
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-[11px] text-muted-foreground/50">{formatDate(job.started_at)}</p>
                      <p className="text-[11px] font-medium capitalize" style={{ color: job.status === "complete" ? "var(--signal)" : undefined }}>
                        {job.status}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </FadeUp>
      )}

      {historyLoading && (
        <div className="space-y-2">
          {[0,1,2].map(i => <Skeleton key={i} className="h-14 rounded-xl" />)}
        </div>
      )}
    </div>
  );
}

const ANALYSIS_ITEMS = [
  { label: "Repository signals",      desc: "Languages, commit history, file structure, stars" },
  { label: "Code quality indicators", desc: "Test coverage, CI/CD configs, deployment setups" },
  { label: "Documentation quality",   desc: "README depth, setup instructions, project clarity" },
  { label: "Problem complexity",      desc: "Multi-system integration, real-world usage, novelty" },
  { label: "AI capability scoring",   desc: "Claude Sonnet analyzes depth and communication quality" },
];
