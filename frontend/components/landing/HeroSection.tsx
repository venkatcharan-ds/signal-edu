"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function HeroSection() {
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center px-6 overflow-hidden">
      {/* Background mesh */}
      <div className="absolute inset-0 gradient-mesh pointer-events-none" />

      {/* Grid lines */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.025]"
        style={{
          backgroundImage:
            "linear-gradient(oklch(1 0 0) 1px, transparent 1px), linear-gradient(90deg, oklch(1 0 0) 1px, transparent 1px)",
          backgroundSize: "80px 80px",
        }}
      />

      <div className="relative z-10 max-w-4xl mx-auto text-center space-y-8">
        {/* Eyebrow tag */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        >
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/10 bg-white/5 text-xs text-muted-foreground tracking-widest uppercase">
            <span className="w-1.5 h-1.5 rounded-full bg-signal animate-pulse" />
            Evidence-based capability intelligence
          </span>
        </motion.div>

        {/* Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1], delay: 0.08 }}
          className="text-5xl sm:text-6xl md:text-7xl font-semibold tracking-tight leading-[1.05] text-foreground"
        >
          We surface the talent{" "}
          <span className="text-signal">credentials</span>{" "}
          hide.
        </motion.h1>

        {/* Subheading */}
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1], delay: 0.16 }}
          className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed"
        >
          SIGNAL analyzes your GitHub repositories and projects to generate an
          evidence-based capability profile — with scores your transcript never captured.
        </motion.p>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1], delay: 0.24 }}
          className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-2"
        >
          <Button asChild size="lg" className="h-12 px-7 text-sm font-medium rounded-full bg-foreground text-background hover:bg-foreground/90 transition-all">
            <Link href="/login">
              <GitHubIcon className="mr-2 h-4 w-4" />
              Get your capability profile
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
          <Button asChild variant="ghost" size="lg" className="h-12 px-6 text-sm rounded-full text-muted-foreground hover:text-foreground hover:bg-white/5">
            <Link href="/profile/signal-demo">
              View a sample profile
            </Link>
          </Button>
        </motion.div>

        {/* Social proof */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.5 }}
          className="text-xs text-muted-foreground/60 pt-2"
        >
          Free for students · Public repositories only · No write access
        </motion.p>
      </div>

      {/* Floating score preview */}
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: 0.5 }}
        className="relative z-10 mt-20 w-full max-w-3xl mx-auto"
      >
        <ScorePreviewCard />
      </motion.div>
    </section>
  );
}

function ScorePreviewCard() {
  const scores = [
    { label: "Technical Execution", score: 8.1, evidence: "Production deployment on constrained hardware · CI/CD pipeline present" },
    { label: "Problem Complexity",  score: 7.6, evidence: "Real-world agricultural dataset · Novel deployment context" },
    { label: "Communication Quality", score: 7.9, evidence: "Detailed READMEs · Hackathon presentation noted" },
  ];

  return (
    <div className="glass rounded-2xl p-6 md:p-8 relative overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-signal-dim border border-signal/20 flex items-center justify-center">
            <span className="text-signal text-sm font-bold">P</span>
          </div>
          <div>
            <p className="text-sm font-medium">Priya Sharma</p>
            <p className="text-xs text-muted-foreground">Data Science · Tier-3 College · CGPA 6.9</p>
          </div>
        </div>
        <div className="text-right">
          <span className="text-xs text-signal font-medium bg-signal-dim px-2 py-1 rounded-full">
            Top 18% Technical Execution
          </span>
        </div>
      </div>

      {/* Scores */}
      <div className="space-y-4">
        {scores.map((item, i) => (
          <motion.div
            key={item.label}
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.7 + i * 0.1, duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
            className="group"
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs text-muted-foreground">{item.label}</span>
              <span className="text-sm font-semibold text-foreground tabular-nums">
                {item.score} <span className="text-muted-foreground/50 font-normal text-xs">/ 9.0</span>
              </span>
            </div>
            <div className="h-1 rounded-full bg-white/5 overflow-hidden">
              <motion.div
                className="h-full rounded-full bg-signal"
                initial={{ width: 0 }}
                animate={{ width: `${(item.score / 9) * 100}%` }}
                transition={{ delay: 0.9 + i * 0.1, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
              />
            </div>
            <p className="mt-1 text-[11px] text-muted-foreground/60 leading-relaxed">{item.evidence}</p>
          </motion.div>
        ))}
      </div>

      {/* Footer tag */}
      <div className="mt-6 pt-5 border-t border-white/5 flex items-center gap-2">
        <span className="text-[11px] text-muted-foreground/50">13 verified capabilities found ·</span>
        <span className="text-[11px] text-muted-foreground/50">Resume listed 5</span>
        <span className="ml-auto text-[11px] text-signal font-medium">2.6× more than her resume</span>
      </div>
    </div>
  );
}

function GitHubIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
    </svg>
  );
}
