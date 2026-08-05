"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { getTokenFromCookie, refreshAccessToken, clearTokenCookie } from "@/lib/api";
import { isJwtExpired } from "@/lib/jwt";
import { NOT_FOUND_PATH } from "@/lib/routes";

const PROTECTED_PREFIXES = ["/admin", "/dashboard", "/start-onboarding", "/profile"];

export function AuthSessionRefresh() {
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    const isProtected = PROTECTED_PREFIXES.some((prefix) =>
      pathname.startsWith(prefix)
    );
    if (!isProtected) return;

    const token = getTokenFromCookie();
    if (token && !isJwtExpired(token)) return;

    refreshAccessToken()
      .then(() => router.refresh())
      .catch(() => {
        clearTokenCookie();
        const destination = pathname.startsWith("/admin")
          ? NOT_FOUND_PATH
          : "/login";
        window.location.href = destination;
      });
  }, [pathname, router]);

  return null;
}
