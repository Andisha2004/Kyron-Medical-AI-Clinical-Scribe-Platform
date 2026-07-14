import type { Metadata } from "next";

import { NewEncounterForm } from "@/components/encounter/new-encounter-form";
import { PageHeader } from "@/components/ui/page-header";

export const metadata: Metadata = {
  title: "New Encounter",
};

export default function NewEncounterPage() {
  return (
    <div>
      <PageHeader
        title="New encounter"
        description="Start the visit here, then move into transcript capture, SOAP drafting, coding, and final review."
      />
      <NewEncounterForm />
    </div>
  );
}
