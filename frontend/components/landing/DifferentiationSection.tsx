"use client";

import { FadeUp, Stagger } from "@/components/ui/motion";
import { motion } from "framer-motion";
import { X, Check } from "lucide-react";

const comparisons = [
  { platform: "LinkedIn",  claim: "Self-reported skills",       signal: "Evidence extracted from actual artifacts" },
  { platform: "GitHub",    claim: "Raw code, no interpretation", signal: "Scored capability profile with citations"  },
  { platform: "Resume",    claim: "Claims without evidence",     signal: "Every score anchored to a specific artifact" },
  { platform: "LeetCode",  claim: "Performance on artificial tasks", signal: "Performance on real project history" },
];

export function DifferentiationSection() {
  return (
    <section className="py-32 px-6 bg-card/30">
      <div className="max-w-5xl mx-auto">
        <FadeUp className="text-center mb-20">
          <p className="text-xs uppercase tracking-widest text-signal mb-4">Why SIGNAL</p>
          <h2 className="text-4xl md:text-5xl font-semibold tracking-tight">
            Not a resume builder.
            <br className="hidden sm:block" /> Not LinkedIn. Not GitHub.
          </h2>
          <p className="mt-6 text-muted-foreground max-w-2xl mx-auto text-lg">
            Every other tool shows what you claim. SIGNAL shows what the evidence demonstrates.
          </p>
        </FadeUp>

        <Stagger className="space-y-2">
          {comparisons.map((item) => (
            <motion.div
              key={item.platform}
              variants={{
                hidden: { opacity: 0, x: -16 },
                show:   { opacity: 1, x: 0, transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] } },
              }}
              className="grid grid-cols-[140px_1fr_1fr] md:grid-cols-[180px_1fr_1fr] items-center gap-4 p-5 rounded-xl border border-white/5 bg-card hover-border-glow group"
            >
              <span className="text-sm font-medium text-muted-foreground">{item.platform}</span>
              <div className="flex items-center gap-2.5">
                <X className="w-3.5 h-3.5 text-muted-foreground/40 shrink-0" />
                <span className="text-sm text-muted-foreground/70">{item.claim}</span>
              </div>
              <div className="flex items-center gap-2.5">
                <Check className="w-3.5 h-3.5 text-signal shrink-0" />
                <span className="text-sm text-foreground">{item.signal}</span>
              </div>
            </motion.div>
          ))}
        </Stagger>
      </div>
    </section>
  );
}
