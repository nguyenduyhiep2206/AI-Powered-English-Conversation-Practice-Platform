import { NextRequest, NextResponse } from "next/server";

const APP_ORIGIN = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

export function getBackendUrl(): string | undefined {
  return process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
}

/**
 * Server-side logout: reads token from cookies (including httpOnly),
 * revokes session on backend, clears local token cookie, redirects to login.
 */
export async function performLogout(request: NextRequest): Promise<NextResponse> {
  const token = request.cookies.get("token")?.value;
  const apiUrl = getBackendUrl();

  if (token && apiUrl) {
    try {
      await fetch(`${apiUrl}/api/v1/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      // Continue clearing local session even if backend is unreachable.
    }
  }

  const response = NextResponse.redirect(new URL("/login", APP_ORIGIN));

  // Clear both non-httpOnly and legacy httpOnly token cookies.
  response.cookies.set("token", "", { path: "/", maxAge: 0 });
  response.cookies.set("token", "", { path: "/", maxAge: 0, httpOnly: true });

  return response;
}
