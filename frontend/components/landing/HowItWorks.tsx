"use client";

import { motion } from "framer-motion";
import { Stagger, FadeUp } from "@/components/ui/motion";
import { GitBranch, Cpu, Share2 } from "lucide-react";

const steps = [
  {
    icon: GitBranch,
    step: "01",
    title: "Connect GitHub",
    description:
      "One-click sign-in with GitHub. SIGNAL immediately begins reading your public repositories — no manual uploads required.",
  },
  {
    icon: Cpu,
    step: "02",
    title: "AI analysis runs",
    description:
      "Our pipeline extracts objective signals from your code — languages, test coverage, CI/CD, deployment configs — then Claude evaluates depth and complexity.",
  },
  {
    icon: Share2,
    step: "03",
    title: "Share your profile",
    description:
      "Within minutes you have a public URL. Every score is anchored to a specific artifact. Send it to recruiters instead of, or alongside, your resume.",
  },
];

export function HowItWorks() {
  return (
    <section className="py-32 px-6">
      <div className="max-w-5xl mx-auto">
        <FadeUp className="text-center mb-20">
          <p className="text-xs uppercase tracking-widest text-signal mb-4">How it works</p>
          <h2 className="text-4xl md:text-5xl font-semibold tracking-tight">
            From GitHub to capability profile
            <br className="hidden sm:block" /> in under 4 minutes.
          </h2>
        </FadeUp>

        <Stagger className="grid md:grid-cols-3 gap-px bg-white/5 rounded-2xl overflow-hidden">
          {steps.map((step) => {
            const Icon = step.icon;
            return (
              <motion.div
                key={step.step}
                variants={{
                  hidden: { opacity: 0, y: 20 },
                  show:   { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
                }}
                className="bg-card p-8 md:p-10 space-y-5 hover-border-glow group"
              >
                <div className="flex items-start justify-between">
                  <div className="w-10 h-10 rounded-xl bg-signal-dim border border-signal/15 flex items-center justify-center group-hover:border-signal/30 transition-colors">
                    <Icon className="w-5 h-5 text-signal" />
                  </div>
                  <span className="text-xs font-mono text-muted-foreground/30">{step.step}</span>
                </div>
                <h3 className="text-lg font-semibold">{step.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{step.description}</p>
              </motion.div>
            );
          })}
        </Stagger>
      </div>
    </section>
  );
}
