import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";

interface EncounterWorkspacePageProps {
  params: Promise<{
    encounterId: string;
  }>;
}

export default async function EncounterWorkspacePage({ params }: EncounterWorkspacePageProps) {
  const { encounterId } = await params;

  return (
    <div>
      <PageHeader
        title="Encounter workspace"
        description={`Encounter ID: ${encounterId}`}
        actions={<StatusBadge label="Draft" status="neutral" />}
      />

      <div className="mt-8 grid gap-6 xl:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-6">
          <h2 className="font-semibold text-slate-950">Transcript and voice session</h2>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Live transcript controls will be implemented during the voice-agent integration task.
          </p>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-6">
          <h2 className="font-semibold text-slate-950">Clinical note</h2>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            SOAP note generation and editing will be implemented during the note-generation task.
          </p>
        </section>
      </div>
    </div>
  );
}
