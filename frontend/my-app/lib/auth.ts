import { getMe } from "@/lib/api";

export type MeData = {
  id: number;
  username: string;
  email: string;
  full_name?: string | null;
  avatar_url?: string | null;
  is_active: boolean;
  auth_provider: string;
  roles: string[];
  permissions: string[];
};

export type MeResponse = {
  success: boolean;
  data: MeData;
};

export function isAdmin(user: MeData): boolean {
  return user.roles.includes("admin");
}

export function hasPermission(user: MeData, permission: string): boolean {
  return user.permissions.includes(permission);
}

/** Where to send the user right after a successful login. */
export function resolvePostLoginPath(user: MeData): string {
  if (isAdmin(user)) return "/admin";
  return "/start-onboarding";
}

/** Client: load the current user profile (requires auth cookie). */
export async function fetchCurrentUserClient(): Promise<MeData> {
  const body = (await getMe()) as MeResponse;
  return body.data;
}
