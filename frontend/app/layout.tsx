import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppFooter } from "@/components/layout/app-footer";
import { AppHeader } from "@/components/layout/app-header";
import { publicEnv } from "@/lib/env";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: publicEnv.appName,
    template: `%s | ${publicEnv.appName}`,
  },
  description: "AI-assisted clinical encounter documentation for healthcare providers.",
};

interface RootLayoutProps {
  children: ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col antialiased">
        <AppHeader />
        <main className="flex flex-1 flex-col">{children}</main>
        <AppFooter />
      </body>
    </html>
  );
}
