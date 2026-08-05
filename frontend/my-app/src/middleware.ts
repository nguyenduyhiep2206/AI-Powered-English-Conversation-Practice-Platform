import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { resolvePostLoginPath } from "@/lib/auth";
import { fetchCurrentUser, isAdminToken } from "@/lib/auth-server";
import { isJwtExpired } from "@/lib/jwt";
import { isOnboardingComplete } from "@/lib/onboarding-status-server";
import {
  isAllowedAdminPath,
  isAllowedAiTutorPath,
  isAllowedDashboardPath,
  isAllowedOnboardingPath,
  isAllowedProfilePath,
  NOT_FOUND_PATH,
} from "@/lib/routes";

const APP_ORIGIN = process.env.NEXT_PUBLIC_APP_URL;
const AUTH_PAGES = ["/login", "/register"];

function getValidToken(request: NextRequest): string | undefined {
  const token = request.cookies.get("token")?.value;
  if (!token || isJwtExpired(token)) return undefined;
  return token;
}

function hasSessionCookie(request: NextRequest): boolean {
  return Boolean(request.cookies.get("token")?.value);
}

async function getPostLoginDestination(token: string): Promise<string> {
  const user = await fetchCurrentUser(token);
  if (!user) return "/start-onboarding";
  return resolvePostLoginPath(user);
}

function notFoundResponse(request: NextRequest): NextResponse {
  return NextResponse.rewrite(new URL(NOT_FOUND_PATH, request.url));
}

export async function middleware(request: NextRequest) {
  const validToken = getValidToken(request);
  const hasSession = hasSessionCookie(request);
  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/admin")) {
    // No cookie → hide admin behind 404. Expired access token with cookie still
    // present is allowed through so AuthSessionRefresh can restore the session
    // (same pattern as /dashboard); otherwise users briefly see 404 then recover.
    if (!hasSession) {
      return notFoundResponse(request);
    }
    if (validToken && !(await isAdminToken(validToken))) {
      return notFoundResponse(request);
    }
    if (!isAllowedAdminPath(pathname)) {
      return notFoundResponse(request);
    }
  }

  if (!hasSession && pathname.startsWith("/dashboard")) {
    return NextResponse.redirect(new URL("/login", APP_ORIGIN));
  }

  if (pathname.startsWith("/dashboard") && !isAllowedDashboardPath(pathname)) {
    return notFoundResponse(request);
  }

  if (
    validToken &&
    pathname.startsWith("/dashboard") &&
    !(await isOnboardingComplete(validToken))
  ) {
    return NextResponse.redirect(new URL("/start-onboarding", APP_ORIGIN));
  }

  if (!hasSession && pathname.startsWith("/ai-tutor")) {
    return NextResponse.redirect(new URL("/login", APP_ORIGIN));
  }

  if (pathname.startsWith("/ai-tutor") && !isAllowedAiTutorPath(pathname)) {
    return notFoundResponse(request);
  }

  if (
    validToken &&
    pathname.startsWith("/ai-tutor") &&
    !(await isOnboardingComplete(validToken))
  ) {
    return NextResponse.redirect(new URL("/start-onboarding", APP_ORIGIN));
  }

  if (!hasSession && pathname.startsWith("/profile")) {
    return NextResponse.redirect(new URL("/login", APP_ORIGIN));
  }

  if (pathname.startsWith("/profile") && !isAllowedProfilePath(pathname)) {
    return notFoundResponse(request);
  }

  if (
    validToken &&
    pathname.startsWith("/profile") &&
    !(await isOnboardingComplete(validToken))
  ) {
    return NextResponse.redirect(new URL("/start-onboarding", APP_ORIGIN));
  }

  if (validToken && AUTH_PAGES.includes(pathname)) {
    const destination = await getPostLoginDestination(validToken);
    return NextResponse.redirect(new URL(destination, APP_ORIGIN));
  }

  if (!hasSession && pathname.startsWith("/start-onboarding")) {
    return NextResponse.redirect(new URL("/login", APP_ORIGIN));
  }

  if (!hasSession && pathname.startsWith("/onboarding")) {
    return NextResponse.redirect(new URL("/login", APP_ORIGIN));
  }

  if (
    pathname.startsWith("/onboarding") &&
    !isAllowedOnboardingPath(pathname)
  ) {
    return notFoundResponse(request);
  }

  if (
    validToken &&
    pathname.startsWith("/onboarding") &&
    (await isOnboardingComplete(validToken))
  ) {
    return NextResponse.redirect(new URL("/dashboard", APP_ORIGIN));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/admin/:path*",
    "/dashboard/:path*",
    "/ai-tutor",
    "/ai-tutor/:path*",
    "/login",
    "/register",
    "/start-onboarding",
    "/onboarding",
    "/onboarding/:path*",
    "/profile",
    "/profile/:path*",
  ],
};
