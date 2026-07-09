import { isJwtExpired } from "@/lib/jwt";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

const REFRESH_TOKEN_MAX_AGE_SECONDS =
  (Number(process.env.NEXT_PUBLIC_REFRESH_TOKEN_EXPIRE_DAYS) || 7) * 24 * 3600;

export const SESSION_ALREADY_ACTIVE_MESSAGE =
  "Another account is already signed in on this browser. Please sign out first.";

export function extractErrorMessage(error: unknown, fallback: string): string {
  if (!error || typeof error !== "object") return fallback;
  const detail = (error as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return (
      detail
        .map((item) => (typeof item === "string" ? item : item?.msg))
        .filter(Boolean)
        .join(", ") || fallback
    );
  }
  return fallback;
}

export function getTokenFromCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|; )token=([^;]*)/);
  if (!match?.[1]) return null;
  try {
    return decodeURIComponent(match[1]);
  } catch {
    return match[1];
  }
}

function assertBrowserSessionAvailable(): void {
  const token = getTokenFromCookie();
  if (token && !isJwtExpired(token)) {
    throw new Error(SESSION_ALREADY_ACTIVE_MESSAGE);
  }
}

// This is a promise that is used to store the refresh token in flight.
let refreshInFlight: Promise<{ access_token: string; token_type: string }> | null = null;

async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  if (!API_URL) {
    throw new Error(
      "NEXT_PUBLIC_API_URL is not set. Add it to .env.local (e.g. http://localhost:8001)."
    );
  }

  const headers = new Headers(options.headers);
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  if (!headers.has("Content-Type") && !isFormData) {
    headers.set("Content-Type", "application/json");
  }

  return fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers,
  });
}

/** Authenticated fetch: attaches Bearer token, retries once after refresh on 401. */
export async function authFetch(
  path: string,
  options: RequestInit = {},
  retried = false
): Promise<Response> {
  const token = getTokenFromCookie();
  const headers = new Headers(options.headers);

  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await apiFetch(path, { ...options, headers });

  if (res.status === 401 && !retried) {
    try {
      const refreshed = await refreshAccessToken();
      const retryHeaders = new Headers(options.headers);
      if (!retryHeaders.has("Content-Type")) {
        retryHeaders.set("Content-Type", "application/json");
      }
      retryHeaders.set("Authorization", `Bearer ${refreshed.access_token}`);
      return apiFetch(path, { ...options, headers: retryHeaders });
    } catch {
      clearTokenCookie();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new Error("Session expired");
    }
  }

  return res;
}

/** Authenticated multipart upload (do not set Content-Type — browser sets boundary). */
export async function authFetchMultipart(
  path: string,
  formData: FormData,
  retried = false
): Promise<Response> {
  const token = getTokenFromCookie();
  const headers = new Headers();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await apiFetch(path, { method: "POST", body: formData, headers });

  if (res.status === 401 && !retried) {
    try {
      const refreshed = await refreshAccessToken();
      const retryHeaders = new Headers();
      retryHeaders.set("Authorization", `Bearer ${refreshed.access_token}`);
      return apiFetch(path, { method: "POST", body: formData, headers: retryHeaders });
    } catch {
      clearTokenCookie();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new Error("Session expired");
    }
  }

  return res;
}

/** Keep cookie until refresh token expires so middleware can detect a restorable session. */
export function setTokenCookie(accessToken: string): void {
  if (typeof document === "undefined" || !accessToken) return;
  document.cookie = `token=${encodeURIComponent(accessToken)}; path=/; max-age=${REFRESH_TOKEN_MAX_AGE_SECONDS}; samesite=lax`;
}

export function clearTokenCookie(): void {
  if (typeof document === "undefined") return;
  const expired = "Thu, 01 Jan 1970 00:00:00 GMT";
  document.cookie = `token=; path=/; expires=${expired}; samesite=lax`;
  document.cookie = `token=; path=/; max-age=0; samesite=lax`;
}

export async function login(email: string, password: string) {
  assertBrowserSessionAvailable();

  const res = await apiFetch("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ identifier: email, password }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Email or password is incorrect"));
  }

  const data = await res.json();
  setTokenCookie(data.access_token);
  return data;
}

export async function googleLogin(credential: string) {
  assertBrowserSessionAvailable();

  const res = await apiFetch("/api/v1/auth/google", {
    method: "POST",
    body: JSON.stringify({ credential }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Sign in with Google failed"));
  }

  const data = await res.json();
  setTokenCookie(data.access_token);
  return data;
}

export async function register(payload: {
  full_name: string;
  username: string;
  email: string;
  password: string;
}) {
  const res = await apiFetch("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Registration failed"));
  }

  const data = await res.json();
  await login(payload.email, payload.password);
  return data;
}

export async function refreshAccessToken() {
  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    const res = await apiFetch("/api/v1/auth/token/refresh", { method: "POST" });

    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(extractErrorMessage(error, "Session expired"));
    }

    const data = (await res.json()) as { access_token: string; token_type: string };
    if (!data.access_token) {
      throw new Error("Session expired");
    }
    setTokenCookie(data.access_token);
    return data;
  })();

  try {
    return await refreshInFlight;
  } finally {
    refreshInFlight = null;
  }
}

export async function getMe() {
  const res = await authFetch("/api/v1/auth/me");

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to load profile"));
  }

  return res.json();
}

/** Revoke current session on backend (refresh cookie sent via credentials), then clear local cookie. */
export async function logout(): Promise<void> {
  try {
    await authFetch("/api/v1/auth/logout", { method: "POST" });
  } catch {
    // Still clear local session if backend is unreachable or token already expired.
  } finally {
    clearTokenCookie();
    window.location.href = "/login";
  }
}
