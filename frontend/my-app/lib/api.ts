const API_URL = process.env.NEXT_PUBLIC_API_URL;

const ACCESS_TOKEN_MAX_AGE_SECONDS =
  (Number(process.env.NEXT_PUBLIC_ACCESS_TOKEN_EXPIRE_MINUTES) || 30) * 60;

function extractErrorMessage(error: unknown, fallback: string): string {
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

function getTokenFromCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|; )token=([^;]*)/);
  return match ? match[1] : null;
}

async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  if (!API_URL) {
    throw new Error(
      "NEXT_PUBLIC_API_URL is not set. Add it to .env.local (e.g. http://localhost:8001)."
    );
  }

  return fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
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
      await refreshAccessToken();
    } catch {
      clearTokenCookie();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new Error("Session expired");
    }

    return authFetch(path, options, true);
  }

  return res;
}

/** Set access token cookie on the frontend domain (for middleware route guards). */
export function setTokenCookie(accessToken: string): void {
  if (typeof document === "undefined") return;
  document.cookie = `token=${accessToken}; path=/; max-age=${ACCESS_TOKEN_MAX_AGE_SECONDS}; samesite=lax`;
}

export function clearTokenCookie(): void {
  if (typeof document === "undefined") return;
  const expired = "Thu, 01 Jan 1970 00:00:00 GMT";
  document.cookie = `token=; path=/; expires=${expired}; samesite=lax`;
  document.cookie = `token=; path=/; max-age=0; samesite=lax`;
}

export async function login(email: string, password: string) {
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
  const res = await apiFetch("/api/v1/auth/token/refresh", { method: "POST" });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Session expired"));
  }

  const data = await res.json();
  setTokenCookie(data.access_token);
  return data;
}

export async function getMe() {
  const res = await authFetch("/api/v1/auth/me");

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to load profile"));
  }

  return res.json();
}

/** Delegates to GET /logout (server clears httpOnly cookie + calls backend). */
export function logout(): void {
  window.location.href = "/logout";
}
