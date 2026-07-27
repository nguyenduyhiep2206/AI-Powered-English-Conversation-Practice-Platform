/** Client-navigable path that renders the shared 404 UI. */
export const NOT_FOUND_PATH = "/404";

const ADMIN_PATHS = new Set([
  "/admin",
  "/admin/books",
  "/admin/quiz",
  "/admin/lessons",
]);

const DASHBOARD_PATH_RE = /^\/dashboard(\/practice\/\d+)?$/;
const ONBOARDING_PATH_RE = /^\/onboarding(\/placement)?$/;

export function isAllowedAdminPath(pathname: string): boolean {
  return ADMIN_PATHS.has(pathname);
}

export function isAllowedDashboardPath(pathname: string): boolean {
  return DASHBOARD_PATH_RE.test(pathname);
}

export function isAllowedOnboardingPath(pathname: string): boolean {
  return ONBOARDING_PATH_RE.test(pathname);
}
