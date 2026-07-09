import { isAdmin, type MeData, type MeResponse } from "@/lib/auth";

function getApiUrl(): string | undefined {
  return process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
}

/** Middleware / server components: load user from backend via Bearer token. */
export async function fetchCurrentUser(token: string): Promise<MeData | null> {
  const apiUrl = getApiUrl();
  if (!apiUrl) return null;

  try {
    const res = await fetch(`${apiUrl}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    const body = (await res.json()) as MeResponse;
    return body.data;
  } catch {
    return null;
  }
}

export async function isAdminToken(token: string): Promise<boolean> {
  const user = await fetchCurrentUser(token);
  return user ? isAdmin(user) : false;
}
