"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { getCurrentUser, login } from "@/lib/auth";

function roleHome(role: "provider" | "admin"): string {
  return role === "admin" ? "/admin" : "/provider";
}

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = searchParams.get("next");
  const reason = searchParams.get("reason");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCheckingExistingSession, setIsCheckingExistingSession] = useState(true);

  const infoMessage = useMemo(() => {
    if (reason === "deactivated") {
      return "Your account is currently inactive. Sign in again after an administrator restores access.";
    }

    if (reason === "expired") {
      return "Your session expired. Sign in again to continue.";
    }

    return null;
  }, [reason]);

  useEffect(() => {
    let isMounted = true;

    async function checkExistingSession() {
      try {
        const user = await getCurrentUser();
        if (!isMounted) {
          return;
        }
        router.replace(nextPath || roleHome(user.role));
      } catch {
        if (isMounted) {
          setIsCheckingExistingSession(false);
        }
      }
    }

    void checkExistingSession();

    return () => {
      isMounted = false;
    };
  }, [nextPath, router]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const response = await login({ email, password });
      router.replace(nextPath || roleHome(response.user.role));
      router.refresh();
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMessage(error.message);
      } else if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("Unable to sign in.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isCheckingExistingSession) {
    return (
      <section className="w-full rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-bold tracking-tight text-slate-950">Sign in</h1>
        <p className="mt-4 text-sm leading-6 text-slate-600">Checking your current session...</p>
      </section>
    );
  }

  return (
    <section className="w-full rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
      <h1 className="text-2xl font-bold tracking-tight text-slate-950">Sign in</h1>
      <p className="mt-2 text-sm leading-6 text-slate-600">
        Use one of the seeded demo accounts to access the provider or admin workspace.
      </p>

      {infoMessage ? (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {infoMessage}
        </div>
      ) : null}

      {errorMessage ? (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorMessage}
        </div>
      ) : null}

      <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
        <div>
          <label htmlFor="email" className="block text-sm font-semibold text-slate-800">
            Email address
          </label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="provider1@kyron-demo.com"
            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
            required
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-semibold text-slate-800">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Enter your password"
            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
            required
          />
        </div>

        <Button type="submit" fullWidth disabled={isSubmitting}>
          {isSubmitting ? "Signing in..." : "Sign in"}
        </Button>
      </form>
    </section>
  );
}
