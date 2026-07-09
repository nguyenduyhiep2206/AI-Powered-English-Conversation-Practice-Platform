"use client";

import { createContext, useContext } from "react";
import type { MeData } from "@/lib/auth";

const AdminUserContext = createContext<MeData | null>(null);

export function AdminUserProvider({
  user,
  children,
}: {
  user: MeData;
  children: React.ReactNode;
}) {
  return (
    <AdminUserContext.Provider value={user}>
      {children}
    </AdminUserContext.Provider>
  );
}

/** Read the authenticated admin user provided by AdminLayout. */
export function useAdminUser(): MeData {
  const user = useContext(AdminUserContext);
  if (!user) {
    throw new Error("useAdminUser must be used within AdminLayout");
  }
  return user;
}
