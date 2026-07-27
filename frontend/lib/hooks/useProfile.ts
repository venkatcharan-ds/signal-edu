"use client";

import useSWR from "swr";
import { getMyProfile } from "@/lib/api";
import type { CapabilityProfile } from "@/types/signal";

export function useProfile() {
  const { data, error, isLoading, mutate } = useSWR<CapabilityProfile>(
    "profile/me",
    getMyProfile,
    { revalidateOnFocus: false }
  );

  return {
    profile: data,
    isLoading,
    isError: !!error,
    refresh: mutate,
  };
}
