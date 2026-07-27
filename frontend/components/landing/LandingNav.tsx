"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";

export function LandingNav() {
  return (
    <motion.header
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="fixed top-0 left-0 right-0 z-50"
    >
      <div className="max-w-6xl mx-auto px-6 py-4">
        <nav className="flex items-center justify-between glass rounded-2xl px-5 py-3">
          <Link href="/" className="font-semibold text-sm tracking-tight">
            SIGNAL
          </Link>

          <div className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
            <Link href="#how-it-works" className="hover:text-foreground transition-colors">
              How it works
            </Link>
            <Link href="#why-signal" className="hover:text-foreground transition-colors">
              Why SIGNAL
            </Link>
          </div>

          <div className="flex items-center gap-3">
            <Button asChild variant="ghost" size="sm" className="text-sm text-muted-foreground hover:text-foreground rounded-full">
              <Link href="/login">Sign in</Link>
            </Button>
            <Button asChild size="sm" className="text-sm rounded-full bg-foreground text-background hover:bg-foreground/90 h-8 px-4">
              <Link href="/login">Get profile</Link>
            </Button>
          </div>
        </nav>
      </div>
    </motion.header>
  );
}

export function LandingFooter() {
  return (
    <footer className="border-t border-white/5 py-12 px-6">
      <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div>
          <span className="font-semibold text-sm">SIGNAL</span>
          <p className="text-xs text-muted-foreground mt-1">
            We surface the talent that credentials hide.
          </p>
        </div>
        <p className="text-xs text-muted-foreground">
          2026 Cintana Alliance AI Challenge · Built for students
        </p>
      </div>
    </footer>
  );
}
