"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { useAdminUser } from "@/components/admin/AdminUserContext";

export default function AdminPage() {
  const user = useAdminUser();
  const displayName = user.full_name || user.username;

  return (
    <>
      <header className="border-b border-border px-6 py-5">
        <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
          Admin dashboard
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">
          Welcome back, {displayName}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage content, users, and system settings from here.
        </p>
      </header>

      <main className="flex-1 p-6">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Link
            href="/admin/books"
            className="ef-card-hover ef-card block rounded-xl border border-border bg-card/60 p-5 transition-colors hover:border-primary/40"
          >
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-sm font-semibold">Books</h2>
              <Badge>Active</Badge>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              Upload and manage PDF books for AI indexing.
            </p>
          </Link>

          <section className="ef-card rounded-xl border border-border bg-card/60 p-5">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-sm font-semibold">Survey questions</h2>
              <Badge variant="outline">Phase 2</Badge>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              Create and edit onboarding survey questions.
            </p>
          </section>

          <section className="ef-card rounded-xl border border-border bg-card/60 p-5">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-sm font-semibold">Users & roles</h2>
              <Badge variant="outline">Phase 3</Badge>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              View learners and assign admin or learner roles.
            </p>
          </section>

          <section className="ef-card rounded-xl border border-border bg-card/60 p-5">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-sm font-semibold">Your access</h2>
              <Badge variant="secondary">{user.roles.join(", ")}</Badge>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              {user.permissions.length} permissions active on this account.
            </p>
          </section>
        </div>
      </main>
    </>
  );
}
