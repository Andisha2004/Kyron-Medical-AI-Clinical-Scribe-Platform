import { api } from "@/lib/api";
import type {
  AdminDashboardResponse,
  AdminEncounterListResponse,
  AdminProviderSummary,
  CreateProviderRequest,
  ProviderStatusUpdateRequest,
} from "@/types/admin";
import type { TemplateMutationRequest, TemplateSummary } from "@/types/template";

export async function getAdminDashboard(): Promise<AdminDashboardResponse> {
  return api.get<AdminDashboardResponse>("/api/admin/dashboard");
}

export async function getAdminProviders(): Promise<AdminProviderSummary[]> {
  return api.get<AdminProviderSummary[]>("/api/admin/providers");
}

export async function createProvider(
  payload: CreateProviderRequest,
): Promise<AdminProviderSummary> {
  return api.post<AdminProviderSummary>("/api/admin/providers", payload);
}

export async function updateProviderStatus(
  providerId: string,
  payload: ProviderStatusUpdateRequest,
): Promise<AdminProviderSummary> {
  return api.patch<AdminProviderSummary>(`/api/admin/providers/${providerId}/status`, payload);
}

export async function getAdminEncounters(query: {
  provider_id?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
}): Promise<AdminEncounterListResponse> {
  return api.get<AdminEncounterListResponse>("/api/encounters/admin/encounters", { query });
}

export async function getAdminTemplates(): Promise<TemplateSummary[]> {
  return api.get<TemplateSummary[]>("/api/admin/templates");
}

export async function createAdminTemplate(
  payload: TemplateMutationRequest,
): Promise<TemplateSummary> {
  return api.post<TemplateSummary>("/api/admin/templates", payload);
}

export async function updateAdminTemplate(
  templateId: string,
  payload: TemplateMutationRequest,
): Promise<TemplateSummary> {
  return api.put<TemplateSummary>(`/api/admin/templates/${templateId}`, payload);
}

export async function deleteAdminTemplate(templateId: string): Promise<TemplateSummary> {
  return api.delete<TemplateSummary>(`/api/admin/templates/${templateId}`);
}
