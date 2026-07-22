"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { AdminUserProvider } from "@/components/admin/AdminUserContext";
import { fetchCurrentUserClient, isAdmin, type MeData } from "@/lib/auth";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [user, setUser] = useState<MeData | null>(null);
  const [status, setStatus] = useState<"loading" | "ready">("loading");

  useEffect(() => {
    let active = true;

    // fetchCurrentUserClient uses authFetch, which refreshes the access token
    // on a 401 (and redirects to /login itself if the refresh token is gone).
    fetchCurrentUserClient()
      .then((me) => {
        if (!active) return;
        if (!isAdmin(me)) {
          router.replace("/start-onboarding");
          return;
        }
        setUser(me);
        setStatus("ready");
      })
      .catch(() => {
        if (!active) return;
        router.replace("/login");
      });

    return () => {
      active = false;
    };
  }, [router]);

  if (status !== "ready" || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background text-foreground">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <AdminUserProvider user={user}>
      <div className="flex min-h-screen bg-background text-foreground">
        <AdminSidebar user={user} />
        <div className="flex min-w-0 flex-1 flex-col">{children}</div>
      </div>
    </AdminUserProvider>
  );
}
