import { EncounterWorkspace } from "@/components/encounter/encounter-workspace";

interface EncounterWorkspacePageProps {
  params: Promise<{
    encounterId: string;
  }>;
}

export default async function EncounterWorkspacePage({ params }: EncounterWorkspacePageProps) {
  const { encounterId } = await params;

  return <EncounterWorkspace encounterId={encounterId} />;
}
