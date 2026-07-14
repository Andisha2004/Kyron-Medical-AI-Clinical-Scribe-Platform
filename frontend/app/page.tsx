import Link from "next/link";

import { StatusBadge } from "@/components/ui/status-badge";
import { publicEnv } from "@/lib/env";

const setupItems = [
  "Next.js application initialized",
  "TypeScript strict checking enabled",
  "App Router enabled",
  "Tailwind CSS configured",
  "ESLint and Prettier configured",
  "Shared API client created",
  "Frontend environment variables configured",
];

export default function HomePage() {
  return (
    <div className="mx-auto w-full max-w-7xl flex-1 px-4 py-12 sm:px-6 lg:px-8">
      <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <StatusBadge label="Frontend healthy" status="success" />
          <span className="text-sm text-slate-500">Development environment</span>
        </div>

        <h1 className="mt-6 max-w-3xl text-4xl font-bold tracking-tight text-slate-950">
          {publicEnv.appName}
        </h1>

        <p className="mt-4 max-w-3xl leading-7 text-slate-600">
          The frontend foundation is running. Provider, encounter, admin, and authentication
          workflows will be implemented in the upcoming tasks.
        </p>

        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          <Link
            href="/provider"
            className="rounded-xl border border-slate-200 p-5 transition hover:border-slate-400 hover:bg-slate-50"
          >
            <h2 className="font-semibold text-slate-950">Provider workspace</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Open the temporary provider dashboard and encounter routes.
            </p>
          </Link>

          <Link
            href="/admin"
            className="rounded-xl border border-slate-200 p-5 transition hover:border-slate-400 hover:bg-slate-50"
          >
            <h2 className="font-semibold text-slate-950">Administration</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Open the temporary administration dashboard.
            </p>
          </Link>
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-xl font-semibold text-slate-950">Frontend setup status</h2>

        <ul className="mt-4 grid gap-3 sm:grid-cols-2">
          {setupItems.map((item) => (
            <li
              key={item}
              className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4"
            >
              <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full bg-emerald-600" />
              <span className="text-sm text-slate-700">{item}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
