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
        description="Create a clinical encounter before starting recording, transcription, and note generation."
      />
      <NewEncounterForm />
    </div>
  );
}
