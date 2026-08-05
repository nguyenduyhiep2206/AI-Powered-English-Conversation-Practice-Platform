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
            E
          </span>
        </Link>

        <nav className="flex flex-1 items-center justify-center gap-6" aria-label="Main">
          <Link
            href="/dashboard"
            className={cn(
              "inline-flex items-center gap-1.5 text-sm transition-colors",
              pathname === "/dashboard" || pathname.startsWith("/dashboard/")
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
              "inline-flex items-center gap-1.5 text-sm transition-colors",
              pathname.startsWith("/ai-tutor")
                ? "font-medium text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" className="h-4 w-4 shrink-0 fill-current">
            <path d="M7 12a1 1 0 0 1 .895.553l.783 1.567c.282.564.369.728.473.864q.159.206.365.364h-.001c.136.104.3.191.863.472l1.57.785a1 1 0 0 1 0 1.79l-1.57.785c-.563.281-.728.367-.863.471a2 2 0 0 0-.363.365v-.001c-.105.136-.191.3-.473.863l-.784 1.57a1 1 0 0 1-1.79 0l-.783-1.568-.304-.594a2 2 0 0 0-.17-.271 2 2 0 0 0-.364-.363c-.135-.105-.3-.192-.862-.472l-1.57-.785a1 1 0 0 1 0-1.79l1.57-.785c.563-.281.727-.368.862-.472q.206-.158.364-.364c.104-.136.191-.3.473-.862l.784-1.57.072-.12A1 1 0 0 1 7 12m0 3.23c-.197.392-.356.7-.567.975h-.001q-.316.41-.727.727c-.276.213-.585.372-.976.568.277.139.512.258.723.392l.253.175v.001q.41.316.727.727c.212.275.37.584.567.974.197-.392.357-.699.568-.974h.001q.316-.41.727-.727c.276-.213.584-.373.976-.569-.393-.197-.7-.354-.976-.566v-.001a4 4 0 0 1-.727-.727c-.212-.275-.372-.584-.568-.974M15.5 1a1 1 0 0 1 .934.64l1.178 3.065c.3.779.395 1.006.524 1.189l.102.131q.163.192.368.34h.001c.182.128.405.222 1.188.523l3.064 1.178a1 1 0 0 1 0 1.868l-3.064 1.178c-.78.3-1.007.395-1.19.525q-.273.196-.47.47c-.096.137-.173.296-.332.698l-.19.49-1.18 3.064a1 1 0 0 1-1.867 0l-1.178-3.064c-.3-.78-.395-1.007-.525-1.19a2 2 0 0 0-.47-.47c-.137-.096-.296-.173-.698-.332l-.49-.19-3.064-1.18a1 1 0 0 1 0-1.867l3.064-1.178.49-.19c.401-.16.563-.238.7-.335q.273-.196.47-.47c.128-.182.222-.405.523-1.188l1.178-3.064.067-.138A1 1 0 0 1 15.5 1m-.246 4.422c-.263.685-.45 1.193-.76 1.63a4 4 0 0 1-.941.942l-.002.001c-.435.308-.941.496-1.628.76v-.001l-.64.246.639.245c.684.263 1.194.45 1.63.76q.411.294.737.679l.205.263.001.002c.308.435.496.941.76 1.628h-.001l.246.639.245-.639c.263-.685.45-1.193.76-1.63a4 4 0 0 1 .942-.941l.002-.001c.435-.308.941-.496 1.628-.76L19.716 9l-.639-.246c-.685-.262-1.193-.45-1.63-.76a4 4 0 0 1-.941-.941l-.001-.002c-.308-.435-.496-.941-.76-1.628v-.001l-.245-.639z">
            </path>
            </svg>
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
                className="absolute right-0 z-50 mt-2 min-w-[10rem] rounded-[8px] border border-[#EAEAEA] bg-white py-1 shadow-[0_2px_8px_rgba(0,0,0,0.04)]"
              >
                <Link
                  href="/profile"
                  role="menuitem"
                  onClick={() => setMenuOpen(false)}
                  className="block w-full px-4 py-2 text-left text-sm text-[#111111] transition-colors hover:bg-[#F9F9F8]"
                >
                  Profile
                </Link>
                <Link
                  href="/profile/settings"
                  role="menuitem"
                  onClick={() => setMenuOpen(false)}
                  className="block w-full px-4 py-2 text-left text-sm text-[#111111] transition-colors hover:bg-[#F9F9F8]"
                >
                  Settings
                </Link>
                <button
                  type="button"
                  role="menuitem"
                  onClick={handleSignOut}
                  className="block w-full cursor-pointer px-4 py-2 text-left text-sm text-[#9F2F2D] transition-colors hover:bg-[#FDEBEC]"
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
