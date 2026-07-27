"use client";

import useSWR from "swr";
import { getAnalysisHistory } from "@/lib/api";
import type { AnalysisJob } from "@/types/signal";

export function useAnalysisHistory() {
  const { data, error, isLoading, mutate } = useSWR<AnalysisJob[]>(
    "analysis/history",
    getAnalysisHistory,
    { revalidateOnFocus: false }
  );

  return {
    history:   data ?? [],
    isLoading,
    isError:   !!error,
    refresh:   mutate,
    lastJob:   data?.[0] ?? null,
  };
}
