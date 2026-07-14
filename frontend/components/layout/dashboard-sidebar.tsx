import Link from "next/link";
import type { ReactNode } from "react";

export interface DashboardNavigationItem {
  href: string;
  label: string;
}

interface DashboardSidebarProps {
  title: string;
  items: DashboardNavigationItem[];
  children: ReactNode;
  footer?: ReactNode;
}

export function DashboardSidebar({ title, items, children, footer }: DashboardSidebarProps) {
  return (
    <div className="mx-auto grid w-full max-w-7xl flex-1 grid-cols-1 md:grid-cols-[240px_1fr]">
      <aside className="flex flex-col border-b border-slate-200 bg-slate-50 p-5 md:border-r md:border-b-0">
        <div>
          <p className="mb-4 text-xs font-bold tracking-wider text-slate-500 uppercase">{title}</p>

          <nav aria-label={`${title} navigation`}>
            <ul className="space-y-1">
              {items.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="block rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-white hover:text-slate-950"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>

        {footer ? <div className="mt-6 md:mt-auto">{footer}</div> : null}
      </aside>

      <section className="min-w-0 p-5 sm:p-8">{children}</section>
    </div>
  );
}
