"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { logout } from "@/lib/api";
import { avatarInitial, isPresetAvatar } from "@/lib/avatar-presets";
import { fetchCurrentUserClient } from "@/lib/auth";
import { cn } from "@/lib/utils";

type AppHeaderProps = {
  extraActions?: ReactNode;
};

export default function AppHeader({ extraActions }: AppHeaderProps) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [initial, setInitial] = useState("U");
  const menuRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  useEffect(() => {
    let cancelled = false;

    void fetchCurrentUserClient()
      .then((me) => {
        if (cancelled) return;
        setAvatarUrl(me.avatar_url ?? null);
        setInitial(avatarInitial(me.full_name, me.username));
      })
      .catch(() => {
        if (cancelled) return;
        setAvatarUrl(null);
        setInitial("U");
      });

    return () => {
      cancelled = true;
    };
  }, [pathname]);

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

  const navClass = (active: boolean) =>
    cn(
      "inline-flex min-h-11 items-center gap-1.5 rounded-xl px-2 text-[0.875rem] transition-colors",
      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04] focus-visible:ring-offset-2 focus-visible:ring-offset-white",
      active
        ? "font-semibold text-[#E85D04]"
        : "text-[#8A8178] hover:text-[#1F1B15]",
    );

  const showAvatar = isPresetAvatar(avatarUrl);

  return (
    <header className="sticky top-0 z-50 border-b border-[#E9D7C9]/80 bg-[#FFFAF5]/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-5 py-2.5 sm:gap-4 sm:px-6">
        <Link
          href="/dashboard"
          aria-label="EnglishFlow home"
          className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-[#E85D04] shadow-[0_6px_16px_rgba(232,93,4,0.28)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04] focus-visible:ring-offset-2"
        >
          <span className="text-[0.875rem] font-bold tracking-tight text-white">
            E
          </span>
        </Link>

        <nav
          className="flex flex-1 items-center justify-center gap-1 sm:gap-3"
          aria-label="Main"
        >
          <Link
            href="/dashboard"
            className={navClass(
              pathname === "/dashboard" || pathname.startsWith("/dashboard/"),
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
            className={navClass(pathname.startsWith("/ai-tutor"))}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              className="h-4 w-4 shrink-0 fill-current"
              aria-hidden
            >
              <path d="M7 12a1 1 0 0 1 .895.553l.783 1.567c.282.564.369.728.473.864q.159.206.365.364h-.001c.136.104.3.191.863.472l1.57.785a1 1 0 0 1 0 1.79l-1.57.785c-.563.281-.728.367-.863.471a2 2 0 0 0-.363.365v-.001c-.105.136-.191.3-.473.863l-.784 1.57a1 1 0 0 1-1.79 0l-.783-1.568-.304-.594a2 2 0 0 0-.17-.271 2 2 0 0 0-.364-.363c-.135-.105-.3-.192-.862-.472l-1.57-.785a1 1 0 0 1 0-1.79l1.57-.785c.563-.281.727-.368.862-.472q.206-.158.364-.364c.104-.136.191-.3.473-.862l.784-1.57.072-.12A1 1 0 0 1 7 12m0 3.23c-.197.392-.356.7-.567.975h-.001q-.316.41-.727.727c-.276.213-.585.372-.976.568.277.139.512.258.723.392l.253.175v.001q.41.316.727.727c.212.275.37.584.567.974.197-.392.357-.699.568-.974h.001q.316-.41.727-.727c.276-.213.584-.373.976-.569-.393-.197-.7-.354-.976-.566v-.001a4 4 0 0 1-.727-.727c-.212-.275-.372-.584-.568-.974M15.5 1a1 1 0 0 1 .934.64l1.178 3.065c.3.779.395 1.006.524 1.189l.102.131q.163.192.368.34h.001c.182.128.405.222 1.188.523l3.064 1.178a1 1 0 0 1 0 1.868l-3.064 1.178c-.78.3-1.007.395-1.19.525q-.273.196-.47.47c-.096.137-.173.296-.332.698l-.19.49-1.18 3.064a1 1 0 0 1-1.867 0l-1.178-3.064c-.3-.78-.395-1.007-.525-1.19a2 2 0 0 0-.47-.47c-.137-.096-.296-.173-.698-.332l-.49-.19-3.064-1.18a1 1 0 0 1 0-1.867l3.064-1.178.49-.19c.401-.16.563-.238.7-.335q.273-.196.47-.47c.128-.182.222-.405.523-1.188l1.178-3.064.067-.138A1 1 0 0 1 15.5 1m-.246 4.422c-.263.685-.45 1.193-.76 1.63a4 4 0 0 1-.941.942l-.002.001c-.435.308-.941.496-1.628.76v-.001l-.64.246.639.245c.684.263 1.194.45 1.63.76q.411.294.737.679l.205.263.001.002c.308.435.496.941.76 1.628h-.001l.246.639.245-.639c.263-.685.45-1.193.76-1.63a4 4 0 0 1 .942-.941l.002-.001c.435-.308.941-.496 1.628-.76L19.716 9l-.639-.246c-.685-.262-1.193-.45-1.63-.76a4 4 0 0 1-.941-.941l-.001-.002c-.308-.435-.496-.941-.76-1.628v-.001l-.245-.639z" />
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
              aria-controls={menuId}
              aria-label="Open account menu"
              onClick={() => setMenuOpen((open) => !open)}
              className="flex h-11 w-11 cursor-pointer items-center justify-center overflow-hidden rounded-2xl bg-[#0D9488] text-[0.875rem] font-semibold text-white transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04] focus-visible:ring-offset-2"
            >
              {showAvatar ? (
                // eslint-disable-next-line @next/next/no-img-element -- preset PNGs from /public
                <img
                  src={avatarUrl!}
                  alt=""
                  className="h-full w-full object-cover"
                />
              ) : (
                <span className="flex h-7 w-7 items-center justify-center rounded-xl bg-[#E85D04] text-[0.75rem] leading-none">
                  {initial}
                </span>
              )}
            </button>

            {menuOpen ? (
              <div
                id={menuId}
                role="menu"
                className="absolute right-0 z-[100] mt-2 min-w-[11rem] rounded-2xl bg-white py-1 shadow-[0_12px_32px_rgba(31,27,21,0.1)] ring-1 ring-[#E9D7C9]"
              >
                <Link
                  href="/profile"
                  role="menuitem"
                  onClick={() => setMenuOpen(false)}
                  className="flex min-h-11 w-full cursor-pointer rounded-xl items-center px-4 text-left text-[0.875rem] text-[#1F1B15] transition-colors hover:bg-[#FFF5EB] focus-visible:bg-[#FFF5EB] focus-visible:outline-none"
                >
                  Profile
                </Link>
                <Link
                  href="/profile/settings"
                  role="menuitem"
                  onClick={() => setMenuOpen(false)}
                  className="flex min-h-11 w-full cursor-pointer rounded-xl items-center px-4 text-left text-[0.875rem] text-[#1F1B15] transition-colors hover:bg-[#FFF5EB] focus-visible:bg-[#FFF5EB] focus-visible:outline-none"
                >
                  Settings
                </Link>
                <button
                  type="button"
                  role="menuitem"
                  onClick={handleSignOut}
                  className="flex min-h-11 w-full cursor-pointer rounded-xl items-center px-4 text-left text-[0.875rem] text-[#BE123C] transition-colors hover:bg-[#FFE4E6] focus-visible:bg-[#FFE4E6] focus-visible:outline-none"
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
