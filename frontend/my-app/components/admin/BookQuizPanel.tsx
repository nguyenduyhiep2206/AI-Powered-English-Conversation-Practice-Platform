"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  generateSkillQuiz,
  syncBookSkills,
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

  useEffect(() => {
    setSourcesByUnitId({});
    setStatusMessage(null);
    setGeneratingSkillId(null);
  }, [bookId]);

  const syncSummary = useMemo(() => {
    const sources = Object.values(sourcesByUnitId);
    if (sources.length === 0) return null;
    const excluded = sources.filter((s) => s.is_excluded).length;
    return { total: sources.length, excluded };
  }, [sourcesByUnitId]);

  async function handleSync() {
    setSyncing(true);
    onError(null);
    setStatusMessage(null);
    try {
      const result = await syncBookSkills(bookId);
      const next: Record<number, SkillSourceRow> = {};
      for (const source of result.sources) {
        const existing = next[source.unit_id];
        // Prefer primary non-excluded source when a unit maps to multiple rows.
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
        `Synced ${result.source_count} skill source(s); ${result.excluded} excluded.`,
      );
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
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to generate quiz");
    } finally {
      setGeneratingSkillId(null);
    }
  }

  return (
    <section className="ef-card rounded-xl border border-border bg-card/60 p-5">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <h2 className="text-sm font-semibold">Quiz skills</h2>
        {syncSummary && (
          <>
            <Badge variant="secondary">{syncSummary.total} sourced</Badge>
            {syncSummary.excluded > 0 && (
              <Badge variant="outline">{syncSummary.excluded} excluded</Badge>
            )}
          </>
        )}
        <Button
          type="button"
          size="sm"
          className="ml-auto"
          disabled={syncing || units.length === 0}
          onClick={handleSync}
        >
          {syncing ? <Loader2 className="h-4 w-4 animate-spin" /> : "Sync skills"}
        </Button>
      </div>

      {statusMessage && (
        <p className="mb-3 text-sm text-muted-foreground">{statusMessage}</p>
      )}

      {units.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No units available. Index the book before syncing skills.
        </p>
      ) : Object.keys(sourcesByUnitId).length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Sync skills from this book&apos;s units, then generate draft quizzes per unit.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead className="border-b border-border text-xs uppercase tracking-wide text-muted-foreground">
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
                    <tr key={unit.id} className="border-b border-border/70 last:border-0">
                      <td className="px-3 py-2 font-medium">{unit.title}</td>
                      <td className="px-3 py-2 text-muted-foreground">—</td>
                      <td className="px-3 py-2 text-muted-foreground">Not linked</td>
                      <td className="px-3 py-2" />
                    </tr>
                  );
                }

                const canGenerate = !source.is_excluded;
                return (
                  <tr key={unit.id} className="border-b border-border/70 last:border-0">
                    <td className="px-3 py-2 font-medium">{unit.title}</td>
                    <td className="px-3 py-2 text-muted-foreground">#{source.skill_id}</td>
                    <td className="px-3 py-2">
                      {source.is_excluded ? (
                        <Badge variant="outline">Excluded</Badge>
                      ) : source.is_primary ? (
                        <Badge variant="secondary">Primary</Badge>
                      ) : (
                        <Badge variant="outline">Linked</Badge>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right">
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
                            "Generate quiz"
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
  );
}
