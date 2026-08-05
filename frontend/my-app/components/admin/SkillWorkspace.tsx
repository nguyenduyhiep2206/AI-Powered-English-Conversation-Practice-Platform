"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import LessonContentPreview from "@/components/lesson/LessonContentPreview";
import {
  generateAdminLessonPack,
  getAdminLesson,
  publishAdminLessonPack,
} from "@/lib/admin-lessons";
import {
  generateSkillQuiz,
  generateSkillWriting,
  listSkillQuestions,
  publishQuestions,
  type QuizQuestionRow,
} from "@/lib/admin-quiz";
import {
  blockReasonLabel,
  fetchSkillWorkspace,
  type SkillWorkspace,
} from "@/lib/admin-skills";
import type { SkillLesson } from "@/lib/lesson";

type Props = {
  skillId: number;
};

type ListStatus = "draft" | "published";
type DrillModeFilter = "all" | "skill_drill" | "toeic";

function statusBadge(status: string | null | undefined) {
  if (!status) return <span className="text-sm text-[#787774]">none</span>;
  return <Badge variant="outline">{status}</Badge>;
}

function questionMode(q: QuizQuestionRow): string {
  const brief = (q.task_brief || {}) as Record<string, unknown>;
  if (typeof brief.mode === "string") return brief.mode;
  if (
    q.question_type === "writing" ||
    q.question_type?.startsWith("writing") ||
    q.question_type === "w1" ||
    q.question_type === "w2" ||
    q.question_type === "w3"
  ) {
    return "writing";
  }
  if (q.toeic_part) return "toeic";
  return "skill_drill";
}

function isWritingQuestion(q: QuizQuestionRow): boolean {
  return questionMode(q) === "writing" || q.question_type === "writing";
}

function writingCueWords(q: QuizQuestionRow): string[] {
  if (Array.isArray(q.prompt_words) && q.prompt_words.length) {
    return q.prompt_words.filter((w): w is string => typeof w === "string");
  }
  const brief = (q.task_brief || {}) as Record<string, unknown>;
  const words = brief.prompt_words ?? brief.words;
  if (Array.isArray(words)) {
    return words.filter((w): w is string => typeof w === "string");
  }
  return [];
}

function StatusTabs({
  value,
  onChange,
}: {
  value: ListStatus;
  onChange: (v: ListStatus) => void;
}) {
  return (
    <div className="flex rounded-[6px] border border-[#EAEAEA] p-0.5">
      {(["draft", "published"] as const).map((tab) => (
        <button
          key={tab}
          type="button"
          className={
            value === tab
              ? "rounded-[4px] bg-[#111111] px-2.5 py-1 text-xs text-white"
              : "rounded-[4px] px-2.5 py-1 text-xs text-[#787774]"
          }
          onClick={() => onChange(tab)}
        >
          {tab === "draft" ? "Draft" : "Published"}
        </button>
      ))}
    </div>
  );
}

export default function SkillWorkspace({ skillId }: Props) {
  const [ws, setWs] = useState<SkillWorkspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [preview, setPreview] = useState<SkillLesson | null>(null);
  const [previewPack, setPreviewPack] = useState<SkillLesson[]>([]);
  const [showToeic, setShowToeic] = useState(false);

  const [drillStatus, setDrillStatus] = useState<ListStatus>("draft");
  const [writingStatus, setWritingStatus] = useState<ListStatus>("draft");
  const [drillModeFilter, setDrillModeFilter] = useState<DrillModeFilter>("all");
  const [drillQuestions, setDrillQuestions] = useState<QuizQuestionRow[]>([]);
  const [writingQuestions, setWritingQuestions] = useState<QuizQuestionRow[]>([]);
  const [selectedDrillIds, setSelectedDrillIds] = useState<Set<number>>(new Set());
  const [selectedWritingIds, setSelectedWritingIds] = useState<Set<number>>(
    new Set(),
  );

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSkillWorkspace(skillId);
      setWs(data);
      const [drillRows, writingRows] = await Promise.all([
        listSkillQuestions(skillId, drillStatus),
        listSkillQuestions(skillId, writingStatus),
      ]);
      setDrillQuestions(drillRows.filter((q) => !isWritingQuestion(q)));
      setWritingQuestions(writingRows.filter((q) => isWritingQuestion(q)));
      setSelectedDrillIds(new Set());
      setSelectedWritingIds(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load workspace");
    } finally {
      setLoading(false);
    }
  }, [skillId, drillStatus, writingStatus]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const filteredDrill = useMemo(() => {
    if (drillModeFilter === "all") return drillQuestions;
    return drillQuestions.filter((q) => questionMode(q) === drillModeFilter);
  }, [drillQuestions, drillModeFilter]);

  async function run(label: string, fn: () => Promise<void>) {
    setBusy(label);
    setError(null);
    setStatusMessage(null);
    try {
      await fn();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  async function publishSelected(ids: number[], label: string) {
    await run(label, async () => {
      const result = await publishQuestions(ids);
      const align =
        result.skipped_alignment > 0
          ? ` (${result.skipped_alignment} skipped alignment)`
          : "";
      setStatusMessage(
        result.skipped > 0
          ? `Published ${result.published}; skipped ${result.skipped}${align}.`
          : `Published ${result.published} question(s).`,
      );
    });
  }

  if (loading && !ws) {
    return (
      <p className="flex items-center gap-2 p-6 text-sm text-[#787774]">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading workspace…
      </p>
    );
  }

  if (!ws) {
    return (
      <p className="p-6 text-sm text-[#9F2F2D]" role="alert">
        {error || "Skill not found"}
      </p>
    );
  }

  const drillBlocked = !ws.quiz.can_generate_skill_drill;
  const blockHint = blockReasonLabel(ws.quiz.block_reason);
  const drillIsDraft = drillStatus === "draft";
  const writingIsDraft = writingStatus === "draft";

  return (
    <div className="space-y-6 p-6">
      <div>
        <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
          Skill workspace
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[#2F3437]">
          {ws.skill.title}
        </h1>
        <p className="mt-1 text-sm text-[#787774]">
          {ws.skill.skill_type} · {ws.skill.cefr_level}
          {ws.book_source
            ? ` · ${ws.book_source.unit_title || `unit ${ws.book_source.unit_id}`}`
            : " · no book attached"}
        </p>
        {!ws.book_source ? (
          <p className="mt-2 text-sm text-[#956400]">
            Attach a book unit first:{" "}
            <Link href="/admin/quiz" className="underline underline-offset-2">
              Open Attach
            </Link>
            .
          </p>
        ) : null}
      </div>

      {error ? (
        <p
          className="rounded-[8px] border border-[#FDEBEC] bg-[#FDEBEC] px-4 py-3 text-sm text-[#9F2F2D]"
          role="alert"
        >
          {error}
        </p>
      ) : null}
      {statusMessage ? (
        <p className="rounded-[8px] border border-[#EAEAEA] bg-[#EDF3EC] px-4 py-3 text-sm text-[#346538]">
          {statusMessage}
        </p>
      ) : null}

      {/* 01 Lesson */}
      <section className="rounded-[12px] border border-[#EAEAEA] bg-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-mono text-[11px] text-[#787774]">01</p>
            <h2 className="mt-1 text-sm font-semibold">Lesson pack</h2>
            <p className="mt-1 text-sm text-[#787774]">
              Generate 3 micro-lessons (L1–L3), review, then publish the pack
              before grammar drills.
            </p>
            <div className="mt-2">{statusBadge(ws.lesson.status)}</div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={busy !== null}
              onClick={() =>
                void run("lesson-pack-gen", async () => {
                  const pack = await generateAdminLessonPack(skillId);
                  setPreviewPack(pack);
                  setPreview(pack[0] ?? null);
                  setStatusMessage(
                    `LessonPack draft created (${pack.length} micro-lessons).`,
                  );
                })
              }
            >
              {busy === "lesson-pack-gen" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Generate pack"
              )}
            </Button>
            {ws.lesson.status ? (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                disabled={busy !== null}
                onClick={() =>
                  void run("lesson-view", async () => {
                    const data = await getAdminLesson(skillId);
                    const pack = data.pack ?? [data];
                    setPreviewPack(pack);
                    setPreview(pack[0] ?? data);
                    const n = pack.length;
                    setStatusMessage(
                      n > 1
                        ? `Loaded pack: ${n} lessons — use L1/L2/L3 tabs in preview.`
                        : "Loaded lesson.",
                    );
                  })
                }
              >
                View
              </Button>
            ) : null}
            {ws.lesson.status && ws.lesson.status !== "published" ? (
              <Button
                type="button"
                size="sm"
                disabled={busy !== null}
                onClick={() =>
                  void run("lesson-pack-pub", async () => {
                    const pack = await publishAdminLessonPack(skillId);
                    setStatusMessage(
                      `LessonPack published (${pack.length} micro-lessons).`,
                    );
                  })
                }
              >
                {busy === "lesson-pack-pub" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  "Publish pack"
                )}
              </Button>
            ) : null}
          </div>
        </div>
      </section>

      {/* 02 Skill drill */}
      <section className="rounded-[12px] border border-[#EAEAEA] bg-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-mono text-[11px] text-[#787774]">02</p>
            <h2 className="mt-1 text-sm font-semibold">Skill drill</h2>
            <p className="mt-1 text-sm text-[#787774]">
              One Practice checkpoint after the lesson pack (~10 items), aligned
              to union targets — not one drill per micro-lesson.
            </p>
            <p className="mt-2 text-xs text-[#787774]">
              Drafts: {ws.quiz.draft_count} · Published: {ws.quiz.published_count} ·
              skill_drill drafts: {ws.quiz.draft_skill_drill_count}
            </p>
            {drillBlocked && blockHint ? (
              <p className="mt-2 text-sm text-[#956400]">{blockHint}</p>
            ) : null}
          </div>
          <Button
            type="button"
            size="sm"
            disabled={busy !== null || drillBlocked}
            onClick={() => {
              setDrillStatus("draft");
              void run("drill", async () => {
                const rows = await generateSkillQuiz(skillId, 10, "skill_drill");
                setStatusMessage(
                  `Created ${rows.length} skill-drill draft(s) (pack checkpoint).`,
                );
              });
            }}
          >
            {busy === "drill" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              "Generate drill"
            )}
          </Button>
        </div>

        <div className="mt-5">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <StatusTabs value={drillStatus} onChange={setDrillStatus} />
              <select
                className="rounded-[6px] border border-[#EAEAEA] bg-white px-2 py-1 text-xs"
                value={drillModeFilter}
                onChange={(e) =>
                  setDrillModeFilter(e.target.value as DrillModeFilter)
                }
              >
                <option value="all">All (drill + TOEIC)</option>
                <option value="skill_drill">skill_drill</option>
                <option value="toeic">toeic</option>
              </select>
            </div>
            <div className="flex gap-2">
              {drillIsDraft && filteredDrill.length > 0 ? (
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={() =>
                    setSelectedDrillIds(new Set(filteredDrill.map((d) => d.id)))
                  }
                >
                  Select all
                </Button>
              ) : null}
              {drillIsDraft ? (
                <Button
                  type="button"
                  size="sm"
                  disabled={busy !== null || selectedDrillIds.size === 0}
                  onClick={() =>
                    void publishSelected([...selectedDrillIds], "publish-drill")
                  }
                >
                  {busy === "publish-drill" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    `Publish (${selectedDrillIds.size})`
                  )}
                </Button>
              ) : null}
            </div>
          </div>

          {filteredDrill.length === 0 ? (
            <p className="text-sm text-[#787774]">
              No {drillStatus} drill questions for this filter.
            </p>
          ) : (
            <ul className="max-h-80 space-y-2 overflow-y-auto">
              {filteredDrill.map((q) => {
                const brief = (q.task_brief || {}) as Record<string, unknown>;
                const mode = typeof brief.mode === "string" ? brief.mode : null;
                const kind =
                  typeof brief.item_kind === "string" ? brief.item_kind : null;
                return (
                  <li
                    key={q.id}
                    className="flex items-start gap-3 rounded-[8px] border border-[#EAEAEA] px-4 py-3"
                  >
                    {drillIsDraft ? (
                      <input
                        type="checkbox"
                        className="mt-1 size-4 accent-[#111111]"
                        checked={selectedDrillIds.has(q.id)}
                        onChange={(e) => {
                          setSelectedDrillIds((prev) => {
                            const next = new Set(prev);
                            if (e.target.checked) next.add(q.id);
                            else next.delete(q.id);
                            return next;
                          });
                        }}
                      />
                    ) : null}
                    <div className="min-w-0 flex-1">
                      <p className="font-mono text-[11px] text-[#787774]">
                        #{q.id} · {q.question_type}
                        {kind ? ` · ${kind}` : ""}
                        {mode ? ` · ${mode}` : ""}
                        {q.toeic_part ? ` · ${q.toeic_part}` : ""}
                      </p>
                      <p className="mt-1 line-clamp-2 text-sm text-[#111111]">
                        {q.stem}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="mt-5 border-t border-[#EAEAEA] pt-4">
          <button
            type="button"
            className="text-sm text-[#1F6C9F] underline-offset-2 hover:underline"
            onClick={() => setShowToeic((v) => !v)}
          >
            {showToeic ? "Hide" : "Show"} advanced: TOEIC mode
          </button>
          {showToeic ? (
            <div className="mt-3">
              <p className="text-sm text-[#787774]">
                Generates classic TOEIC R5–R7 reading items (not skill-aligned drills).
              </p>
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="mt-2"
                disabled={busy !== null || !ws.book_source}
                onClick={() => {
                  setDrillStatus("draft");
                  void run("toeic", async () => {
                    const rows = await generateSkillQuiz(skillId, 6, "toeic");
                    setStatusMessage(`Created ${rows.length} TOEIC draft(s).`);
                  });
                }}
              >
                {busy === "toeic" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  "Generate TOEIC"
                )}
              </Button>
            </div>
          ) : null}
        </div>
      </section>

      {/* 03 Writing */}
      <section className="rounded-[12px] border border-[#EAEAEA] bg-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-mono text-[11px] text-[#787774]">03</p>
            <h2 className="mt-1 text-sm font-semibold">Writing (optional)</h2>
            <p className="mt-1 text-sm text-[#787774]">
              TOEIC-style writing tasks (W1–W3). Review drafts here, then publish.
            </p>
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={busy !== null || !ws.book_source}
            onClick={() => {
              setWritingStatus("draft");
              void run("writing", async () => {
                const rows = await generateSkillWriting(skillId, 2);
                setStatusMessage(`Created ${rows.length} writing draft(s).`);
              });
            }}
          >
            {busy === "writing" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              "Generate writing"
            )}
          </Button>
        </div>

        <div className="mt-5">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <StatusTabs value={writingStatus} onChange={setWritingStatus} />
            <div className="flex gap-2">
              {writingIsDraft && writingQuestions.length > 0 ? (
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={() =>
                    setSelectedWritingIds(
                      new Set(writingQuestions.map((d) => d.id)),
                    )
                  }
                >
                  Select all
                </Button>
              ) : null}
              {writingIsDraft ? (
                <Button
                  type="button"
                  size="sm"
                  disabled={busy !== null || selectedWritingIds.size === 0}
                  onClick={() =>
                    void publishSelected(
                      [...selectedWritingIds],
                      "publish-writing",
                    )
                  }
                >
                  {busy === "publish-writing" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    `Publish (${selectedWritingIds.size})`
                  )}
                </Button>
              ) : null}
            </div>
          </div>

          {writingQuestions.length === 0 ? (
            <p className="text-sm text-[#787774]">
              No {writingStatus} writing tasks yet.
            </p>
          ) : (
            <ul className="max-h-80 space-y-2 overflow-y-auto">
              {writingQuestions.map((q) => {
                const brief = (q.task_brief || {}) as Record<string, unknown>;
                const part =
                  typeof brief.part === "string"
                    ? brief.part
                    : q.toeic_part || null;
                const cues = writingCueWords(q);
                const minWords =
                  typeof brief.min_words === "number" ? brief.min_words : null;
                return (
                  <li
                    key={q.id}
                    className="flex items-start gap-3 rounded-[8px] border border-[#EAEAEA] px-4 py-3"
                  >
                    {writingIsDraft ? (
                      <input
                        type="checkbox"
                        className="mt-1 size-4 accent-[#111111]"
                        checked={selectedWritingIds.has(q.id)}
                        onChange={(e) => {
                          setSelectedWritingIds((prev) => {
                            const next = new Set(prev);
                            if (e.target.checked) next.add(q.id);
                            else next.delete(q.id);
                            return next;
                          });
                        }}
                      />
                    ) : null}
                    <div className="min-w-0 flex-1">
                      <p className="font-mono text-[11px] text-[#787774]">
                        #{q.id} · writing
                        {part ? ` · ${part}` : ""}
                        {minWords != null ? ` · min ${minWords} words` : ""}
                      </p>
                      <p className="mt-1 text-sm text-[#111111]">{q.stem}</p>
                      {cues.length > 0 ? (
                        <p className="mt-2 text-xs text-[#787774]">
                          Cue words: {cues.join(" · ")}
                        </p>
                      ) : null}
                      {q.passage ? (
                        <p className="mt-2 line-clamp-3 whitespace-pre-wrap text-xs text-[#787774]">
                          {q.passage}
                        </p>
                      ) : null}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </section>

      <LessonContentPreview
        lesson={preview}
        pack={previewPack.length > 0 ? previewPack : null}
        onClose={() => {
          setPreview(null);
          setPreviewPack([]);
        }}
      />
    </div>
  );
}
