import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { NextResponse, type NextRequest } from "next/server";

/**
 * OAuth callback handler — matches the redirectTo URL in LoginButton.tsx.
 *
 * Flow:
 *   GitHub → Supabase → GET /auth/callback?code=<pkce_code>
 *   1. Exchange the one-time code for a Supabase session
 *   2. Session is written into secure httpOnly cookies
 *   3. Redirect to /auth/syncing so the client can call POST /v1/auth/sync
 *      and create the User row in our database
 *
 * On error, redirects to /login?error=<reason> so the UI can surface it.
 */
export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const code  = searchParams.get("code");
  const next  = searchParams.get("next") ?? "/auth/syncing";
  const error = searchParams.get("error");
  const errorDescription = searchParams.get("error_description");

  // GitHub OAuth errors arrive as query params (e.g. user denied access)
  if (error) {
    const params = new URLSearchParams({ error, reason: errorDescription ?? "" });
    return NextResponse.redirect(`${origin}/login?${params}`);
  }

  if (!code) {
    return NextResponse.redirect(`${origin}/login?error=missing_code`);
  }

  const cookieStore = await cookies();

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => cookieStore.getAll(),
        setAll: (cookiesToSet) => {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          );
        },
      },
    }
  );

  const { data: exchangeData, error: exchangeError } = await supabase.auth.exchangeCodeForSession(code);

  if (exchangeError) {
    console.error("[auth/callback] exchange error:", exchangeError.message);
    return NextResponse.redirect(
      `${origin}/login?error=exchange_failed&reason=${encodeURIComponent(exchangeError.message)}`
    );
  }

  // provider_token is only present on the raw exchange response — @supabase/ssr
  // deliberately does not write it to cookies, so it is lost after this point.
  // We must call /auth/sync here, server-side, while we still have it.
  const session = exchangeData?.session;
  if (session?.provider_token) {
    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/v1";
    try {
      await fetch(`${apiBase}/auth/sync`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ provider_token: session.provider_token }),
      });
    } catch (err) {
      // Non-fatal: user row will be created lazily by get_current_user,
      // but github_access_token will be missing until the user re-authenticates.
      console.error("[auth/callback] backend sync failed:", err);
    }
  } else {
    console.warn("[auth/callback] no provider_token in exchange response — GitHub token will not be stored");
  }

  // Session established — go to the syncing page (now a no-op for token storage,
  // kept as a loading screen before the dashboard redirect).
  return NextResponse.redirect(`${origin}${next}`);
}
