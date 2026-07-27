/**
 * Fallback page at /callback (note: no "auth/" prefix — route group).
 * The real OAuth callback is handled by app/auth/callback/route.ts at /auth/callback.
 * This page is shown only if someone navigates to /callback directly.
 */
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function CallbackFallbackPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 px-6 text-center">
      <p className="text-muted-foreground text-sm">
        If you arrived here from a sign-in link, please start the process again.
      </p>
      <Button asChild size="sm" variant="outline" className="rounded-lg border-white/10">
        <Link href="/login">Back to sign in</Link>
      </Button>
    </div>
  );
}
