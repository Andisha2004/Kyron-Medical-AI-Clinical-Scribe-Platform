import { api } from "@/lib/api";
import type { IcdSearchResult } from "@/types/icd";

export async function searchIcdCodes(
  query: string,
  options: { signal?: AbortSignal; limit?: number } = {},
): Promise<IcdSearchResult[]> {
  return api.get<IcdSearchResult[]>("/api/icd/search", {
    query: {
      q: query,
      limit: options.limit ?? 8,
    },
    signal: options.signal,
  });
}
