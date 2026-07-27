"use client";

import { motion } from "framer-motion";
import { FadeUp } from "@/components/ui/motion";

const stats = [
  { value: "2.7×",  label: "more verified capabilities found vs. self-reported resume skills" },
  { value: "< 4m",  label: "from GitHub sign-in to full capability profile" },
  { value: "10",    label: "target roles with gap analysis and specific recommendations" },
  { value: "9.0",   label: "point scale with evidence citations for every dimension" },
];

export function StatsSection() {
  return (
    <section className="py-32 px-6">
      <div className="max-w-5xl mx-auto">
        <FadeUp className="text-center mb-20">
          <p className="text-xs uppercase tracking-widest text-signal mb-4">By the numbers</p>
          <h2 className="text-4xl md:text-5xl font-semibold tracking-tight">
            Built for the student the
            <br className="hidden sm:block" /> credential system missed.
          </h2>
        </FadeUp>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-white/5 rounded-2xl overflow-hidden">
          {stats.map((stat, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              className="bg-card px-6 py-10 text-center space-y-3"
            >
              <p className="text-4xl md:text-5xl font-semibold tracking-tight text-signal score-glow">
                {stat.value}
              </p>
              <p className="text-xs text-muted-foreground leading-relaxed">{stat.label}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
