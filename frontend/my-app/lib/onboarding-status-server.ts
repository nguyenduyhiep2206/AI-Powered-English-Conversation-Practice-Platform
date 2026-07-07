import { isJwtExpired } from "@/lib/jwt";
import type { OnboardingStatusResponse } from "@/lib/onboarding-status";

function getApiUrl(): string | undefined {
  return process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
}

/** Middleware / server: check onboarding_complete via backend. */
export async function isOnboardingComplete(token: string): Promise<boolean> {
  if (isJwtExpired(token)) return true;

  const apiUrl = getApiUrl();
  if (!apiUrl) return true;

  try {
    const res = await fetch(`${apiUrl}/api/v1/onboarding/status`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!res.ok) return true;
    const body = (await res.json()) as OnboardingStatusResponse;
    return body.data.onboarding_complete;
  } catch {
    return true;
  }
}
