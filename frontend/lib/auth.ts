import { createClient } from "@/lib/supabase";

/**
 * Returns the current Supabase access token for use in API requests.
 * Returns null when the user is not signed in.
 *
 * Uses getSession() (cached) rather than getUser() (network) because this
 * is called on every API request and we want it to be fast. The middleware
 * already validated and refreshed the token server-side before page render,
 * so the client-side session is trustworthy.
 */
export async function getAccessToken(): Promise<string | null> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

/**
 * Signs the user out of Supabase and returns the destination URL.
 * Callers are responsible for the router redirect.
 */
export async function signOut(): Promise<void> {
  const supabase = createClient();
  await supabase.auth.signOut();
}
