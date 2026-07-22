"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Loader2, Route as RouteIcon, Sparkles } from "lucide-react";
import { RoadmapPath } from "@/components/roadmap/RoadmapPath";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import LogoutButton from "@/components/ui/LogoutButton";
import { fetchOnboardingStatus } from "@/lib/onboarding-status";
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
  const [loading, setLoading] = useState(true);
  const [assembling, setAssembling] = useState(false);
  const [completingStepId, setCompletingStepId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [path, status] = await Promise.all([
      fetchRoadmap(),
      fetchOnboardingStatus(),
    ]);
    setWeeks(path);
    setLevel(status.current_level ?? path[0]?.level ?? null);
    setPlacementScore(status.placement_score ?? null);
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
      const path = await assembleRoadmap({ max_steps: 10 });
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
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-white">
              <Sparkles className="h-4 w-4 text-black" />
            </div>
            <span className="font-semibold tracking-tight text-foreground">
              EnglishFlow
            </span>
          </Link>
          <div className="flex items-center gap-2">
            <Link
              href="/dashboard/level-challenge"
              className="hidden text-xs text-muted-foreground transition-colors hover:text-foreground sm:inline"
            >
              Level feels too easy?
            </Link>
            <LogoutButton />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-10">
        <div className="ef-fade-up mb-10 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
              Your path
            </p>
            <h1 className="mt-1.5 text-3xl font-semibold tracking-tight text-foreground">
              Weekly roadmap
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              One clear next step — unlock weeks as you build mastery.
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
              Build a personalized 8–12 week path from skills in your zone of
              proximal development.
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
            <div className="mb-4 flex justify-end sm:hidden">
              <Link
                href="/dashboard/level-challenge"
                className="text-xs text-muted-foreground underline-offset-4 hover:underline"
              >
                Level feels too easy?
              </Link>
            </div>
            <RoadmapPath
              weeks={weeks}
              completingStepId={completingStepId}
              actionError={actionError}
              onComplete={handleComplete}
            />
          </>
        )}
      </main>
    </div>
  );
}
