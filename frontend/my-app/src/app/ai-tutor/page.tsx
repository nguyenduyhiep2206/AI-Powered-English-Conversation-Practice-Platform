"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, MessageSquare } from "lucide-react";
import AppHeader from "@/components/AppHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
    <div className="flex min-h-screen flex-col bg-background">
      <AppHeader />

      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-8 sm:px-6">
        <div className="mb-8">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-primary" />
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              AI Tutor
            </h1>
          </div>
          <p className="mt-2 max-w-xl text-sm text-muted-foreground">
            Pick a topic and practice a short role-play. Stay in character — the
            tutor will gently correct and keep you on goal.
          </p>
        </div>

        {loading ? (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            Loading topics…
          </div>
        ) : null}

        {error ? (
          <p className="mb-4 text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}

        {!loading && scenarios.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No scenarios available for your level yet.
          </p>
        ) : null}

        <div className="grid gap-4 sm:grid-cols-2">
          {scenarios.map((scenario) => (
            <article
              key={scenario.id}
              className="flex flex-col border-b border-border/70 pb-5 sm:border-0 sm:pb-0"
            >
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline" className="uppercase tracking-wide">
                  AI Tutor
                </Badge>
                <Badge variant="secondary">{scenario.level}</Badge>
              </div>
              <h2 className="mt-3 text-lg font-medium tracking-tight text-foreground">
                {scenario.title}
              </h2>
              <p className="mt-1.5 flex-1 text-sm leading-relaxed text-muted-foreground">
                {truncate(scenario.description || scenario.goal_prompt)}
              </p>
              <p className="mt-2 text-xs text-muted-foreground">
                You: {scenario.user_role} · Tutor: {scenario.ai_role}
              </p>
              <Button
                type="button"
                className="mt-4 w-full sm:w-auto"
                disabled={startingId != null}
                onClick={() => void handleStart(scenario)}
              >
                {startingId === scenario.id ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Starting…
                  </>
                ) : (
                  "Start"
                )}
              </Button>
            </article>
          ))}
        </div>
      </main>
    </div>
  );
}
