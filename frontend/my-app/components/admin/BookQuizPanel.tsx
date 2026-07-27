"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  generateSkillQuiz,
  listBookQuestions,
  publishQuestions,
  syncBookSkills,
  type QuizQuestionRow,
  type SkillSourceRow,
} from "@/lib/admin-quiz";

type PreviewUnit = {
  id: number;
  title: string;
};

type BookQuizPanelProps = {
  bookId: number;
  units: PreviewUnit[];
  onError: (message: string | null) => void;
};

export function BookQuizPanel({ bookId, units, onError }: BookQuizPanelProps) {
  const [sourcesByUnitId, setSourcesByUnitId] = useState<Record<number, SkillSourceRow>>(
    {},
  );
  const [syncing, setSyncing] = useState(false);
  const [generatingSkillId, setGeneratingSkillId] = useState<number | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<QuizQuestionRow[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [loadingDrafts, setLoadingDrafts] = useState(false);
  const [publishing, setPublishing] = useState(false);

  const refreshDrafts = useCallback(async () => {
    setLoadingDrafts(true);
    try {
      const rows = await listBookQuestions(bookId, "draft");
      setDrafts(rows);
      setSelectedIds(new Set());
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to load drafts");
    } finally {
      setLoadingDrafts(false);
    }
  }, [bookId, onError]);

  useEffect(() => {
    setSourcesByUnitId({});
    setStatusMessage(null);
    setGeneratingSkillId(null);
    setDrafts([]);
    setSelectedIds(new Set());
    void refreshDrafts();
  }, [bookId, refreshDrafts]);

  const syncSummary = useMemo(() => {
    const sources = Object.values(sourcesByUnitId);
    if (sources.length === 0) return null;
    const excluded = sources.filter((s) => s.is_excluded).length;
    return { total: sources.length, excluded };
  }, [sourcesByUnitId]);

  const hasSynced = Object.keys(sourcesByUnitId).length > 0;

  async function handleSync() {
    setSyncing(true);
    onError(null);
    setStatusMessage(null);
    try {
      const result = await syncBookSkills(bookId);
      const next: Record<number, SkillSourceRow> = {};
      for (const source of result.sources) {
        const existing = next[source.unit_id];
        if (
          !existing ||
          (source.is_primary && !source.is_excluded) ||
          (existing.is_excluded && !source.is_excluded)
        ) {
          next[source.unit_id] = source;
        }
      }
      setSourcesByUnitId(next);
      setStatusMessage(
        `Synced ${result.source_count} skill source(s); ${result.excluded} excluded` +
          (result.llm_used === true
            ? "; LLM refine on."
            : result.llm_used === false
              ? "; rule fallback."
              : "."),
      );
      await refreshDrafts();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to sync skills");
    } finally {
      setSyncing(false);
    }
  }

  async function handleGenerate(skillId: number, unitTitle: string) {
    setGeneratingSkillId(skillId);
    onError(null);
    setStatusMessage(null);
    try {
      const questions = await generateSkillQuiz(skillId);
      setStatusMessage(
        `Created ${questions.length} draft question(s) for “${unitTitle}”.`,
      );
      await refreshDrafts();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to generate quiz");
    } finally {
      setGeneratingSkillId(null);
    }
  }

  async function handlePublish() {
    if (selectedIds.size === 0) return;
    setPublishing(true);
    onError(null);
    try {
      const n = await publishQuestions([...selectedIds]);
      setStatusMessage(`Published ${n} question(s).`);
      await refreshDrafts();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to publish");
    } finally {
      setPublishing(false);
    }
  }

  function toggleSelected(id: number, checked: boolean) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  function selectAllDrafts() {
    setSelectedIds(new Set(drafts.map((q) => q.id)));
  }

  return (
    <div className="space-y-6">
      {statusMessage && (
        <p className="rounded-[8px] border border-[#EAEAEA] bg-[#EDF3EC] px-4 py-3 text-sm text-[#346538]">
          {statusMessage}
        </p>
      )}

      {/* Step 1 — Sync */}
      <section className="rounded-[12px] border border-[#EAEAEA] bg-white p-6 md:p-8">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-mono text-[11px] tracking-[0.08em] text-[#787774]">01</p>
            <h2 className="mt-1 text-sm font-semibold tracking-tight">Sync skills</h2>
            <p className="mt-1 text-sm text-[#787774]">
              Link book units to the skill graph before generating questions.
            </p>
          </div>
          <Button
            type="button"
            size="sm"
            className="rounded-[6px] bg-[#111111] text-white hover:bg-[#333333] active:scale-[0.98]"
            disabled={syncing || units.length === 0}
            onClick={handleSync}
          >
            {syncing ? <Loader2 className="h-4 w-4 animate-spin" /> : "Sync skills"}
          </Button>
        </div>

        {syncSummary && (
          <div className="mb-4 flex flex-wrap gap-2">
            <span className="rounded-full bg-[#E1F3FE] px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.05em] text-[#1F6C9F]">
              {syncSummary.total} sourced
            </span>
            {syncSummary.excluded > 0 && (
              <span className="rounded-full bg-[#FBF3DB] px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.05em] text-[#956400]">
                {syncSummary.excluded} excluded
              </span>
            )}
          </div>
        )}

        {units.length === 0 ? (
          <p className="text-sm text-[#787774]">
            No units available. Index the book before syncing skills.
          </p>
        ) : !hasSynced ? (
          <p className="text-sm text-[#787774]">
            Sync once to map units to skills. You can re-sync after structure changes.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-left text-sm">
              <thead className="border-b border-[#EAEAEA] text-[11px] uppercase tracking-[0.08em] text-[#787774]">
                <tr>
                  <th className="px-3 py-2 font-medium">Unit</th>
                  <th className="px-3 py-2 font-medium">Skill</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2 font-medium" />
                </tr>
              </thead>
              <tbody>
                {units.map((unit) => {
                  const source = sourcesByUnitId[unit.id];
                  if (!source) {
                    return (
                      <tr key={unit.id} className="border-b border-[#EAEAEA] last:border-0">
                        <td className="px-3 py-2.5 font-medium">{unit.title}</td>
                        <td className="px-3 py-2.5 text-[#787774]">—</td>
                        <td className="px-3 py-2.5 text-[#787774]">Not linked</td>
                        <td className="px-3 py-2.5" />
                      </tr>
                    );
                  }

                  const canGenerate = !source.is_excluded;
                  return (
                    <tr key={unit.id} className="border-b border-[#EAEAEA] last:border-0">
                      <td className="px-3 py-2.5 font-medium">{unit.title}</td>
                      <td className="px-3 py-2.5 font-mono text-xs text-[#787774]">
                        #{source.skill_id}
                      </td>
                      <td className="px-3 py-2.5">
                        {source.is_excluded ? (
                          <span className="rounded-full bg-[#F9F9F8] px-2.5 py-0.5 text-[10px] uppercase tracking-[0.05em] text-[#787774]">
                            Excluded
                          </span>
                        ) : source.is_primary ? (
                          <span className="rounded-full bg-[#EDF3EC] px-2.5 py-0.5 text-[10px] uppercase tracking-[0.05em] text-[#346538]">
                            Primary
                          </span>
                        ) : (
                          <span className="rounded-full bg-[#E1F3FE] px-2.5 py-0.5 text-[10px] uppercase tracking-[0.05em] text-[#1F6C9F]">
                            Linked
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        {canGenerate && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            disabled={generatingSkillId === source.skill_id}
                            onClick={() => handleGenerate(source.skill_id, unit.title)}
                          >
                            {generatingSkillId === source.skill_id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              "Generate"
                            )}
                          </Button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Step 2+3 — Generate hint sits in table; Publish drafts */}
      <section className="rounded-[12px] border border-[#EAEAEA] bg-white p-6 md:p-8">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-mono text-[11px] tracking-[0.08em] text-[#787774]">
              02–03
            </p>
            <h2 className="mt-1 text-sm font-semibold tracking-tight">Draft questions</h2>
            <p className="mt-1 text-sm text-[#787774]">
              Generate from a synced skill above, review drafts, then publish.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="rounded-[6px] border-[#EAEAEA] shadow-none"
              disabled={loadingDrafts}
              onClick={() => void refreshDrafts()}
            >
              {loadingDrafts ? <Loader2 className="h-4 w-4 animate-spin" /> : "Refresh"}
            </Button>
            {drafts.length > 0 && (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={selectAllDrafts}
              >
                Select all
              </Button>
            )}
            <Button
              type="button"
              size="sm"
              className="rounded-[6px] bg-[#111111] text-white hover:bg-[#333333] active:scale-[0.98]"
              disabled={publishing || selectedIds.size === 0}
              onClick={() => void handlePublish()}
            >
              {publishing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                `Publish (${selectedIds.size})`
              )}
            </Button>
          </div>
        </div>

        {drafts.length === 0 ? (
          <p className="text-sm text-[#787774]">
            No drafts yet. Sync skills, then generate quiz for a unit.
          </p>
        ) : (
          <ul className="max-h-80 space-y-2 overflow-y-auto">
            {drafts.map((q) => (
              <li
                key={q.id}
                className="flex items-start gap-3 rounded-[8px] border border-[#EAEAEA] px-4 py-3 transition-colors hover:bg-[#F9F9F8]"
              >
                <input
                  type="checkbox"
                  className="mt-1 size-4 accent-[#111111]"
                  checked={selectedIds.has(q.id)}
                  onChange={(e) => toggleSelected(q.id, e.target.checked)}
                />
                <div className="min-w-0 flex-1">
                  <p className="font-mono text-[11px] text-[#787774]">
                    #{q.id} · skill {q.skill_id} · {q.question_type}
                  </p>
                  {q.passage ? (
                    <p className="mt-1 line-clamp-3 whitespace-pre-wrap text-xs leading-relaxed text-[#787774]">
                      {q.passage}
                    </p>
                  ) : null}
                  <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-[#111111]">
                    {q.stem}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
