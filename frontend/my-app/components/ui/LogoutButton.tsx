"use client";

import { LogOut } from "lucide-react";
import { logout } from "@/lib/api";
import { cn } from "@/lib/utils";

type LogoutButtonProps = {
  className?: string;
};

export default function LogoutButton({ className }: LogoutButtonProps) {
  async function handleLogout(e: React.MouseEvent<HTMLButtonElement>) {
    e.preventDefault();
    await logout();
  }

  return (
    <button
      type="button"
      onClick={handleLogout}
      className={cn(
        "relative z-10 inline-flex cursor-pointer items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors",
        "hover:bg-destructive/10 hover:text-destructive",
        className
      )}
    >
      <LogOut className="h-3.5 w-3.5" aria-hidden />
      Sign out
    </button>
  );
}
