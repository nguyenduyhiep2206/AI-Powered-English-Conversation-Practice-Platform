"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, MessageSquare, Sparkles } from "lucide-react";
import AppHeader from "@/components/AppHeader";
import {
  listTutorScenarios,
  startTutorSession,
  type TutorScenario,
} from "@/lib/tutor";

function truncate(text: string, max = 120): string {
  const t = text.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

export default function TutorCatalogPage() {
  const router = useRouter();
  const [scenarios, setScenarios] = useState<TutorScenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [startingId, setStartingId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await listTutorScenarios();
        if (!cancelled) setScenarios(data);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load topics",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleStart(scenario: TutorScenario) {
    if (startingId != null) return;
    setStartingId(scenario.id);
    setError(null);
    try {
      const session = await startTutorSession({ scenarioId: scenario.id });
      router.push(`/ai-tutor/${session.id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not start tutor session",
      );
      setStartingId(null);
    }
  }

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[#FFF5EB] text-[#1F1B15]">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 55% 40% at 10% 8%, rgba(232, 93, 4, 0.14), transparent 58%), radial-gradient(ellipse 45% 35% at 90% 20%, rgba(13, 148, 136, 0.12), transparent 55%)",
        }}
      />

      <div className="relative flex min-h-screen flex-col">
        <AppHeader />

        <main className="mx-auto w-full max-w-4xl flex-1 px-5 py-8 sm:px-8 md:px-10 md:py-10">
          <div className="ef-fade-up mb-8" style={{ ["--ef-index" as string]: 0 }}>
            <div className="flex items-center gap-3">
              <span className="grid h-11 w-11 place-items-center rounded-2xl bg-[#E85D04] text-white shadow-[0_8px_24px_rgba(232,93,4,0.28)]">
                <MessageSquare className="h-5 w-5" aria-hidden />
              </span>
              <div>
                <h1 className="text-[1.75rem] font-semibold tracking-tight text-[#1F1B15] md:text-[2rem]">
                  AI Tutor
                </h1>
                <p className="mt-1 max-w-xl text-[0.875rem] leading-relaxed text-[#8A8178]">
                  Pick a topic and practice a short role-play. Stay in character
                  — the tutor will gently correct and keep you on goal.
                </p>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center gap-2 text-[0.875rem] text-[#8A8178]">
              <Loader2 className="h-5 w-5 animate-spin text-[#E85D04]" aria-hidden />
              Loading topics…
            </div>
          ) : null}

          {error ? (
            <div
              className="mb-5 rounded-2xl bg-[#FFE4E6] px-4 py-3 text-[0.875rem] text-[#BE123C] ring-1 ring-[#BE123C]/25"
              role="alert"
            >
              {error}
            </div>
          ) : null}

          {!loading && scenarios.length === 0 ? (
            <p className="text-[0.875rem] text-[#8A8178]">
              No scenarios available for your level yet.
            </p>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            {scenarios.map((scenario, index) => (
              <article
                key={scenario.id}
                className="ef-fade-up flex flex-col rounded-[1.75rem] bg-white p-5 shadow-[0_18px_50px_rgba(31,27,21,0.06)] ring-1 ring-[#1F1B15]/06 sm:p-6"
                style={{ ["--ef-index" as string]: Math.min(index + 1, 6) }}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-1 rounded-2xl bg-[#CCFBF1] px-2.5 py-1 text-[0.75rem] font-semibold text-[#115E59]">
                    <Sparkles className="h-3 w-3" aria-hidden />
                    Role-play
                  </span>
                  <span className="rounded-2xl bg-[#FFE8D6] px-2.5 py-1 text-[0.75rem] font-semibold text-[#9A3412]">
                    {scenario.level}
                  </span>
                </div>

                <h2 className="mt-4 text-[1.25rem] font-semibold tracking-tight text-[#1F1B15]">
                  {scenario.title}
                </h2>
                <p className="mt-2 flex-1 text-[0.9375rem] leading-relaxed text-[#6B6258]">
                  {truncate(scenario.description || scenario.goal_prompt)}
                </p>
                <p className="mt-3 text-[0.8125rem] text-[#8A8178]">
                  You: {scenario.user_role} · Tutor: {scenario.ai_role}
                </p>

                <button
                  type="button"
                  disabled={startingId != null}
                  aria-busy={startingId === scenario.id}
                  onClick={() => void handleStart(scenario)}
                  className="mt-5 inline-flex h-11 w-full items-center justify-center rounded-2xl bg-[#E85D04] text-[0.9375rem] font-semibold text-white shadow-[0_10px_24px_rgba(232,93,4,0.28)] transition-[transform,background-color] duration-200 hover:bg-[#D04F00] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04] active:scale-[0.98] disabled:opacity-60 sm:w-auto sm:px-6"
                >
                  {startingId === scenario.id ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
                      Starting…
                    </>
                  ) : (
                    "Start"
                  )}
                </button>
              </article>
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}
