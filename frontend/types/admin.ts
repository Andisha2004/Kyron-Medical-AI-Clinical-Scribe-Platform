export interface AdminDashboardEncounter {
  id: string;
  patient_name: string;
  provider_name: string;
  status: string;
  encounter_date: string;
  template_name: string;
}

export interface AdminDashboardResponse {
  active_provider_count: number;
  total_encounter_count: number;
  active_template_count: number;
  recent_encounters: AdminDashboardEncounter[];
}

export interface AdminProviderSummary {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  specialty: string | null;
  is_active: boolean;
  created_at: string;
}

export interface CreateProviderRequest {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  specialty?: string;
}

export interface ProviderStatusUpdateRequest {
  is_active: boolean;
}

export interface AdminEncounterListItem {
  id: string;
  provider_id: string;
  provider_name: string;
  patient_name: string;
  encounter_date: string;
  status: string;
  template_name: string;
  updated_at: string;
}

export interface AdminEncounterListResponse {
  items: AdminEncounterListItem[];
  page: number;
  page_size: number;
  total: number;
}
