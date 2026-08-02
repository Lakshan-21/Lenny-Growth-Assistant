import type { ApiErrorBody } from "@/types/domain";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/**
 * Phase 1 auth assumption: no `Authorization` header is attached. Real
 * Supabase Auth isn't implemented on the backend yet — the backend must
 * run with `DEV_AUTH_BYPASS=true` (see backend/app/domains/auth/
 * dependencies.py) for any request from this client to succeed. This is
 * the single place that would change once login exists (attach a bearer
 * token here) — see README "Known Phase 1 limitations".
 */
export class ApiError extends Error {
  status: number;
  errorCode: string;

  constructor(status: number, errorCode: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errorCode = errorCode;
  }
}

async function throwForErrorResponse(response: Response): Promise<never> {
  let body: ApiErrorBody | undefined;
  try {
    body = (await response.json()) as ApiErrorBody;
  } catch {
    // Non-JSON error body (e.g. a proxy/network-level failure) — fall
    // through to the generic message below.
  }
  throw new ApiError(response.status, body?.error_code ?? "unknown_error", body?.message ?? response.statusText);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    await throwForErrorResponse(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

/**
 * For endpoints that return a raw body (e.g. the artifact Markdown
 * download, which is `PlainTextResponse` on the backend) rather than
 * JSON — `request()` always calls `.json()`, which would fail here.
 */
async function requestText(path: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    await throwForErrorResponse(response);
  }

  return response.text();
}

export const apiClient = {
  get: <T>(path: string): Promise<T> => request<T>(path, { method: "GET" }),
  getText: (path: string): Promise<string> => requestText(path),
  post: <T>(path: string, body?: unknown): Promise<T> =>
    request<T>(path, {
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
};
