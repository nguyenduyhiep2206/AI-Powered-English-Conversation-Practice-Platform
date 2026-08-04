/** Client-navigable path that renders the shared 404 UI. */
export const NOT_FOUND_PATH = "/404";

const ADMIN_PATHS = new Set([
  "/admin",
  "/admin/books",
  "/admin/quiz",
  "/admin/skills",
]);

const DASHBOARD_PATH_RE = /^\/dashboard(\/practice\/\d+)?$/;
const AI_TUTOR_PATH_RE = /^\/ai-tutor(\/\d+)?$/;
const ONBOARDING_PATH_RE = /^\/onboarding(\/placement)?$/;
const PROFILE_PATH_RE = /^\/profile(\/settings)?$/;
const ADMIN_SKILL_PATH_RE = /^\/admin\/skills(\/\d+)?$/;

export function isAllowedAdminPath(pathname: string): boolean {
  if (ADMIN_PATHS.has(pathname)) return true;
  return ADMIN_SKILL_PATH_RE.test(pathname);
}

export function isAllowedDashboardPath(pathname: string): boolean {
  return DASHBOARD_PATH_RE.test(pathname);
}

export function isAllowedAiTutorPath(pathname: string): boolean {
  return AI_TUTOR_PATH_RE.test(pathname);
}

export function isAllowedOnboardingPath(pathname: string): boolean {
  return ONBOARDING_PATH_RE.test(pathname);
}

export function isAllowedProfilePath(pathname: string): boolean {
  return PROFILE_PATH_RE.test(pathname);
}
