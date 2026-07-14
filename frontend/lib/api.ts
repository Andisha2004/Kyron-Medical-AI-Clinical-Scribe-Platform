import { publicEnv } from "@/lib/env";
import type { ApiErrorBody } from "@/types/api";

type QueryValue = string | number | boolean | null | undefined;

export interface ApiRequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  query?: Record<string, QueryValue>;
  timeoutMs?: number;
}

export class ApiError extends Error {
  public readonly status: number;
  public readonly body: ApiErrorBody | null;

  constructor(message: string, status: number, body: ApiErrorBody | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function createRequestUrl(path: string, query?: Record<string, QueryValue>): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  if (publicEnv.apiBaseUrl.startsWith("/")) {
    const url = new URL(
      `${publicEnv.apiBaseUrl.replace(/\/$/, "")}${normalizedPath}`,
      window.location.origin,
    );

    if (query) {
      for (const [key, value] of Object.entries(query)) {
        if (value !== undefined && value !== null) {
          url.searchParams.set(key, String(value));
        }
      }
    }

    return `${url.pathname}${url.search}`;
  }

  const url = new URL(normalizedPath, publicEnv.apiBaseUrl);

  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    }
  }

  return url.toString();
}

function hasJsonBody(body: unknown): boolean {
  return body !== undefined && body !== null && !(body instanceof FormData);
}

async function safelyReadResponseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type");

  if (response.status === 204) {
    return null;
  }

  if (contentType?.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();
  return text || null;
}

async function request<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { body, query, headers, timeoutMs = 15000, ...requestInit } = options;

  const timeoutController = new AbortController();
  const timeoutId = setTimeout(() => timeoutController.abort(), timeoutMs);

  const requestHeaders = new Headers(headers);

  if (hasJsonBody(body) && !requestHeaders.has("Content-Type")) {
    requestHeaders.set("Content-Type", "application/json");
  }

  requestHeaders.set("Accept", "application/json");

  try {
    const response = await fetch(createRequestUrl(path, query), {
      ...requestInit,
      headers: requestHeaders,
      body: body instanceof FormData ? body : hasJsonBody(body) ? JSON.stringify(body) : undefined,
      signal: timeoutController.signal,
      credentials: "include",
    });

    const responseBody = await safelyReadResponseBody(response);

    if (!response.ok) {
      const apiErrorBody =
        typeof responseBody === "object" && responseBody !== null
          ? (responseBody as ApiErrorBody)
          : null;

      const message =
        apiErrorBody?.detail ||
        apiErrorBody?.message ||
        `API request failed with status ${response.status}.`;

      throw new ApiError(message, response.status, apiErrorBody);
    }

    return responseBody as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(`API request timed out after ${timeoutMs} milliseconds.`);
    }

    throw new Error(
      error instanceof Error
        ? `Unable to reach the API: ${error.message}`
        : "Unable to reach the API.",
    );
  } finally {
    clearTimeout(timeoutId);
  }
}

export const api = {
  get<T>(path: string, options: Omit<ApiRequestOptions, "method" | "body"> = {}): Promise<T> {
    return request<T>(path, {
      ...options,
      method: "GET",
    });
  },

  post<T>(
    path: string,
    body?: unknown,
    options: Omit<ApiRequestOptions, "method" | "body"> = {},
  ): Promise<T> {
    return request<T>(path, {
      ...options,
      method: "POST",
      body,
    });
  },

  put<T>(
    path: string,
    body?: unknown,
    options: Omit<ApiRequestOptions, "method" | "body"> = {},
  ): Promise<T> {
    return request<T>(path, {
      ...options,
      method: "PUT",
      body,
    });
  },

  patch<T>(
    path: string,
    body?: unknown,
    options: Omit<ApiRequestOptions, "method" | "body"> = {},
  ): Promise<T> {
    return request<T>(path, {
      ...options,
      method: "PATCH",
      body,
    });
  },

  delete<T>(path: string, options: Omit<ApiRequestOptions, "method" | "body"> = {}): Promise<T> {
    return request<T>(path, {
      ...options,
      method: "DELETE",
    });
  },
};
