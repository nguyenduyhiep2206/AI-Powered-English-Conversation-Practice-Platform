import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { isJwtExpired } from "@/lib/jwt";

const APP_ORIGIN = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";
const AUTH_PAGES = ["/login", "/register"];

function getValidToken(request: NextRequest): string | undefined {
  const token = request.cookies.get("token")?.value;
  if (!token || isJwtExpired(token)) return undefined;
  return token;
}

export function middleware(request: NextRequest) {
  const token = getValidToken(request);
  const { pathname } = request.nextUrl;

  if (!token && pathname.startsWith("/dashboard")) {
    return NextResponse.redirect(new URL("/login", APP_ORIGIN));
  }

  if (token && AUTH_PAGES.includes(pathname)) {
    return NextResponse.redirect(new URL("/start-onboarding", APP_ORIGIN));
  }

  if (!token && pathname.startsWith("/start-onboarding")) {
    return NextResponse.redirect(new URL("/login", APP_ORIGIN));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/login", "/register", "/start-onboarding"],
};
