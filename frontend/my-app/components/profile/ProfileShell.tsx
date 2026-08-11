"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import AppHeader from "@/components/AppHeader";
import { cn } from "@/lib/utils";

export default function ProfileShell({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const profileActive = pathname === "/profile";
  const settingsActive = pathname === "/profile/settings";

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[#FFF5EB] text-[#1F1B15]">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 55% 40% at 8% 12%, rgba(232, 93, 4, 0.12), transparent 58%), radial-gradient(ellipse 45% 35% at 92% 18%, rgba(13, 148, 136, 0.1), transparent 55%)",
        }}
      />

      <div className="relative">
        <AppHeader />

        <main className="mx-auto w-full max-w-5xl px-5 py-8 sm:px-8 md:px-10 md:py-10">
          <div className="grid grid-cols-1 gap-8 md:grid-cols-[12rem_minmax(0,1fr)] md:gap-12">
            <aside className="md:pt-1">
              <nav
                className="flex gap-2 md:flex-col md:gap-1"
                aria-label="Profile"
              >
                <Link
                  href="/profile"
                  className={cn(
                    "inline-flex min-h-11 items-center rounded-2xl px-3.5 text-[0.875rem] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]",
                    profileActive
                      ? "bg-white font-semibold text-[#E85D04] shadow-[0_4px_16px_rgba(31,27,21,0.06)] ring-1 ring-[#1F1B15]/06"
                      : "text-[#8A8178] hover:bg-white/60 hover:text-[#1F1B15]",
                  )}
                >
                  Profile
                </Link>
                <Link
                  href="/profile/settings"
                  className={cn(
                    "inline-flex min-h-11 items-center rounded-2xl px-3.5 text-[0.875rem] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]",
                    settingsActive
                      ? "bg-white font-semibold text-[#E85D04] shadow-[0_4px_16px_rgba(31,27,21,0.06)] ring-1 ring-[#1F1B15]/06"
                      : "text-[#8A8178] hover:bg-white/60 hover:text-[#1F1B15]",
                  )}
                >
                  Settings
                </Link>
              </nav>
            </aside>

            <div className="min-w-0 space-y-5">{children}</div>
          </div>
        </main>
      </div>
    </div>
  );
}
