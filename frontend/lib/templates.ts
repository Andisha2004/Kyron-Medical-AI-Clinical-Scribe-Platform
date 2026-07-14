import { api } from "@/lib/api";
import type { TemplateSummary } from "@/types/template";

export async function getActiveTemplates(): Promise<TemplateSummary[]> {
  return api.get<TemplateSummary[]>("/api/templates");
}
