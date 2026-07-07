"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { clearTokenCookie, refreshAccessToken } from "@/lib/api";
import { isJwtExpired } from "@/lib/jwt";

const PROTECTED_PREFIXES = ["/dashboard", "/start-onboarding"];

function getTokenFromCookie(): string | null {
  const match = document.cookie.match(/(?:^|; )token=([^;]*)/);
  return match ? match[1] : null;
}

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
        window.location.href = "/login";
      });
  }, [pathname, router]);

  return null;
}
