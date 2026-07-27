"use client";

import useSWR from "swr";
import { getMyGaps } from "@/lib/api";
import type { GapAnalysis } from "@/types/signal";

export function useGapAnalyses() {
  const { data, error, isLoading, mutate } = useSWR<GapAnalysis[]>(
    "profiles/me/gaps",
    getMyGaps,
    { revalidateOnFocus: false }
  );

  return {
    gaps:      data ?? [],
    isLoading,
    isError:   !!error,
    refresh:   mutate,
    readyCount: data?.filter((g) => g.overall_ready).length ?? 0,
  };
}
