"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";

export function CtaSection() {
  return (
    <section className="py-32 px-6">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className="max-w-2xl mx-auto text-center space-y-8"
      >
        <div className="relative inline-block">
          <div className="absolute inset-0 blur-3xl bg-signal/20 rounded-full" />
          <h2 className="relative text-4xl md:text-5xl font-semibold tracking-tight">
            Your transcript doesn&apos;t show
            <br className="hidden sm:block" /> what you can actually do.
          </h2>
        </div>

        <p className="text-lg text-muted-foreground leading-relaxed">
          SIGNAL does. Connect your GitHub and get your capability profile in minutes.
        </p>

        <Button
          asChild
          size="lg"
          className="h-13 px-8 text-sm font-medium rounded-full bg-signal text-white hover:bg-signal/90 transition-all shadow-[0_0_30px_oklch(0.65_0.19_259/25%)]"
        >
          <Link href="/login">
            Get your profile — it&apos;s free
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>

        <p className="text-xs text-muted-foreground/50">
          No email required. Sign in with GitHub in one click.
        </p>
      </motion.div>
    </section>
  );
}
