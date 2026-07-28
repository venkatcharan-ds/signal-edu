import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

/**
 * Runs on every request before the page renders.
 * Refreshes the Supabase session so server components always
 * get a valid, unexpired access token via supabase.auth.getUser().
 *
 * Without this, tokens expire mid-session and the dashboard layout
 * silently redirects logged-in users to /login.
 *
 * Next.js 16 renamed "middleware" to "proxy" — the file must be proxy.ts
 * and the export must be named `proxy` (or a default export).
 */
export async function proxy(request: NextRequest) {
  let response = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (cookiesToSet) => {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          );
          response = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  // getUser() validates the JWT and refreshes it when expired.
  // Do NOT use getSession() here — it does not validate server-side.
  await supabase.auth.getUser();

  return response;
}

export const config = {
  matcher: [
    /*
     * Run on all paths except:
     * - _next/static (static files)
     * - _next/image  (image optimisation)
     * - favicon.ico
     * - public folder assets
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
