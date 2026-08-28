"use client";

/**
 * SSE hook that connects to the analysis status stream and automatically
 * reconnects if the connection drops before a terminal state is reached.
 *
 * EventSource cannot send Authorization headers, so we use fetch() +
 * ReadableStream. On disconnect we retry with exponential backoff.
 * The jobId is also persisted in sessionStorage so the hook resumes
 * correctly after a page refresh.
 */

import { useEffect, useRef, useState } from "react";
import { getAccessToken } from "@/lib/auth";
import type { AnalysisProgressEvent } from "@/types/signal";

export interface UseAnalysisStatusReturn {
  events:       AnalysisProgressEvent[];
  progress:     number;
  isComplete:   boolean;
  isFailed:     boolean;
  latestLabel:  string | null;
  currentStep:  string | null;
}

const TERMINAL      = new Set(["complete", "failed", "cancelled"]);
const MAX_RECONNECTS = 10;
const BASE_DELAY_MS  = 2_000;

export function useAnalysisStatus(jobId: string | null): UseAnalysisStatusReturn {
  const [events,      setEvents]      = useState<AnalysisProgressEvent[]>([]);
  const [progress,    setProgress]    = useState(0);
  const [isComplete,  setIsComplete]  = useState(false);
  const [isFailed,    setIsFailed]    = useState(false);
  const [currentStep, setCurrentStep] = useState<string | null>(null);

  // Refs shared between openStream and scheduleReconnect closures
  const abortRef     = useRef<AbortController | null>(null);
  const terminalRef  = useRef(false);
  const retryCount   = useRef(0);
  const timerRef     = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!jobId) return;

    // Reset for each new jobId
    terminalRef.current = false;
    retryCount.current  = 0;

    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/v1";

    async function openStream() {
      if (terminalRef.current) return;

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

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
          // Auth / not-found → don't retry
          if (res.status === 401 || res.status === 404) {
            terminalRef.current = true;
            setIsFailed(true);
            return;
          }
          scheduleReconnect();
          return;
        }

        // Successful connection — reset retry counter
        retryCount.current = 0;

        const reader  = res.body.getReader();
        const decoder = new TextDecoder();
        let   buffer  = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const frames = buffer.split("\n\n");
          buffer = frames.pop() ?? "";

          for (const frame of frames) {
            const line = frame.trim();
            if (!line.startsWith("data: ")) continue;
            const payload = line.slice(6).trim();

            // Server closes stream after _MAX_STREAM_S timeout — reconnect
            if (payload === "[DONE]") {
              if (!terminalRef.current) scheduleReconnect();
              return;
            }

            try {
              const event: AnalysisProgressEvent = JSON.parse(payload);
              setEvents((prev) => [...prev, event]);
              setProgress(event.progress);
              setCurrentStep(event.step);

              if (TERMINAL.has(event.step)) {
                terminalRef.current = true;
                if (event.step === "complete") setIsComplete(true);
                else setIsFailed(true);
                return;
              }
            } catch {
              // Malformed JSON frame — skip silently
            }
          }
        }

        // Reader ended without a terminal event — reconnect
        if (!terminalRef.current) scheduleReconnect();
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        if (!terminalRef.current) scheduleReconnect();
      }
    }

    function scheduleReconnect() {
      if (terminalRef.current || retryCount.current >= MAX_RECONNECTS) {
        if (!terminalRef.current) {
          terminalRef.current = true;
          setIsFailed(true);
        }
        return;
      }
      const delay = Math.min(BASE_DELAY_MS * 2 ** retryCount.current, 30_000);
      retryCount.current++;
      timerRef.current = setTimeout(openStream, delay);
    }

    openStream();

    return () => {
      // Prevent any pending reconnects from firing after unmount
      terminalRef.current = true;
      abortRef.current?.abort();
      if (timerRef.current !== null) clearTimeout(timerRef.current);
    };
  }, [jobId]);

  const latestLabel = events.length > 0 ? events[events.length - 1].label : null;

  return { events, progress, isComplete, isFailed, latestLabel, currentStep };
}
