import Link from "next/link";
import { createClient } from "@/lib/supabase-server";
import { redirect } from "next/navigation";
import LoginButton from "./LoginButton";

export const metadata = { title: "Sign in — SIGNAL" };

interface Props {
  searchParams: Promise<{ error?: string; reason?: string }>;
}

export default async function LoginPage({ searchParams }: Props) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (user) redirect("/dashboard");

  const { error, reason } = await searchParams;

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6 relative">
      <div className="absolute inset-0 gradient-mesh pointer-events-none" />

      <div className="relative z-10 w-full max-w-sm space-y-8">
        {/* Logo */}
        <div className="text-center space-y-2">
          <Link href="/" className="inline-block">
            <span className="text-2xl font-semibold tracking-tight">SIGNAL</span>
          </Link>
          <p className="text-muted-foreground text-sm">
            We surface the talent that credentials hide.
          </p>
        </div>

        {/* Error banner from OAuth callback */}
        {error && (
          <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {errorMessage(error, reason)}
          </div>
        )}

        {/* Card */}
        <div className="glass rounded-2xl p-8 space-y-6">
          <div className="space-y-1">
            <h1 className="text-xl font-semibold">Get your capability profile</h1>
            <p className="text-sm text-muted-foreground">
              Connect GitHub to analyze your repositories and generate an evidence-based profile.
            </p>
          </div>

          <LoginButton />

          <div className="space-y-3 text-xs text-muted-foreground/70 leading-relaxed">
            <div className="flex gap-2">
              <span className="text-signal mt-0.5">✓</span>
              <span>We only read your public repositories</span>
            </div>
            <div className="flex gap-2">
              <span className="text-signal mt-0.5">✓</span>
              <span>No write access is ever requested</span>
            </div>
            <div className="flex gap-2">
              <span className="text-signal mt-0.5">✓</span>
              <span>Free for students, always</span>
            </div>
          </div>
        </div>

        <p className="text-center text-xs text-muted-foreground/50">
          By continuing you agree to our{" "}
          <Link href="/terms" className="underline underline-offset-2 hover:text-foreground transition-colors">
            Terms
          </Link>{" "}
          and{" "}
          <Link href="/privacy" className="underline underline-offset-2 hover:text-foreground transition-colors">
            Privacy Policy
          </Link>
          .
        </p>
      </div>
    </div>
  );
}

function errorMessage(error: string, reason?: string): string {
  switch (error) {
    case "access_denied":
      return "GitHub access was denied. Please try again and approve the requested permissions.";
    case "exchange_failed":
      return `Authentication failed${reason ? `: ${reason}` : ""}. Please try again.`;
    case "missing_code":
      return "Invalid callback URL. Please start the login process again.";
    case "no_session":
      return "Session could not be established. Please try again.";
    default:
      return reason ?? "Something went wrong. Please try again.";
  }
}
