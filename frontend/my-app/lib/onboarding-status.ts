import { authFetch } from "@/lib/api";

export type OnboardingStep = "survey" | "placement" | "completed";

export type OnboardingStatusPayload = {
  survey_done: boolean;
  placement_done: boolean;
  onboarding_complete: boolean;
  current_step: OnboardingStep;
  occupation?: string | null;
  goal?: string | null;
  weak_point?: string | null;
  daily_time_min?: number | null;
  current_level?: string | null;
  placement_score?: number | null;
};

export type OnboardingStatusResponse = {
  success: boolean;
  data: OnboardingStatusPayload;
};

/** Client: fetch onboarding status from backend (requires auth cookie). */
export async function fetchOnboardingStatus(): Promise<OnboardingStatusPayload> {
  const res = await authFetch("/api/v1/onboarding/status");
  if (!res.ok) {
    throw new Error("Failed to load onboarding status");
  }
  const body = (await res.json()) as OnboardingStatusResponse;
  return body.data;
}
