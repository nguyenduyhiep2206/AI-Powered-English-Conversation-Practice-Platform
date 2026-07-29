"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import LessonContentPreview from "@/components/lesson/LessonContentPreview";
import {
  generateAdminLesson,
  getAdminLesson,
  listAdminLessonSkills,
  publishAdminLesson,
  type AdminLessonSkillRow,
} from "@/lib/admin-lessons";
import type { SkillLesson } from "@/lib/lesson";

export default function AdminLessonsPage() {
  const [rows, setRows] = useState<AdminLessonSkillRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<SkillLesson | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRows(await listAdminLessonSkills());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function onGenerate(skillId: number) {
    setBusyId(skillId);
    setError(null);
    try {
      const lesson = await generateAdminLesson(skillId);
      setPreview(lesson);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generate failed");
    } finally {
      setBusyId(null);
    }
  }

  async function onPublish(skillId: number) {
    setBusyId(skillId);
    setError(null);
    try {
      const lesson = await publishAdminLesson(skillId);
      setPreview(lesson);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Publish failed");
    } finally {
      setBusyId(null);
    }
  }

  async function onPreview(skillId: number) {
    setBusyId(skillId);
    setError(null);
    try {
      setPreview(await getAdminLesson(skillId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Load failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <header className="border-b border-border px-6 py-5">
        <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
          Admin
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Lessons</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Generate mini-unit drafts (passage → targets → checks → writing) and
          publish.
        </p>
      </header>

      <main className="flex-1 space-y-6 p-6">
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
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.skill_id} className="border-b border-[#EAEAEA] last:border-0">
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
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          disabled={busyId === row.skill_id}
                          onClick={() => void onGenerate(row.skill_id)}
                        >
                          Generate
                        </Button>
                        {row.lesson_status ? (
                          <>
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              disabled={busyId === row.skill_id}
                              onClick={() => void onPreview(row.skill_id)}
                            >
                              View
                            </Button>
                            {row.lesson_status !== "published" ? (
                              <Button
                                type="button"
                                size="sm"
                                disabled={busyId === row.skill_id}
                                onClick={() => void onPublish(row.skill_id)}
                              >
                                Publish
                              </Button>
                            ) : null}
                          </>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      <LessonContentPreview lesson={preview} onClose={() => setPreview(null)} />
    </>
  );
}
