"use client";

/**
 * SSE hook that uses fetch() instead of EventSource.
 *
 * EventSource does not support custom headers, so it cannot send
 * Authorization: Bearer tokens. fetch() + ReadableStream is the
 * correct approach when the server requires JWT auth on SSE endpoints.
 */

import { useEffect, useRef, useState } from "react";
import { getAccessToken } from "@/lib/auth";
import type { AnalysisProgressEvent } from "@/types/signal";

interface UseAnalysisStatusReturn {
  events:      AnalysisProgressEvent[];
  progress:    number;
  isComplete:  boolean;
  isFailed:    boolean;
  latestLabel: string | null;
}

export function useAnalysisStatus(jobId: string | null): UseAnalysisStatusReturn {
  const [events,     setEvents]     = useState<AnalysisProgressEvent[]>([]);
  const [progress,   setProgress]   = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [isFailed,   setIsFailed]   = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const controller = new AbortController();
    abortRef.current = controller;

    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/v1";

    (async () => {
      try {
        const token = await getAccessToken();

        const res = await fetch(`${apiBase}/analysis/status/${jobId}`, {
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            Accept: "text/event-stream",
            "Cache-Control": "no-cache",
          },
          signal: controller.signal,
        });

        if (!res.ok || !res.body) {
          setIsFailed(true);
          return;
        }

        const reader  = res.body.getReader();
        const decoder = new TextDecoder();
        let   buffer  = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // SSE frames are separated by double newlines
          const frames = buffer.split("\n\n");
          buffer = frames.pop() ?? "";

          for (const frame of frames) {
            const line = frame.trim();
            if (!line.startsWith("data: ")) continue;

            const payload = line.slice(6).trim();
            if (payload === "[DONE]") {
              setIsComplete(true);
              return;
            }

            try {
              const event: AnalysisProgressEvent = JSON.parse(payload);
              setEvents((prev) => [...prev, event]);
              setProgress(event.progress);

              if (event.step === "complete") { setIsComplete(true); return; }
              if (event.step === "failed")   { setIsFailed(true);   return; }
            } catch {
              // Malformed JSON frame — skip
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setIsFailed(true);
        }
      }
    })();

    return () => controller.abort();
  }, [jobId]);

  const latestLabel =
    events.length > 0 ? events[events.length - 1].label : null;

  return { events, progress, isComplete, isFailed, latestLabel };
}
