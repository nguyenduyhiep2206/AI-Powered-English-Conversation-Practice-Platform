"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import AppHeader from "@/components/AppHeader";
import { cn } from "@/lib/utils";

export default function ProfileShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const profileActive = pathname === "/profile";
  const settingsActive = pathname === "/profile/settings";

  return (
    <div className="min-h-screen bg-[#F7F6F3] text-[#111111]">
      <AppHeader />

      <main className="mx-auto w-full max-w-6xl px-6 py-10 md:px-10">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-[160px_minmax(0,1fr)_200px] md:gap-10">
          <aside className="md:pt-1">
            <nav className="flex flex-col space-y-1" aria-label="Profile">
              <Link
                href="/profile"
                className={cn(
                  "border-l-2 py-2 pl-3 text-sm transition-colors",
                  profileActive
                    ? "border-[#111111] font-medium text-[#111111]"
                    : "border-transparent text-[#787774] hover:text-[#111111]",
                )}
              >
                Profile
              </Link>
              <Link
                href="/profile/settings"
                className={cn(
                  "border-l-2 py-2 pl-3 text-sm transition-colors",
                  settingsActive
                    ? "border-[#111111] font-medium text-[#111111]"
                    : "border-transparent text-[#787774] hover:text-[#111111]",
                )}
              >
                Settings
              </Link>
            </nav>
          </aside>

          <div className="min-w-0 space-y-6">{children}</div>

          <aside aria-hidden className="hidden md:block" />
        </div>
      </main>
    </div>
  );
}
