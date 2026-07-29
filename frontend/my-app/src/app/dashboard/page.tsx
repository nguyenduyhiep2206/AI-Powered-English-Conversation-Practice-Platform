"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Loader2, Route as RouteIcon } from "lucide-react";
import AppHeader from "@/components/AppHeader";
import { RoadmapPath } from "@/components/roadmap/RoadmapPath";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { fetchOnboardingStatus } from "@/lib/onboarding-status";
import { fetchPlacementAccessStatus, type PlacementAccessStatus } from "@/lib/placement";
import {
  assembleRoadmap,
  completeRoadmapStep,
  fetchRoadmap,
  type RoadmapWeek,
} from "@/lib/roadmap";

export default function DashboardPage() {
  const [weeks, setWeeks] = useState<RoadmapWeek[]>([]);
  const [level, setLevel] = useState<string | null>(null);
  const [placementScore, setPlacementScore] = useState<number | null>(null);
  const [access, setAccess] = useState<PlacementAccessStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [assembling, setAssembling] = useState(false);
  const [completingStepId, setCompletingStepId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [path, status, accessStatus] = await Promise.all([
      fetchRoadmap(),
      fetchOnboardingStatus(),
      fetchPlacementAccessStatus().catch(() => null),
    ]);
    setWeeks(path);
    setLevel(status.current_level ?? path[0]?.level ?? null);
    setPlacementScore(status.placement_score ?? null);
    setAccess(accessStatus);
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
    try {
      const path = await assembleRoadmap();
      setWeeks(path);
      if (path[0]?.level) setLevel(path[0].level);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create path");
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
              Your next steps
            </p>
            <h1 className="mt-1.5 text-3xl font-semibold tracking-tight text-foreground">
              Weekly roadmap
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              We keep a few steps ahead — the path updates when you complete a
              week.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {level ? <Badge variant="outline">CEFR {level}</Badge> : null}
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
        ) : weeks.length === 0 ? (
          <section className="ef-fade-up rounded-xl border border-border/60 bg-card/40 px-6 py-14 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg border border-border/60 bg-muted/30">
              <RouteIcon className="h-5 w-5 text-muted-foreground" />
            </div>
            <h2 className="mt-5 text-lg font-medium text-foreground">
              No path yet
            </h2>
            <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">
              Build your next 3 steps from skills in your zone.
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
          <RoadmapPath
            weeks={weeks}
            completingStepId={completingStepId}
            actionError={actionError}
            onComplete={handleComplete}
          />
        )}
      </main>
    </div>
  );
}
