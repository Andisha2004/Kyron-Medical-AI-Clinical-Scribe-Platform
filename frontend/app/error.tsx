"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";

interface GlobalErrorProps {
  error: Error & {
    digest?: string;
  };
  reset: () => void;
}

export default function GlobalError({ error, reset }: GlobalErrorProps) {
  useEffect(() => {
    console.error("Unhandled frontend error:", error);
  }, [error]);

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 items-center px-4 py-12">
      <section className="w-full rounded-2xl border border-red-200 bg-white p-8">
        <h1 className="text-2xl font-bold text-slate-950">Something went wrong</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          The page could not be displayed. Try the request again.
        </p>
        <Button className="mt-6" onClick={reset}>
          Try again
        </Button>
      </section>
    </div>
  );
}
