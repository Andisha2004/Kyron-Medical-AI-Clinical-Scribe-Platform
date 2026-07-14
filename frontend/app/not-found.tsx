import Link from "next/link";

export default function NotFoundPage() {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 items-center px-4 py-12">
      <section className="w-full rounded-2xl border border-slate-200 bg-white p-8 text-center">
        <p className="text-sm font-semibold text-slate-500">404</p>
        <h1 className="mt-2 text-3xl font-bold text-slate-950">Page not found</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          The requested frontend route does not exist.
        </p>
        <Link
          href="/"
          className="mt-6 inline-flex min-h-10 items-center justify-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700"
        >
          Return home
        </Link>
      </section>
    </div>
  );
}
