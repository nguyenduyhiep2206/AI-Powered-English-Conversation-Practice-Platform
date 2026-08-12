"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2, Loader2, PartyPopper, X } from "lucide-react";
import LogoutButton from "@/components/ui/LogoutButton";
import { cn } from "@/lib/utils";
import type { PlacementSession } from "@/lib/placement";

const CEFR_BANDS = ["A1", "A2", "B1", "B2", "C1"] as const;

const CONFETTI_TONES = [
  "bg-[#E85D04]",
  "bg-[#0D9488]",
  "bg-[#2F9E44]",
  "bg-[#FFB38A]",
  "bg-[#9A3412]",
] as const;

type PlacementCompleteProps = {
  session: PlacementSession;
  error: string | null;
  assembling: boolean;
  onAssemble: () => void;
};

function nextBandHint(level: string | null | undefined): string {
  if (level === "A1") return ", on the way to A2";
  if (level === "A2") return ", on the way to B1";
  if (level === "B1") return ", on the way to B2";
  if (level === "B2") return ", on the way to C1";
  return "";
}

function bandIndex(level: string | null | undefined): number {
  const i = CEFR_BANDS.indexOf((level ?? "A1") as (typeof CEFR_BANDS)[number]);
  return i >= 0 ? i : 0;
}

export default function PlacementComplete({
  session,
  error,
  assembling,
  onAssemble,
}: PlacementCompleteProps) {
  const [toastOpen, setToastOpen] = useState(true);
  const level = session.current_level ?? "A1";
  const levelIdx = bandIndex(level);
  const readingTotal = session.form?.reading_items?.length ?? 0;
  const readingCorrect = session.reading_raw ?? 0;
  const readingPct =
    readingTotal > 0
      ? Math.round((readingCorrect / readingTotal) * 100)
      : null;

  useEffect(() => {
    const id = window.setTimeout(() => setToastOpen(false), 6500);
    return () => window.clearTimeout(id);
  }, []);

  return (
    <main className="relative min-h-screen overflow-x-hidden bg-[#FFF5EB] px-5 py-10 text-[#1F1B15] sm:px-8">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 55% 40% at 12% 8%, rgba(47, 158, 68, 0.14), transparent 58%), radial-gradient(ellipse 45% 35% at 88% 18%, rgba(232, 93, 4, 0.12), transparent 55%)",
        }}
      />

      <div
        aria-hidden
        className="placement-confetti pointer-events-none absolute inset-x-0 top-0 h-72 overflow-hidden"
      >
        {Array.from({ length: 18 }).map((_, i) => (
          <span
            key={i}
            className={cn(
              "placement-confetti-piece absolute top-0 size-2 rounded-sm opacity-0",
              CONFETTI_TONES[i % CONFETTI_TONES.length],
            )}
            style={{
              left: `${6 + ((i * 5.2) % 88)}%`,
              animationDelay: `${i * 45}ms`,
              ["--confetti-x" as string]: `${((i % 5) - 2) * 18}px`,
              ["--confetti-rot" as string]: `${(i % 7) * 40 - 80}deg`,
            }}
          />
        ))}
      </div>

      <div className="relative mx-auto max-w-2xl space-y-5">
        <div className="flex justify-end">
          <LogoutButton className="min-h-11 rounded-[1rem] px-4 text-[0.875rem] font-semibold text-[#BE123C] hover:bg-[#FFE4E6] hover:text-[#BE123C]" />
        </div>

        {toastOpen ? (
          <div
            role="status"
            aria-live="polite"
            className="placement-toast flex items-start gap-3 rounded-[1rem] bg-[#2F9E44] px-4 py-3.5 text-white shadow-[0_16px_40px_rgba(47,158,68,0.28)]"
          >
            <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-[1rem] bg-white/20">
              <PartyPopper className="h-4 w-4" aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[0.9375rem] font-semibold">
                Nice work — placement finished
              </p>
              <p className="mt-0.5 text-[0.8125rem] text-white/90">
                Your starting level is ready. Review the summary, then build
                your path.
              </p>
            </div>
            <button
              type="button"
              aria-label="Dismiss congratulations"
              onClick={() => setToastOpen(false)}
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-[1rem] text-white/90 transition-colors hover:bg-white/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          </div>
        ) : null}

        <section className="ef-fade-up relative overflow-hidden rounded-[1rem] bg-white p-6 shadow-[0_18px_50px_rgba(31,27,21,0.08)] ring-1 ring-[#1F1B15]/06 sm:p-8">
          <span
            aria-hidden
            className="pointer-events-none absolute -right-1 top-6 select-none text-[2.75rem] font-semibold leading-none text-[#FFF5EB] sm:top-4 sm:scale-[2.2] sm:origin-top-right"
          >
            {level}
          </span>

          <div className="relative">
            <p className="text-[0.8125rem] font-medium text-[#8A8178]">
              Placement result
            </p>

            <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-start">
              <div className="placement-level-pop grid h-16 w-16 shrink-0 place-items-center rounded-[1rem] bg-[#FFE8D6] text-[1.25rem] font-semibold text-[#E85D04] shadow-[0_10px_24px_rgba(232,93,4,0.22)] ring-1 ring-[#E85D04]/20">
                {level}
              </div>
              <div className="min-w-0">
                <h1 className="text-[1.75rem] font-semibold tracking-tight text-[#1F1B15] md:text-[2rem]">
                  Estimated starting level: {level}
                </h1>
                <p className="mt-2 text-[0.9375rem] leading-relaxed text-[#6B6258]">
                  Your answers place you around{" "}
                  <span className="font-semibold text-[#1F1B15]">{level}</span>
                  {session.placement_score != null
                    ? ` (sub-level ${session.placement_score}/10)`
                    : ""}
                  . {level} is your safest CEFR base for the path right now
                  {nextBandHint(level)}.
                </p>
              </div>
            </div>

            <div className="mt-7">
              <div className="flex justify-between gap-1">
                {CEFR_BANDS.map((band, i) => (
                  <span
                    key={band}
                    className={cn(
                      "flex-1 text-center text-[0.75rem] font-semibold",
                      i <= levelIdx ? "text-[#9A3412]" : "text-[#A89F94]",
                    )}
                  >
                    {band}
                  </span>
                ))}
              </div>
              <div
                className="mt-2 flex h-2.5 overflow-hidden rounded-full bg-[#E9D7C9]"
                role="img"
                aria-label={`CEFR progress through ${level}`}
              >
                {CEFR_BANDS.map((band, i) => (
                  <span
                    key={band}
                    className={cn(
                      "h-full flex-1 border-r border-[#FFF5EB]/80 last:border-r-0",
                      i <= levelIdx ? "bg-[#E85D04]" : "bg-transparent",
                    )}
                  />
                ))}
              </div>
            </div>
          </div>
        </section>

        <div
          className="ef-fade-up grid gap-4 sm:grid-cols-2"
          style={{ ["--ef-index" as string]: 1 }}
        >
          <div className="rounded-[1rem] bg-white p-5 shadow-[0_12px_36px_rgba(31,27,21,0.06)] ring-1 ring-[#1F1B15]/06 sm:p-6">
            <p className="text-[0.8125rem] font-medium text-[#8A8178]">
              Reading
            </p>
            <p className="mt-2 text-[1.75rem] font-semibold tracking-tight text-[#115E59]">
              {session.reading_scale ?? "—"}
            </p>
            <p className="mt-1 text-[0.875rem] text-[#6B6258]">
              Scale score
              {readingPct != null
                ? ` · ${readingCorrect}/${readingTotal} correct (${readingPct}%)`
                : ""}
            </p>
          </div>
          <div className="rounded-[1rem] bg-white p-5 shadow-[0_12px_36px_rgba(31,27,21,0.06)] ring-1 ring-[#1F1B15]/06 sm:p-6">
            <p className="text-[0.8125rem] font-medium text-[#8A8178]">
              Writing
            </p>
            <p className="mt-2 text-[1.75rem] font-semibold tracking-tight text-[#9A3412]">
              {session.writing_scale ?? "—"}
            </p>
            <p className="mt-1 text-[0.875rem] text-[#6B6258]">
              Scale score
              {session.writing_raw != null
                ? ` · raw ${session.writing_raw}`
                : ""}
            </p>
          </div>
        </div>

        {session.writing_feedback && session.writing_feedback.length > 0 ? (
          <section
            className="ef-fade-up rounded-[1rem] bg-white p-5 shadow-[0_12px_36px_rgba(31,27,21,0.06)] ring-1 ring-[#1F1B15]/06 sm:p-6"
            style={{ ["--ef-index" as string]: 2 }}
          >
            <h2 className="text-[1.25rem] font-semibold tracking-tight text-[#1F1B15]">
              Writing feedback
            </h2>
            <ul className="mt-4 space-y-3">
              {session.writing_feedback.map((f, fi) => (
                <li
                  key={`${f.item_id}-${fi}`}
                  className="rounded-[1rem] bg-[#FFFAF5] px-4 py-3 ring-1 ring-[#E9D7C9]"
                >
                  <div className="flex items-center gap-2">
                    <CheckCircle2
                      className="h-4 w-4 shrink-0 text-[#2F9E44]"
                      aria-hidden
                    />
                    <p className="text-[0.875rem] font-semibold text-[#1F1B15]">
                      Task {f.item_id}
                      <span className="font-medium text-[#8A8178]">
                        {" "}
                        · score {f.score}
                      </span>
                    </p>
                  </div>
                  {f.feedback ? (
                    <p className="mt-1.5 text-[0.875rem] leading-relaxed text-[#6B6258]">
                      {f.feedback}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {error ? (
          <div
            className="rounded-[1rem] bg-[#FFE4E6] px-4 py-3 text-[0.875rem] text-[#BE123C] ring-1 ring-[#BE123C]/25"
            role="alert"
          >
            {error}
          </div>
        ) : null}

        <div
          className="ef-fade-up flex flex-wrap gap-3"
          style={{ ["--ef-index" as string]: 3 }}
        >
          <button
            type="button"
            onClick={onAssemble}
            disabled={assembling}
            aria-busy={assembling}
            className="inline-flex h-11 items-center justify-center rounded-[1rem] bg-[#E85D04] px-5 text-[0.875rem] font-semibold text-white shadow-[0_10px_24px_rgba(232,93,4,0.28)] transition-[transform,background-color] hover:bg-[#D04F00] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04] active:scale-[0.98] disabled:opacity-60"
          >
            {assembling ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
            ) : null}
            Build my band path
            {!assembling ? (
              <ArrowRight className="ml-1.5 h-4 w-4" aria-hidden />
            ) : null}
          </button>
          <Link
            href="/dashboard"
            className="inline-flex h-11 items-center justify-center rounded-[1rem] bg-white px-5 text-[0.875rem] font-semibold text-[#9A3412] ring-1 ring-[#E9D7C9] transition-colors hover:bg-[#FFFAF5] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]"
          >
            Dashboard
          </Link>
        </div>
      </div>
    </main>
  );
}
