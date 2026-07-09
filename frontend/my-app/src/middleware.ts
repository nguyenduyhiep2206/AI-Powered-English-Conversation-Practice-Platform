import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { resolvePostLoginPath } from "@/lib/auth";
import { fetchCurrentUser } from "@/lib/auth-server";
import { isJwtExpired } from "@/lib/jwt";
import { isOnboardingComplete } from "@/lib/onboarding-status-server";

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

export async function middleware(request: NextRequest) {
  const validToken = getValidToken(request);
  const hasSession = hasSessionCookie(request);
  const { pathname } = request.nextUrl;

  if (!hasSession && pathname.startsWith("/admin")) {
    return NextResponse.redirect(new URL("/login", APP_ORIGIN));
  }

  if (!hasSession && pathname.startsWith("/dashboard")) {
    return NextResponse.redirect(new URL("/login", APP_ORIGIN));
  }

  if (
    validToken &&
    pathname.startsWith("/dashboard") &&
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
    "/login",
    "/register",
    "/start-onboarding",
    "/onboarding",
  ],
};
