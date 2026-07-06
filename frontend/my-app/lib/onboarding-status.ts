export type OnboardingStatus = "not_started" | "in_progress" | "completed" | "skipped";

const KEY = "ef:onboarding-status";

export function getOnboardingStatus(): OnboardingStatus {
  if (typeof window === "undefined") return "not_started";
  return (localStorage.getItem(KEY) as OnboardingStatus | null) ?? "not_started";
}

export function setOnboardingStatus(status: OnboardingStatus) {
  if (typeof window === "undefined") return;
  localStorage.setItem(KEY, status);
}
