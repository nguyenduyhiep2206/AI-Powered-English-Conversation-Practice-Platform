"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  listAdminSkills,
  type AdminLessonSkillRow,
} from "@/lib/admin-skills";

const CEFR_OPTIONS = ["", "A1", "A2", "B1", "B2", "C1"] as const;

export default function AdminSkillsPage() {
  const [rows, setRows] = useState<AdminLessonSkillRow[]>([]);
  const [cefr, setCefr] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRows(await listAdminSkills(cefr || undefined));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load skills");
    } finally {
      setLoading(false);
    }
  }, [cefr]);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => r.title.toLowerCase().includes(q));
  }, [rows, query]);

  return (
    <>
      <header className="border-b border-border px-6 py-5">
        <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
          Admin
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Skills</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Triage skills by lesson status, quiz drafts, and book attach. Workspace
          opens after skill-aligned / admin-skill-workspace land.
        </p>
      </header>

      <main className="flex-1 space-y-4 p-6">
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm text-[#787774]">
            CEFR{" "}
            <select
              className="ml-2 rounded-[6px] border border-[#EAEAEA] bg-white px-2 py-1.5 text-sm"
              value={cefr}
              onChange={(e) => setCefr(e.target.value)}
            >
              {CEFR_OPTIONS.map((level) => (
                <option key={level || "all"} value={level}>
                  {level || "All"}
                </option>
              ))}
            </select>
          </label>
          <input
            className="min-w-[200px] flex-1 rounded-[6px] border border-[#EAEAEA] px-3 py-1.5 text-sm outline-none focus:border-[#2F3437]"
            placeholder="Search title…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <Button type="button" size="sm" variant="outline" onClick={() => void load()}>
            Refresh
          </Button>
        </div>

        {error ? (
          <p className="text-sm text-[#9F2F2D]" role="alert">
            {error}
          </p>
        ) : null}

        {loading ? (
          <p className="text-sm text-[#787774]">Loading skills…</p>
        ) : (
          <div className="overflow-hidden rounded-[12px] border border-[#EAEAEA] bg-white">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-[#EAEAEA] bg-[#F7F6F3] text-[11px] uppercase tracking-[0.12em] text-[#787774]">
                <tr>
                  <th className="px-4 py-3 font-medium">Skill</th>
                  <th className="px-4 py-3 font-medium">Type</th>
                  <th className="px-4 py-3 font-medium">CEFR</th>
                  <th className="px-4 py-3 font-medium">Lesson</th>
                  <th className="px-4 py-3 font-medium">Quiz</th>
                  <th className="px-4 py-3 font-medium">Book</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((row) => (
                  <tr
                    key={row.skill_id}
                    className="border-b border-[#EAEAEA] last:border-0"
                  >
                    <td className="px-4 py-3 text-[#2F3437]">{row.title}</td>
                    <td className="px-4 py-3 text-[#787774]">{row.skill_type}</td>
                    <td className="px-4 py-3 text-[#787774]">{row.cefr_level}</td>
                    <td className="px-4 py-3">
                      {row.lesson_status ? (
                        <Badge variant="outline">{row.lesson_status}</Badge>
                      ) : (
                        <span className="text-[#787774]">none</span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px] text-[#787774]">
                      d{row.quiz_draft_count ?? 0} · p{row.quiz_published_count ?? 0}
                    </td>
                    <td className="px-4 py-3">
                      {row.has_book_source ? (
                        <span className="rounded-[4px] bg-[#EDF3EC] px-2 py-0.5 text-[10px] uppercase tracking-[0.05em] text-[#346538]">
                          attached
                        </span>
                      ) : (
                        <span className="rounded-[4px] bg-[#FBF3DB] px-2 py-0.5 text-[10px] uppercase tracking-[0.05em] text-[#956400]">
                          no book
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {row.has_book_source ? (
                        <span className="text-xs text-[#787774]">
                          Workspace soon
                        </span>
                      ) : (
                        <Button asChild size="sm" variant="outline">
                          <Link href="/admin/quiz">Open Attach</Link>
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </>
  );
}
