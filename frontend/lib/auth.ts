import { api } from "@/lib/api";
import type { AuthenticatedUser, LoginRequest, LoginResponse } from "@/types/auth";

export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  return api.post<LoginResponse>("/api/auth/login", credentials);
}

export async function logout(): Promise<void> {
  await api.post<void>("/api/auth/logout");
}

export async function getCurrentUser(): Promise<AuthenticatedUser> {
  return api.get<AuthenticatedUser>("/api/auth/me");
}
