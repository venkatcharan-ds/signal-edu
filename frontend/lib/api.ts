import { getAccessToken } from "@/lib/auth";
import type {
  CapabilityProfile,
  AnalysisJob,
  AnalysisQuota,
  PublicProfile,
  GapAnalysis,
  ProjectRepo,
} from "@/types/signal";

export class RateLimitError extends Error {
  retryAfter: number | null;
  remaining: number;
  constructor(message: string, retryAfter: number | null = null, remaining = 0) {
    super(message);
    this.name = "RateLimitError";
    this.retryAfter = retryAfter;
    this.remaining = remaining;
  }
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/v1";

/**
 * Authenticated fetch wrapper.
 * Attaches Authorization: Bearer <supabase_access_token> to every request.
 * Throws an Error with the backend's `detail` message on non-2xx responses.
 */
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await getAccessToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (options.body instanceof FormData) {
    delete headers["Content-Type"];
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    if (res.status === 429) {
      const retryAfter = res.headers.get("Retry-After");
      const remaining = parseInt(res.headers.get("X-RateLimit-Remaining") ?? "0", 10);
      throw new RateLimitError(
        body.detail ?? "Rate limit exceeded",
        retryAfter ? parseInt(retryAfter, 10) : null,
        remaining,
      );
    }
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }

  if (res.status === 204) return undefined as T;

  return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const syncUser = () =>
  request<{ id: string; github_username: string; full_name: string | null }>(
    "/auth/sync",
    { method: "POST" }
  );

// ── Analysis ──────────────────────────────────────────────────────────────────

export const startAnalysis = () =>
  request<AnalysisJob>("/analysis/start", { method: "POST" });

export const getAnalysisHistory = () =>
  request<AnalysisJob[]>("/analysis/history");

export const getAnalysisQuota = () =>
  request<AnalysisQuota>("/analysis/quota");

// ── Profiles ──────────────────────────────────────────────────────────────────

export const getMyProfile = () =>
  request<CapabilityProfile>("/profiles/me");

export const getMyGaps = () =>
  request<GapAnalysis[]>("/profiles/me/gaps");

export const getMyProjects = () =>
  request<ProjectRepo[]>("/profiles/me/projects");

export const getPublicProfile = (username: string) =>
  request<PublicProfile>(`/profiles/${username}`);

export const updateProfile = (data: {
  institution?: string;
  full_name?: string;
}) =>
  request<{ id: string; full_name: string | null; institution: string | null }>(
    "/profiles/me",
    { method: "PATCH", body: JSON.stringify(data) }
  );

export const submitResumeSkills = (skills: string[]) =>
  request<{ stored: number }>("/profiles/me/resume-skills", {
    method: "POST",
    body: JSON.stringify({ skills }),
  });

// ── Artifacts ─────────────────────────────────────────────────────────────────

export const uploadArtifact = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return request<{ id: string }>("/artifacts/upload", {
    method: "POST",
    body: form,
  });
};

export const addLink = (url: string, title?: string) =>
  request<{ id: string }>("/artifacts/link", {
    method: "POST",
    body: JSON.stringify({ url, title }),
  });
