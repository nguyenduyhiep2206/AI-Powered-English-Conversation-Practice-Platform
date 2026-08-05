"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  enrichBookUnits,
  fetchBookStructurePreview,
  type StructureUnitPreview,
} from "@/lib/admin-books";
import {
  fetchBookSkillSources,
  listBookQuestions,
  publishQuestions,
  syncBookSkills,
  type QuizQuestionRow,
  type SkillSourceRow,
} from "@/lib/admin-quiz";

type PreviewUnit = {
  id: number;
  title: string;
  language_focus?: string | null;
  grammar_cues?: string[] | null;
  enrichment_method?: string | null;
};

type BookQuizPanelProps = {
  bookId: number;
  units: PreviewUnit[];
  onError: (message: string | null) => void;
};

function unitSignalLine(unit: {
  language_focus?: string | null;
  grammar_cues?: string[] | null;
}): string | null {
  const parts: string[] = [];
  if (unit.language_focus?.trim()) parts.push(unit.language_focus.trim());
  const cues = (unit.grammar_cues ?? []).filter((c) => c.trim());
  if (cues.length) parts.push(cues.join(", "));
  return parts.length ? parts.join(" · ") : null;
}

function uniqueMappedSkills(sources: SkillSourceRow[]): SkillSourceRow[] {
  const seen = new Set<number>();
  const out: SkillSourceRow[] = [];
  for (const s of sources) {
    if (s.is_excluded) continue;
    if (seen.has(s.skill_id)) continue;
    seen.add(s.skill_id);
    out.push(s);
  }
  return out;
}

export function BookQuizPanel({ bookId, units, onError }: BookQuizPanelProps) {
  const [sourcesByUnitId, setSourcesByUnitId] = useState<Record<number, SkillSourceRow>>(
    {},
  );
  const [unitMetaById, setUnitMetaById] = useState<
    Record<number, StructureUnitPreview>
  >({});
  const [sourcesLoaded, setSourcesLoaded] = useState(false);
  const [loadingSources, setLoadingSources] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [continueSkills, setContinueSkills] = useState<SkillSourceRow[]>([]);
  const [unmappedUnits, setUnmappedUnits] = useState<
    { unit_index: number; unit_title: string }[]
  >([]);
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

  function applySources(
    sources: SkillSourceRow[],
    unmapped: { unit_index: number; unit_title: string }[],
  ) {
    const next: Record<number, SkillSourceRow> = {};
    for (const source of sources) {
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
    setUnmappedUnits(unmapped);
    setSourcesLoaded(true);
  }

  const refreshUnitMeta = useCallback(
    async (opts?: { reportError?: boolean }) => {
      try {
        const preview = await fetchBookStructurePreview(bookId);
        const next: Record<number, StructureUnitPreview> = {};
        for (const u of preview.units ?? []) {
          next[u.id] = u;
        }
        setUnitMetaById(next);
      } catch (err) {
        if (opts?.reportError) {
          onError(err instanceof Error ? err.message : "Failed to refresh unit meta");
        }
      }
    },
    [bookId, onError],
  );

  const refreshSources = useCallback(
    async (opts?: { reportError?: boolean }): Promise<boolean> => {
      setLoadingSources(true);
      try {
        const result = await fetchBookSkillSources(bookId);
        applySources(result.sources, result.unmapped_units ?? []);
        return true;
      } catch (err) {
        if (opts?.reportError) {
          onError(err instanceof Error ? err.message : "Failed to load skill sources");
        }
        setSourcesLoaded(true);
        return false;
      } finally {
        setLoadingSources(false);
      }
    },
    [bookId, onError],
  );

  useEffect(() => {
    void refreshSources();
    void refreshUnitMeta();
    void refreshDrafts();
  }, [bookId, refreshDrafts, refreshUnitMeta, refreshSources]);

  const syncSummary = useMemo(() => {
    const sources = Object.values(sourcesByUnitId);
    if (sources.length === 0 && unmappedUnits.length === 0) return null;
    const excluded = sources.filter((s) => s.is_excluded).length;
    return {
      total: sources.length,
      excluded,
      unmapped: unmappedUnits.length,
    };
  }, [sourcesByUnitId, unmappedUnits]);

  const hasSynced =
    Object.keys(sourcesByUnitId).length > 0 || unmappedUnits.length > 0;

  async function handleSync() {
    if (hasSynced) {
      const ok = window.confirm(
        "Retry will re-enrich all units and replace existing catalog mappings. Continue?",
      );
      if (!ok) return;
    }
    setSyncing(true);
    onError(null);
    setStatusMessage(null);
    setContinueSkills([]);
    try {
      const result = await syncBookSkills(bookId);
      const unmapped = result.unmapped_units ?? [];
      applySources(result.sources, unmapped);
      const mapped = result.mapped_count ?? result.source_count;
      const enriched =
        typeof result.enriched === "number" ? result.enriched : null;
      setContinueSkills(uniqueMappedSkills(result.sources).slice(0, 8));
      setStatusMessage(
        `Attached ${mapped} unit(s) to the CEFR catalog` +
          (enriched != null ? `; enriched ${enriched}` : "") +
          (result.excluded ? `; ${result.excluded} excluded` : "") +
          (unmapped.length ? `; ${unmapped.length} unmapped` : "") +
          (result.llm_used === true
            ? " (LLM)."
            : result.llm_used === false
              ? " (rule fallback)."
              : "."),
      );
      await refreshUnitMeta({ reportError: true });
      await refreshDrafts();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to sync skills");
    } finally {
      setSyncing(false);
    }
  }

  async function handleEnrich() {
    setEnriching(true);
    onError(null);
    setStatusMessage(null);
    try {
      const result = await enrichBookUnits(bookId);
      setStatusMessage(
        `Re-enriched ${result.enriched} unit(s). Run Attach to rematch the catalog if needed.`,
      );
      await refreshUnitMeta({ reportError: true });
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to enrich units");
    } finally {
      setEnriching(false);
    }
  }

  async function handlePublish() {
    if (selectedIds.size === 0) return;
    setPublishing(true);
    onError(null);
    try {
      const { published, skipped, skipped_alignment } = await publishQuestions([
        ...selectedIds,
      ]);
      const alignNote =
        skipped_alignment > 0
          ? ` (${skipped_alignment} skipped for skill-drill alignment)`
          : "";
      setStatusMessage(
        skipped > 0
          ? `Published ${published}; skipped ${skipped}${alignNote}.`
          : `Published ${published} question(s).`,
      );
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

      {continueSkills.length > 0 ? (
        <div className="rounded-[8px] border border-[#E1F3FE] bg-[#E1F3FE]/40 px-4 py-3 text-sm text-[#1F6C9F]">
          <p className="font-medium">Continue in Skills</p>
          <p className="mt-1 text-[#787774]">
            Generate lesson and drills in the skill workspace (not on this page).
          </p>
          <ul className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
            {continueSkills.map((s) => (
              <li key={s.skill_id}>
                <Link
                  href={`/admin/skills/${s.skill_id}`}
                  className="underline underline-offset-2"
                >
                  {s.skill_title?.trim() || `Skill #${s.skill_id}`}
                </Link>
              </li>
            ))}
            <li>
              <Link href="/admin/skills" className="underline underline-offset-2">
                All skills →
              </Link>
            </li>
          </ul>
        </div>
      ) : null}

      <section className="rounded-[12px] border border-[#EAEAEA] bg-white p-6 md:p-8">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-mono text-[11px] tracking-[0.08em] text-[#787774]">01</p>
            <h2 className="mt-1 text-sm font-semibold tracking-tight">
              Attach to CEFR catalog
            </h2>
            <p className="mt-1 text-sm text-[#787774]">
              Enrich unit signals then map onto seeded ladder skills (A1/A2). Unmapped
              units stay out of the learner path until they match a catalog skill.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="rounded-[6px] border-[#EAEAEA] shadow-none"
              disabled={enriching || syncing || units.length === 0}
              onClick={() => void handleEnrich()}
            >
              {enriching ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Re-enrich units"
              )}
            </Button>
            <Button
              type="button"
              size="sm"
              className="rounded-[6px] bg-[#111111] text-white hover:bg-[#333333] active:scale-[0.98]"
              disabled={syncing || units.length === 0 || loadingSources}
              onClick={handleSync}
            >
              {syncing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : hasSynced ? (
                "Retry attach"
              ) : (
                "Attach units"
              )}
            </Button>
          </div>
        </div>

        {syncSummary && (
          <div className="mb-4 flex flex-wrap gap-2">
            <span className="rounded-[4px] bg-[#E1F3FE] px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.05em] text-[#1F6C9F]">
              {syncSummary.total} attached
            </span>
            {syncSummary.excluded > 0 && (
              <span className="rounded-[4px] bg-[#FBF3DB] px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.05em] text-[#956400]">
                {syncSummary.excluded} excluded
              </span>
            )}
            {syncSummary.unmapped > 0 && (
              <span className="rounded-[4px] bg-[#FDEBEC] px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.05em] text-[#9F2F2D]">
                {syncSummary.unmapped} unmapped
              </span>
            )}
          </div>
        )}

        {units.length === 0 ? (
          <p className="text-sm text-[#787774]">
            No units available. Index the book before attaching to the catalog.
          </p>
        ) : (
          <div className="space-y-4">
            {!sourcesLoaded || loadingSources ? (
              <p className="flex items-center gap-2 text-sm text-[#787774]">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading attach status…
              </p>
            ) : !hasSynced ? (
              <p className="text-sm text-[#787774]">
                Attach extracts language focus / grammar cues from each unit, then maps
                onto the CEFR catalog. Retry after structure changes.
              </p>
            ) : null}
            {unmappedUnits.length > 0 ? (
              <div className="rounded-[8px] border border-[#EAEAEA] bg-[#F9F9F8] px-4 py-3">
                <p className="text-xs font-medium text-[#111111]">Unmapped units</p>
                <p className="mt-1 text-xs text-[#787774]">
                  Unit not mapped to catalog — Retry attach or check CEFR seed /
                  enrichment. There is no remap editor here.
                </p>
                <ul className="mt-2 space-y-1 text-sm text-[#787774]">
                  {unmappedUnits.map((u) => (
                    <li key={`${u.unit_index}-${u.unit_title}`}>
                      <span className="font-mono text-[11px] text-[#787774]">
                        #{u.unit_index}
                      </span>{" "}
                      {u.unit_title}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead className="border-b border-[#EAEAEA] text-[11px] uppercase tracking-[0.08em] text-[#787774]">
                  <tr>
                    <th className="px-3 py-2 font-medium">Unit</th>
                    <th className="px-3 py-2 font-medium">Catalog skill</th>
                    <th className="px-3 py-2 font-medium">Status</th>
                    <th className="px-3 py-2 font-medium" />
                  </tr>
                </thead>
                <tbody>
                  {units.map((unit) => {
                    const source = sourcesByUnitId[unit.id];
                    const meta = unitMetaById[unit.id];
                    const signal = unitSignalLine(meta ?? unit);
                    const method =
                      meta?.enrichment_method ?? unit.enrichment_method ?? null;
                    const unitCell = (
                      <td className="px-3 py-2.5">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-medium">{unit.title}</span>
                          {method && method !== "skipped" ? (
                            <span className="rounded-[4px] bg-[#F9F9F8] px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.05em] text-[#787774]">
                              {method}
                            </span>
                          ) : null}
                        </div>
                        {signal ? (
                          <p className="mt-1 text-xs leading-relaxed text-[#787774]">
                            {signal}
                          </p>
                        ) : null}
                      </td>
                    );
                    if (!source) {
                      return (
                        <tr
                          key={unit.id}
                          className="border-b border-[#EAEAEA] last:border-0"
                        >
                          {unitCell}
                          <td className="px-3 py-2.5 text-[#787774]">—</td>
                          <td className="px-3 py-2.5">
                            {hasSynced ? (
                              <span className="rounded-[4px] bg-[#FDEBEC] px-2.5 py-0.5 text-[10px] uppercase tracking-[0.05em] text-[#9F2F2D]">
                                Unmapped
                              </span>
                            ) : (
                              <span className="text-[#787774]">—</span>
                            )}
                          </td>
                          <td className="px-3 py-2.5" />
                        </tr>
                      );
                    }

                    return (
                      <tr
                        key={unit.id}
                        className="border-b border-[#EAEAEA] last:border-0"
                      >
                        {unitCell}
                        <td className="px-3 py-2.5">
                          <span className="font-medium text-[#111111]">
                            {source.skill_title?.trim() || `#${source.skill_id}`}
                          </span>
                        </td>
                        <td className="px-3 py-2.5">
                          {source.is_excluded ? (
                            <span className="rounded-[4px] bg-[#F9F9F8] px-2.5 py-0.5 text-[10px] uppercase tracking-[0.05em] text-[#787774]">
                              Excluded
                            </span>
                          ) : source.is_primary ? (
                            <span className="rounded-[4px] bg-[#EDF3EC] px-2.5 py-0.5 text-[10px] uppercase tracking-[0.05em] text-[#346538]">
                              Primary
                            </span>
                          ) : (
                            <span className="rounded-[4px] bg-[#E1F3FE] px-2.5 py-0.5 text-[10px] uppercase tracking-[0.05em] text-[#1F6C9F]">
                              Linked
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2.5 text-right">
                          {!source.is_excluded ? (
                            <Link
                              href={`/admin/skills/${source.skill_id}`}
                              className="text-[11px] text-[#1F6C9F] underline-offset-2 hover:underline"
                            >
                              Workspace
                            </Link>
                          ) : null}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      <section className="rounded-[12px] border border-[#EAEAEA] bg-white p-6 md:p-8">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-mono text-[11px] tracking-[0.08em] text-[#787774]">
              02
            </p>
            <h2 className="mt-1 text-sm font-semibold tracking-tight">
              Book drafts (optional)
            </h2>
            <p className="mt-1 text-sm text-[#787774]">
              Drafts are created in Skill workspace. Publish book-wide here if useful.
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
              <Button type="button" size="sm" variant="ghost" onClick={selectAllDrafts}>
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
            No drafts for this book. Open a skill Workspace to generate.
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
                    {q.toeic_part ? ` · ${q.toeic_part}` : ""}
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
