"use client";

import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import { getCurrentUser } from "@/lib/auth";
import type { AuthenticatedUser } from "@/types/auth";

interface UseAuthSessionResult {
  user: AuthenticatedUser | null;
  isLoading: boolean;
  error: ApiError | Error | null;
}

export function useAuthSession(): UseAuthSessionResult {
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<ApiError | Error | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadCurrentUser() {
      try {
        const currentUser = await getCurrentUser();
        if (!isMounted) {
          return;
        }
        setUser(currentUser);
        setError(null);
      } catch (loadError) {
        if (!isMounted) {
          return;
        }

        if (
          loadError instanceof ApiError &&
          (loadError.status === 401 || loadError.status === 403)
        ) {
          setUser(null);
          setError(loadError);
        } else {
          setError(loadError instanceof Error ? loadError : new Error("Failed to load user."));
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadCurrentUser();

    return () => {
      isMounted = false;
    };
  }, []);

  return { user, isLoading, error };
}
