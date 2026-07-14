import type { Metadata } from "next";

import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Login",
};

export default function LoginPage() {
  return (
    <div className="mx-auto flex w-full max-w-md flex-1 items-center px-4 py-12">
      <section className="w-full rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-bold tracking-tight text-slate-950">Sign in</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Authentication will be connected to the FastAPI backend in the authentication task.
        </p>

        <form className="mt-8 space-y-5">
          <div>
            <label htmlFor="email" className="block text-sm font-semibold text-slate-800">
              Email address
            </label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              disabled
              placeholder="provider@example.com"
              className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 disabled:bg-slate-100 disabled:text-slate-500"
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
              disabled
              placeholder="Enter your password"
              className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 disabled:bg-slate-100 disabled:text-slate-500"
            />
          </div>

          <Button type="submit" fullWidth disabled>
            Authentication coming soon
          </Button>
        </form>
      </section>
    </div>
  );
}
