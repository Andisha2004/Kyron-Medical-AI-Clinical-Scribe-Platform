import type { Metadata } from "next";

import { Button } from "@/components/ui/button";
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

      <section className="mt-8 max-w-2xl rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <form className="space-y-5">
          <div>
            <label
              htmlFor="patientDisplayName"
              className="block text-sm font-semibold text-slate-800"
            >
              Test patient display name
            </label>
            <input
              id="patientDisplayName"
              name="patientDisplayName"
              type="text"
              disabled
              placeholder="Jordan Test"
              className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 disabled:bg-slate-100"
            />
            <p className="mt-2 text-xs leading-5 text-slate-500">
              Use fictional patient information during development.
            </p>
          </div>

          <div>
            <label htmlFor="chiefComplaint" className="block text-sm font-semibold text-slate-800">
              Chief complaint
            </label>
            <textarea
              id="chiefComplaint"
              name="chiefComplaint"
              rows={4}
              disabled
              placeholder="Describe the fictional reason for the encounter."
              className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 disabled:bg-slate-100"
            />
          </div>

          <Button type="submit" disabled>
            Backend connection required
          </Button>
        </form>
      </section>
    </div>
  );
}
