import type { Metadata } from "next";

import { AdminEncounterReview } from "@/components/admin/admin-encounter-review";

export const metadata: Metadata = {
  title: "Admin Encounter Review",
};

interface AdminEncounterPageProps {
  params: Promise<{ encounterId: string }>;
}

export default async function AdminEncounterPage({ params }: AdminEncounterPageProps) {
  const { encounterId } = await params;
  return <AdminEncounterReview encounterId={encounterId} />;
}
