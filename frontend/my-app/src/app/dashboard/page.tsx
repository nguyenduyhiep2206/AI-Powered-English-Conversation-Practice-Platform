"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Loader2, Route as RouteIcon } from "lucide-react";
import AppHeader from "@/components/AppHeader";
import { RoadmapPath } from "@/components/roadmap/RoadmapPath";
import { WeakSkillsReview } from "@/components/roadmap/WeakSkillsReview";
import { Button } from "@/components/ui/button";
import { fetchOnboardingStatus } from "@/lib/onboarding-status";
import {
  fetchPlacementAccessStatus,
  type PlacementAccessStatus,
} from "@/lib/placement";
import {
  assembleRoadmap,
  completeRoadmapStep,
  fetchRoadmap,
  fetchWeakSkills,
  nextCefrBand,
  type RoadmapWeek,
  type WeakSkill,
} from "@/lib/roadmap";
import { cn } from "@/lib/utils";

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
  const completedCount = useMemo(
    () => weeks.filter((w) => w.status === "completed").length,
    [weeks],
  );
  const activeWeek = useMemo(
    () => weeks.find((w) => w.status === "in_progress") ?? null,
    [weeks],
  );

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
          setError(
            err instanceof Error ? err.message : "Failed to load dashboard",
          );
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
      const message =
        err instanceof Error ? err.message : "Failed to create path";
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
    <div className="relative min-h-screen overflow-x-hidden bg-[#FFF8F4] text-[#2A2438]">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-[22rem]"
        style={{
          background:
            "radial-gradient(ellipse 70% 60% at 18% 0%, rgba(255, 138, 107, 0.26), transparent 55%), radial-gradient(ellipse 50% 45% at 92% 8%, rgba(140, 198, 232, 0.2), transparent 50%)",
        }}
      />

      <div className="relative">
        <AppHeader
          extraActions={
            access?.has_in_progress ? (
              <Link
                href="/onboarding/placement"
                className="hidden text-[0.75rem] font-medium text-[#7B6EF6] transition-colors hover:text-[#6758E8] sm:inline"
              >
                Resume placement
              </Link>
            ) : null
          }
        />

        <main className="mx-auto max-w-3xl px-5 py-8 sm:px-6 sm:py-10">
          <header className="mb-8">
            <h1 className="text-3xl font-semibold tracking-tight text-[#2A2438] sm:text-[2rem]">
              {level ? `${level} foundation` : "Your roadmap"}
            </h1>
            <p className="mt-2 max-w-prose text-[0.9375rem] leading-relaxed text-[#6B6478]">
              {activeWeek
                ? `Continue with “${activeWeek.skill_title || activeWeek.skill_slug}” — practice until mastery is ready, then complete the week.`
                : level
                  ? nextBand
                    ? `Theme units at ${level}. Finish this band, then challenge toward ${nextBand} when ready.`
                    : `Theme units at ${level}. Keep strengthening skills in your zone.`
                  : "Build a path from catalog skills in your zone. It updates as you progress."}
            </p>

            <div className="mt-4 flex flex-wrap items-center gap-2">
              {weeks.length > 0 ? (
                <span className="rounded-2xl bg-white px-3 py-1.5 text-[0.75rem] font-semibold text-[#2A2438] ring-1 ring-[#2A2438]/06">
                  {completedCount}/{weeks.length} steps done
                </span>
              ) : null}
              {level ? (
                <span className="rounded-2xl bg-white/80 px-3 py-1.5 text-[0.75rem] font-semibold text-[#5C5468] ring-1 ring-[#2A2438]/06">
                  CEFR {level}
                </span>
              ) : null}
              {nextBand ? (
                <span className="rounded-2xl bg-[#8CC6E8]/20 px-3 py-1.5 text-[0.75rem] font-semibold text-[#3D7FA0] ring-1 ring-[#8CC6E8]/35">
                  Next {nextBand}
                </span>
              ) : null}
              {placementScore != null ? (
                <span className="rounded-2xl bg-[#C4B0E8]/20 px-3 py-1.5 text-[0.75rem] font-semibold text-[#6B5B9A] ring-1 ring-[#C4B0E8]/40">
                  Sub-level {placementScore}/10
                </span>
              ) : null}
            </div>
          </header>

          {loading ? (
            <div
              className="flex flex-col items-center justify-center gap-3 py-24"
              aria-busy="true"
              aria-live="polite"
            >
              <Loader2 className="h-6 w-6 animate-spin text-[#FF8A6B]" />
              <p className="text-[0.875rem] text-[#8A8396]">Loading your path…</p>
            </div>
          ) : error ? (
            <div
              className="rounded-[1.75rem] bg-[#FFF0EE] px-5 py-6 text-[0.875rem] text-[#C24B3A] ring-1 ring-[#FF8A6B]/25"
              role="alert"
            >
              <p className="font-semibold">Couldn’t load your path</p>
              <p className="mt-1 leading-relaxed">{error}</p>
              <Button
                type="button"
                className="mt-4 h-10 rounded-2xl bg-[#FF8A6B] px-4 text-[0.875rem] font-semibold text-white hover:bg-[#F47A5A]"
                onClick={() => {
                  setLoading(true);
                  setError(null);
                  void refresh().finally(() => setLoading(false));
                }}
              >
                Try again
              </Button>
            </div>
          ) : weeks.length === 0 && !showBandExit ? (
            <section className="rounded-[1.75rem] bg-white px-6 py-14 text-center shadow-[0_18px_50px_rgba(42,36,56,0.06)] ring-1 ring-[#2A2438]/06">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[#FF8A6B]/15 text-[#FF8A6B]">
                <RouteIcon className="h-6 w-6" aria-hidden />
              </div>
              <h2 className="mt-5 text-xl font-semibold tracking-tight text-[#2A2438]">
                Create your first path
              </h2>
              <p className="mx-auto mt-2 max-w-sm text-[0.9375rem] leading-relaxed text-[#6B6478]">
                {level
                  ? `We’ll pick the next ${level} theme units from covered skills in your zone.`
                  : "We’ll pick theme units from covered catalog skills in your zone."}
              </p>
              <Button
                type="button"
                size="lg"
                className={cn(
                  "mt-7 h-11 rounded-2xl bg-[#FF8A6B] px-6 text-[0.9375rem] font-semibold text-white",
                  "shadow-[0_10px_24px_rgba(255,138,107,0.28)] hover:bg-[#F47A5A]",
                  "active:scale-[0.98]",
                )}
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
                <section className="mt-10 rounded-[1.75rem] bg-white px-6 py-7 shadow-[0_12px_36px_rgba(42,36,56,0.05)] ring-1 ring-[#2A2438]/06">
                  <h2 className="text-xl font-semibold tracking-tight text-[#2A2438]">
                    {level
                      ? `${level} foundation checkpoint`
                      : "Foundation checkpoint"}
                  </h2>
                  <p className="mt-2 max-w-lg text-[0.9375rem] leading-relaxed text-[#6B6478]">
                    {nextBand
                      ? `No more eligible steps at this level. Review weak skills below, then take a level challenge when ready for ${nextBand}. This path is not an official CEFR certificate.`
                      : "No more eligible steps at this level. Review weak skills below to keep building."}
                  </p>
                  {weeks.length === 0 ? (
                    <Button
                      type="button"
                      className="mt-5 h-10 rounded-2xl border border-[#EDE6E0] bg-[#FFFCF9] text-[#2A2438] hover:bg-[#FFF8F4]"
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
    </div>
  );
}
