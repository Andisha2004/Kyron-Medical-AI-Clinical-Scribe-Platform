export interface ApiErrorBody {
  detail?: string;
  message?: string;
  errors?: Record<string, unknown>;
  path?: string;
  timestamp?: string;
}

export interface ApiHealthResponse {
  status: string;
  service?: string;
  version?: string;
  timestamp?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
}
