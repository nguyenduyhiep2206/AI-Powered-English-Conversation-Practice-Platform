"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Loader2, Route as RouteIcon } from "lucide-react";
import AppHeader from "@/components/AppHeader";
import { RoadmapPath } from "@/components/roadmap/RoadmapPath";
import { WeakSkillsReview } from "@/components/roadmap/WeakSkillsReview";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { fetchOnboardingStatus } from "@/lib/onboarding-status";
import { fetchPlacementAccessStatus, type PlacementAccessStatus } from "@/lib/placement";
import {
  assembleRoadmap,
  completeRoadmapStep,
  fetchRoadmap,
  fetchWeakSkills,
  nextCefrBand,
  type RoadmapWeek,
  type WeakSkill,
} from "@/lib/roadmap";

export default function DashboardPage() {
  const [weeks, setWeeks] = useState<RoadmapWeek[]>([]);
  const [weakSkills, setWeakSkills] = useState<WeakSkill[]>([]);
  const [level, setLevel] = useState<string | null>(null);
  const [placementScore, setPlacementScore] = useState<number | null>(null);
  const [access, setAccess] = useState<PlacementAccessStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [assembling, setAssembling] = useState(false);
  const [completingStepId, setCompletingStepId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pathExhausted, setPathExhausted] = useState(false);

  const nextBand = nextCefrBand(level);
  const allWeeksCompleted = useMemo(
    () => weeks.length > 0 && weeks.every((w) => w.status === "completed"),
    [weeks],
  );
  const showBandExit = allWeeksCompleted || pathExhausted;

  const refresh = useCallback(async () => {
    const [path, status, accessStatus, weak] = await Promise.all([
      fetchRoadmap(),
      fetchOnboardingStatus(),
      fetchPlacementAccessStatus().catch(() => null),
      fetchWeakSkills(5).catch(() => [] as WeakSkill[]),
    ]);
    setWeeks(path);
    setLevel(status.current_level ?? path[0]?.level ?? null);
    setPlacementScore(status.placement_score ?? null);
    setAccess(accessStatus);
    setWeakSkills(weak);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await refresh();
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load dashboard");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  async function handleAssemble() {
    setAssembling(true);
    setError(null);
    setActionError(null);
    setPathExhausted(false);
    try {
      const path = await assembleRoadmap();
      setWeeks(path);
      if (path[0]?.level) setLevel(path[0].level);
      const weak = await fetchWeakSkills(5).catch(() => [] as WeakSkill[]);
      setWeakSkills(weak);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create path";
      const exhausted =
        /no weak skills|not enough|no .*skills left|no eligible/i.test(message);
      if (exhausted) {
        setPathExhausted(true);
        setError(null);
        const weak = await fetchWeakSkills(5).catch(() => [] as WeakSkill[]);
        setWeakSkills(weak);
      } else {
        setError(message);
      }
    } finally {
      setAssembling(false);
    }
  }

  async function handleComplete(week: RoadmapWeek) {
    setCompletingStepId(week.roadmap_step_id);
    setActionError(null);
    try {
      await completeRoadmapStep(week.roadmap_step_id);
      await refresh();
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : "Could not complete this week",
      );
    } finally {
      setCompletingStepId(null);
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <AppHeader
        extraActions={
          access?.has_in_progress ? (
            <Link
              href="/onboarding/placement"
              className="hidden text-xs text-muted-foreground transition-colors hover:text-foreground sm:inline"
            >
              Resume placement
            </Link>
          ) : null
        }
      />

      <main className="mx-auto max-w-3xl px-6 py-10">
        <div className="ef-fade-up mb-10 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
              Foundation path
            </p>
            <h1 className="mt-1.5 text-3xl font-semibold tracking-tight text-foreground">
              {level ? `${level} foundation` : "Your roadmap"}
            </h1>
            <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
              {level
                ? nextBand
                  ? `Theme units at ${level}. Build the foundation, then take a level challenge toward ${nextBand} — this is not an official CEFR certificate.`
                  : `Theme units at ${level}. Keep strengthening skills in your zone.`
                : "Theme units from covered catalog skills in your zone. The path updates as you progress."}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {level ? <Badge variant="outline">CEFR {level}</Badge> : null}
            {nextBand ? (
              <Badge variant="outline">Next {nextBand}</Badge>
            ) : null}
            {placementScore != null ? (
              <Badge variant="outline">Sub-level {placementScore}/10</Badge>
            ) : null}
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-2 py-24 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            Loading path…
          </div>
        ) : error ? (
          <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-6 text-sm text-destructive">
            {error}
          </div>
        ) : weeks.length === 0 && !showBandExit ? (
          <section className="ef-fade-up rounded-xl border border-border/60 bg-card/40 px-6 py-14 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg border border-border/60 bg-muted/30">
              <RouteIcon className="h-5 w-5 text-muted-foreground" />
            </div>
            <h2 className="mt-5 text-lg font-medium text-foreground">
              No path yet
            </h2>
            <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">
              {level
                ? `Build the next steps from covered ${level} catalog skills in your zone.`
                : "Build the next steps from covered catalog skills in your zone."}
            </p>
            <Button
              type="button"
              size="lg"
              className="mt-6"
              disabled={assembling}
              onClick={handleAssemble}
            >
              {assembling ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating path…
                </>
              ) : (
                "Create my path"
              )}
            </Button>
          </section>
        ) : (
          <>
            {weeks.length > 0 ? (
              <RoadmapPath
                weeks={weeks}
                completingStepId={completingStepId}
                actionError={actionError}
                onComplete={handleComplete}
              />
            ) : null}

            {showBandExit ? (
              <section className="ef-fade-up mt-10 rounded-xl border border-border/60 bg-muted/20 px-5 py-6">
                <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                  Band exit
                </p>
                <h2 className="mt-1 text-lg font-semibold tracking-tight text-foreground">
                  {level ? `${level} foundation checkpoint` : "Foundation checkpoint"}
                </h2>
                <p className="mt-2 max-w-lg text-sm leading-relaxed text-muted-foreground">
                  {nextBand
                    ? `No more eligible steps at this level. Review weak skills below, then take a level challenge when ready to move toward ${nextBand}. Completing this path is not an official CEFR certificate.`
                    : "No more eligible steps at this level. Review weak skills below to keep your foundation strong."}
                </p>
                {weeks.length === 0 ? (
                  <Button
                    type="button"
                    variant="outline"
                    className="mt-4"
                    disabled={assembling}
                    onClick={handleAssemble}
                  >
                    {assembling ? "Checking…" : "Try rebuild path"}
                  </Button>
                ) : null}
              </section>
            ) : null}

            <WeakSkillsReview skills={weakSkills} level={level} />
          </>
        )}
      </main>
    </div>
  );
}
