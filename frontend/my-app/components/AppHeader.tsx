"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { logout } from "@/lib/api";
import { cn } from "@/lib/utils";

type AppHeaderProps = {
  extraActions?: ReactNode;
};

export default function AppHeader({ extraActions }: AppHeaderProps) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const myPlanActive = pathname === "/dashboard" || pathname.startsWith("/dashboard/");

  useEffect(() => {
    if (!menuOpen) return;

    function handlePointerDown(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setMenuOpen(false);
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [menuOpen]);

  async function handleSignOut() {
    setMenuOpen(false);
    await logout();
  }

  return (
    <header className="border-b border-border bg-white">
      <div className="mx-auto flex items-center justify-between gap-4 px-24 py-3">
        <Link
          href="/dashboard"
          className="inline-flex shrink-0 items-center rounded-md bg-black px-3 py-1.5"
        >
          <span className="text-sm font-semibold tracking-tight text-white lowercase">
            englishflow
          </span>
        </Link>

        <nav className="flex flex-1 items-center justify-center gap-6" aria-label="Main">
          <Link
            href="/dashboard"
            className={cn(
              "inline-flex items-center gap-1.5 text-sm transition-colors",
              myPlanActive
                ? "font-medium text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              className="h-4 w-4 shrink-0 fill-current"
              aria-hidden
            >
              <path
                fillRule="evenodd"
                clipRule="evenodd"
                d="M15.667 4.5a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0m-1.855 1a3.502 3.502 0 0 0 6.855-1 3.5 3.5 0 0 0-6.855-1h-5.41a4.39 4.39 0 0 0-4.035 2.66 4.42 4.42 0 0 0 .114 3.705 4.47 4.47 0 0 0 3.253 2.41l4.268.711 4.269.712c.768.128 1.44.627 1.793 1.332a2.39 2.39 0 0 1-2.132 3.47h-5.41a3.502 3.502 0 0 0-6.855 1 3.5 3.5 0 0 0 6.855 1h5.41a4.39 4.39 0 0 0 4.034-2.66 4.42 4.42 0 0 0-.114-3.705 4.47 4.47 0 0 0-3.252-2.41l-4.269-.711-4.268-.712A2.47 2.47 0 0 1 6.27 8.97a2.42 2.42 0 0 1-.065-2.021A2.39 2.39 0 0 1 8.402 5.5zm-8.145 14a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0"
              />
            </svg>
            My plan
          </Link>
          <Link
            href="/ai-tutor"
            className={cn(
              "text-sm transition-colors",
              pathname.startsWith("/ai-tutor")
                ? "font-medium text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            AI Tutor
          </Link>
        </nav>

        <div className="flex shrink-0 items-center gap-2">
          {extraActions}
          <div className="relative" ref={menuRef}>
            <button
              type="button"
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              aria-label="Open account menu"
              onClick={() => setMenuOpen((open) => !open)}
              className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-full bg-[#7dcf7a] text-sm font-semibold text-white transition-opacity hover:opacity-90"
            >
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#4a90d9] text-[11px] leading-none">
                U
              </span>
            </button>

            {menuOpen ? (
              <div
                role="menu"
                className="absolute right-0 z-50 mt-2 min-w-[10rem] rounded-md border border-[#EAEAEA] bg-white py-1 shadow-[0_2px_8px_rgba(0,0,0,0.04)]"
              >
                <button
                  type="button"
                  role="menuitem"
                  onClick={handleSignOut}
                  className="block w-full cursor-pointer px-4 py-2 text-left text-sm text-red-600 transition-colors hover:bg-red-50"
                >
                  Sign out
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </header>
  );
}
