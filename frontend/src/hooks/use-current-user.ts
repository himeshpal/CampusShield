"use client";

import { useQuery } from "@tanstack/react-query";

import { useHydrated } from "@/hooks/use-hydrated";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";

/**
 * The signed-in user. `user` stays undefined until after hydration: the server never
 * knows who is signed in, so rendering the cached user earlier causes a mismatch.
 */
export function useCurrentUser(): { user: User | undefined; isError: boolean } {
  const hydrated = useHydrated();
  const { data, isError } = useQuery({
    queryKey: ["me"],
    queryFn: () => api<User>("/auth/me"),
    staleTime: 5 * 60_000,
  });
  return { user: hydrated ? data : undefined, isError };
}
