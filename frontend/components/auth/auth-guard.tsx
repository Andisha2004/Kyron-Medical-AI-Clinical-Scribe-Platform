"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import { ApiError } from "@/lib/api";
import { useAuthSession } from "@/hooks/use-auth-session";
import type { UserRole } from "@/types/auth";

interface AuthGuardProps {
  allowedRoles: UserRole[];
  children: ReactNode;
}

function roleHome(role: UserRole): string {
  return role === "admin" ? "/admin" : "/provider";
}

export function AuthGuard({ allowedRoles, children }: AuthGuardProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isLoading, error } = useAuthSession();

  useEffect(() => {
    if (isLoading) {
      return;
    }

    if (!user) {
      const reason = error instanceof ApiError && error.status === 403 ? "deactivated" : "expired";
      router.replace(`/login?next=${encodeURIComponent(pathname)}&reason=${reason}`);
      return;
    }

    if (!allowedRoles.includes(user.role)) {
      router.replace(roleHome(user.role));
    }
  }, [allowedRoles, error, isLoading, pathname, router, user]);

  if (isLoading || !user || !allowedRoles.includes(user.role)) {
    return (
      <div className="mx-auto flex w-full max-w-7xl flex-1 items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
        <div className="rounded-xl border border-slate-200 bg-white px-6 py-4 text-sm text-slate-600 shadow-sm">
          Verifying your session...
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
