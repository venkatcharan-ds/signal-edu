import useSWR from "swr";
import { getAnalysisQuota } from "@/lib/api";
import type { AnalysisQuota } from "@/types/signal";

export function useAnalysisQuota() {
  const { data, error, isLoading, mutate } = useSWR<AnalysisQuota>(
    "analysis/quota",
    getAnalysisQuota,
    { revalidateOnFocus: false, refreshInterval: 30_000 },
  );

  return {
    quota: data ?? null,
    isLoading,
    isError: !!error,
    refresh: mutate,
    canStart: data ? data.remaining > 0 && !data.has_active_job : true,
  };
}
