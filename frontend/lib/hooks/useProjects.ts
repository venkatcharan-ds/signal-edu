"use client";

import useSWR from "swr";
import { getMyProjects } from "@/lib/api";
import type { ProjectRepo } from "@/types/signal";

export function useProjects() {
  const { data, error, isLoading, mutate } = useSWR<ProjectRepo[]>(
    "profiles/me/projects",
    getMyProjects,
    { revalidateOnFocus: false }
  );

  return {
    projects:  data ?? [],
    isLoading,
    isError:   !!error,
    refresh:   mutate,
  };
}
