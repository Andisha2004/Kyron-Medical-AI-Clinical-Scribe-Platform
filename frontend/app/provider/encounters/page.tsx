import type { Metadata } from "next";

import { ProviderEncountersPage } from "@/components/encounter/provider-encounters-page";

export const metadata: Metadata = {
  title: "Encounters",
};

export default function EncountersPage() {
  return <ProviderEncountersPage />;
}
