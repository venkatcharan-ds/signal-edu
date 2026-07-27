"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";
import { motion } from "framer-motion";

/**
 * Transient page shown after OAuth code exchange.
 *
 * Sends the GitHub provider_token to POST /v1/auth/sync so the backend
 * can call the GitHub API on the user's behalf during analysis.
 * provider_token is only available in the initial session — after a token
 * refresh Supabase drops it, so we must capture it here.
 */
export default function SyncingPage() {
  const router = useRouter();
  const called = useRef(false);

  useEffect(() => {
    if (called.current) return;
    called.current = true;

    (async () => {
      try {
        const supabase = createClient();
        const { data: { session } } = await supabase.auth.getSession();

        if (!session) {
          router.replace("/login?error=no_session");
          return;
        }

        const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/v1";

        await fetch(`${apiBase}/auth/sync`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            // provider_token is the GitHub OAuth token — available only
            // in the initial session before the first Supabase token refresh
            provider_token: session.provider_token ?? null,
          }),
        });
      } catch {
        // Non-fatal — user creation and token storage happen lazily
      } finally {
        router.replace("/dashboard");
      }
    })();
  }, [router]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4">
      <motion.div
        className="w-8 h-8 rounded-full border-2 border-signal border-t-transparent"
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
      />
      <p className="text-sm text-muted-foreground">Setting up your profile…</p>
    </div>
  );
}
