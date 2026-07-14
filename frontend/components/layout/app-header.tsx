import Link from "next/link";

import { publicEnv } from "@/lib/env";

export function AppHeader() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href="/" className="font-semibold tracking-tight text-slate-950">
          {publicEnv.appName}
        </Link>

        <nav
          aria-label="Primary navigation"
          className="flex items-center gap-4 text-sm font-medium text-slate-700"
        >
          <Link className="hover:text-slate-950" href="/provider">
            Provider
          </Link>
          <Link className="hover:text-slate-950" href="/admin">
            Admin
          </Link>
          <Link className="hover:text-slate-950" href="/login">
            Login
          </Link>
        </nav>
      </div>
    </header>
  );
}
