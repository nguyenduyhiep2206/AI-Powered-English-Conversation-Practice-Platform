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
            className="ef-card-hover ef-card block rounded-[12px] border border-[#EAEAEA] bg-white p-6 transition-all duration-200 hover:shadow-[0_2px_8px_rgba(0,0,0,0.04)]"
          >
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-sm font-semibold tracking-tight">Books</h2>
              <Badge className="rounded-full bg-[#EDF3EC] text-[10px] uppercase tracking-[0.05em] text-[#346538] hover:bg-[#EDF3EC]">
                Active
              </Badge>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-[#787774]">
              Upload PDFs, detect structure, and index for learning content.
            </p>
          </Link>

          <Link
            href="/admin/quiz"
            className="ef-card-hover ef-card block rounded-[12px] border border-[#EAEAEA] bg-white p-6 transition-all duration-200 hover:shadow-[0_2px_8px_rgba(0,0,0,0.04)]"
          >
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-sm font-semibold tracking-tight">Quiz</h2>
              <Badge className="rounded-full bg-[#E1F3FE] text-[10px] uppercase tracking-[0.05em] text-[#1F6C9F] hover:bg-[#E1F3FE]">
                Active
              </Badge>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-[#787774]">
              Sync skills from indexed books, generate drafts, and publish.
            </p>
          </Link>

          <section className="ef-card rounded-[12px] border border-[#EAEAEA] bg-white p-6">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-sm font-semibold tracking-tight">Survey questions</h2>
              <Badge variant="outline" className="rounded-full text-[10px] uppercase tracking-[0.05em]">
                Soon
              </Badge>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-[#787774]">
              Create and edit onboarding survey questions.
            </p>
          </section>

          <section className="ef-card rounded-[12px] border border-[#EAEAEA] bg-white p-6">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-sm font-semibold tracking-tight">Users & roles</h2>
              <Badge variant="outline" className="rounded-full text-[10px] uppercase tracking-[0.05em]">
                Soon
              </Badge>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-[#787774]">
              View learners and assign admin or learner roles.
            </p>
          </section>

          <section className="ef-card rounded-[12px] border border-[#EAEAEA] bg-white p-6">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-sm font-semibold tracking-tight">Your access</h2>
              <Badge
                variant="secondary"
                className="rounded-full bg-[#FBF3DB] text-[10px] uppercase tracking-[0.05em] text-[#956400] hover:bg-[#FBF3DB]"
              >
                {user.roles.join(", ")}
              </Badge>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-[#787774]">
              {user.permissions.length} permissions active on this account.
            </p>
          </section>
        </div>
      </main>
    </>
  );
}
