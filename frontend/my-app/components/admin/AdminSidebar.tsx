"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  ClipboardList,
  LayoutDashboard,
  Sparkles,
  Users,
} from "lucide-react";
import LogoutButton from "@/components/ui/LogoutButton";
import { cn } from "@/lib/utils";
import type { MeData } from "@/lib/auth";

const NAV_ITEMS = [
  { href: "/admin", label: "Overview", icon: LayoutDashboard, enabled: true, exact: true },
  { href: "/admin/books", label: "Books", icon: BookOpen, enabled: true, exact: false },
  { href: "/admin/survey", label: "Survey", icon: ClipboardList, enabled: false, exact: false },
  { href: "/admin/users", label: "Users", icon: Users, enabled: false, exact: false },
] as const;

type AdminSidebarProps = {
  user: MeData;
};

export function AdminSidebar({ user }: AdminSidebarProps) {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r border-border bg-sidebar">
      <div className="flex items-center gap-2 border-b border-border px-5 py-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-white">
          <Sparkles className="h-4 w-4 text-black" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-foreground">EnglishFlow</p>
          <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
            Admin
          </p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {NAV_ITEMS.map((item) => {
          const active = item.exact
            ? pathname === item.href
            : pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;

          if (!item.enabled) {
            return (
              <div
                key={item.href}
                className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground/60"
                aria-disabled
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{item.label}</span>
                <span className="ml-auto text-[10px] uppercase tracking-wide">Soon</span>
              </div>
            );
          }

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border p-4">
        <p className="truncate text-sm font-medium text-foreground">
          {user.full_name || user.username}
        </p>
        <p className="truncate text-xs text-muted-foreground">{user.email}</p>
        <div className="mt-3">
          <LogoutButton className="w-full justify-start px-0" />
        </div>
      </div>
    </aside>
  );
}
