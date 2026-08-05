"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Lightbulb, Loader2 } from "lucide-react";
import AppHeader from "@/components/AppHeader";
import TutorFeedbackRail from "@/components/tutor/TutorFeedbackRail";
import TutorScenarioRail from "@/components/tutor/TutorScenarioRail";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  collectFeedbackItems,
  type TutorFeedbackItem,
} from "@/lib/tutor-feedback";
import {
  endTutorSession,
  getTutorSession,
  streamTutorMessage,
  type TutorMessage,
  type TutorSessionDetail,
  type TutorSummary,
  type TutorTurnMeta,
} from "@/lib/tutor";

function MessageBubble({ message }: { message: TutorMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-primary text-primary-foreground"
            : "border border-border/60 bg-card text-foreground",
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
}

type SummaryModalProps = {
  summary: TutorSummary;
  onClose: () => void;
};

function SummaryModal({ summary, onClose }: SummaryModalProps) {
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  const hasSignals = summary.soft_skill_signals.length > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Close summary"
        className="absolute inset-0 bg-[#111111]/30"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        className="relative z-10 max-h-[85vh] w-full max-w-md overflow-y-auto rounded-xl border border-border bg-background p-6 shadow-lg"
      >
        <h2 className="text-xl font-semibold tracking-tight text-foreground">
          Session summary
        </h2>

        {summary.went_well.length > 0 ? (
          <section className="mt-5">
            <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
              Went well
            </p>
            <ul className="mt-2 space-y-1.5 text-sm text-foreground">
              {summary.went_well.map((item) => (
                <li key={item} className="leading-relaxed">
                  {item}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {summary.fix_next.length > 0 ? (
          <section className="mt-5">
            <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
              Fix next
            </p>
            <ul className="mt-2 space-y-1.5 text-sm text-foreground">
              {summary.fix_next.map((item) => (
                <li key={item} className="leading-relaxed">
                  {item}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {hasSignals ? (
          <p className="mt-5 text-sm text-muted-foreground">
            Some target skills may need more practice — review weak skills on
            your dashboard.
          </p>
        ) : null}

        <div className="mt-6 flex flex-col gap-2 sm:flex-row">
          {hasSignals ? (
            <Button asChild type="button" variant="secondary" className="flex-1">
              <Link href="/dashboard">Review weak skills</Link>
            </Button>
          ) : null}
          <Button type="button" className="flex-1" onClick={onClose}>
            Back to topics
          </Button>
        </div>
      </div>
    </div>
  );
}

function feedbackFromStreamingMeta(
  meta: TutorTurnMeta | null,
): TutorFeedbackItem[] {
  if (!meta) return [];
  const items: TutorFeedbackItem[] = [];
  if (meta.correction) {
    items.push({
      id: "c-streaming",
      kind: "correction",
      original: meta.correction.original,
      corrected: meta.correction.better,
      note: meta.correction.why ?? "",
    });
  }
  if (meta.hint?.trim()) {
    items.push({
      id: "h-streaming",
      kind: "hint",
      note: meta.hint.trim(),
    });
  }
  return items;
}

export default function TutorSessionPage() {
  const router = useRouter();
  const params = useParams();
  const sessionId = Number(params.sessionId);

  const [session, setSession] = useState<TutorSessionDetail | null>(null);
  const [messages, setMessages] = useState<TutorMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [streamingText, setStreamingText] = useState("");
  const [streamingMeta, setStreamingMeta] = useState<TutorTurnMeta | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [ending, setEnding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<TutorSummary | null>(null);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [revealedHint, setRevealedHint] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const autoOpenedFeedback = useRef(false);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      if (!Number.isFinite(sessionId) || sessionId <= 0) {
        if (!cancelled) {
          setError("Invalid session");
          setLoading(false);
        }
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const data = await getTutorSession(sessionId);
        if (!cancelled) {
          setSession(data);
          setMessages(data.messages ?? []);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load session",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const feedbackItems = useMemo(() => {
    const fromMessages = collectFeedbackItems(messages);
    const fromStream = feedbackFromStreamingMeta(streamingMeta);
    if (fromStream.length === 0) return fromMessages;
    return [...fromMessages, ...fromStream];
  }, [messages, streamingMeta]);

  useEffect(() => {
    if (feedbackItems.length > 0 && !autoOpenedFeedback.current) {
      if (
        typeof window !== "undefined" &&
        window.matchMedia("(min-width: 1024px)").matches
      ) {
        autoOpenedFeedback.current = true;
        setFeedbackOpen(true);
      }
    }
  }, [feedbackItems.length]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const isActive = session?.status === "active";
  const isStreaming = sending && Boolean(streamingText || streamingMeta);
  const scenario = session?.scenario ?? null;
  const latestHint = useMemo(() => {
    for (let i = feedbackItems.length - 1; i >= 0; i -= 1) {
      const item = feedbackItems[i];
      if (item.kind === "hint" && item.note.trim()) return item.note;
    }
    return null;
  }, [feedbackItems]);

  async function handleSend(event: React.FormEvent) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || !session || !isActive || sending) return;

    setSending(true);
    setError(null);
    setDraft("");
    setStreamingText("");
    setStreamingMeta(null);
    setRevealedHint(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamTutorMessage(
        session.id,
        content,
        {
          onUserMessage: (msg) => {
            setMessages((prev) => [
              ...prev,
              {
                id: msg.id,
                role: "user",
                content: msg.content,
                meta: null,
                created_at: new Date().toISOString(),
              },
            ]);
          },
          onToken: (text) => {
            setStreamingText((prev) => prev + text);
          },
          onMeta: (meta) => {
            setStreamingMeta(meta);
          },
          onAssistantMessage: (msg) => {
            setMessages((prev) => [
              ...prev,
              {
                id: msg.id,
                role: "assistant",
                content: msg.content,
                meta: msg.meta,
                created_at: new Date().toISOString(),
              },
            ]);
            setStreamingText("");
            setStreamingMeta(null);
          },
          onError: (err) => {
            setError(err.message);
          },
          onDone: () => {
            setStreamingText("");
          },
        },
        { signal: controller.signal },
      );
    } catch (err) {
      if (!(err instanceof DOMException && err.name === "AbortError")) {
        setError(err instanceof Error ? err.message : "Failed to send message");
      }
    } finally {
      abortRef.current = null;
      setSending(false);
      setStreamingText("");
      setStreamingMeta(null);
    }
  }

  async function handleEnd() {
    if (!session || !isActive || ending) return;

    abortRef.current?.abort();
    setEnding(true);
    setError(null);
    try {
      const result = await endTutorSession(session.id);
      setSummary(result);
      setSession((prev) =>
        prev ? { ...prev, status: "completed" } : prev,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to end session");
    } finally {
      setEnding(false);
    }
  }

  function handleHint() {
    if (!latestHint) return;
    setRevealedHint(latestHint);
    setFeedbackOpen(true);
  }

  const title = scenario?.title ?? "AI Tutor";

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <AppHeader />

      <div className="flex min-h-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center gap-3 border-b border-border/60 px-4 py-3 sm:px-6">
          <Button asChild type="button" variant="ghost" size="sm">
            <Link href="/ai-tutor">
              <ArrowLeft className="mr-1.5 h-4 w-4" />
              Topics
            </Link>
          </Button>

          {scenario ? (
            <Badge variant="outline" className="uppercase">
              {scenario.level}
            </Badge>
          ) : null}

          <div className="min-w-0 flex-1">
            <h1 className="truncate text-base font-semibold tracking-tight text-foreground sm:text-lg">
              {title}
            </h1>
            <p className="text-xs text-muted-foreground">
              {session
                ? isActive
                  ? "Session in progress"
                  : "Session completed"
                : loading
                  ? "Loading…"
                  : "—"}
            </p>
          </div>

          {isActive ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={ending || loading}
              onClick={() => void handleEnd()}
            >
              {ending ? "Ending…" : "End session"}
            </Button>
          ) : null}
        </header>

        {loading ? (
          <div className="flex flex-1 items-center justify-center gap-2 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            Loading session…
          </div>
        ) : error && !session ? (
          <div className="mx-auto w-full max-w-lg px-4 py-8">
            <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-6 text-sm text-destructive">
              {error}
            </div>
          </div>
        ) : (
          <div className="relative flex min-h-0 flex-1">
            {scenario ? (
              <TutorScenarioRail scenario={scenario} status={session?.status} />
            ) : null}

            <section className="flex min-w-0 flex-1 flex-col">
              <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 py-4 sm:px-6">
                {messages.length === 0 && !isStreaming ? (
                  <p className="py-8 text-center text-sm text-muted-foreground">
                    Send your first message to start the conversation.
                  </p>
                ) : null}

                {messages.map((message) => (
                  <MessageBubble key={message.id} message={message} />
                ))}

                {streamingText || (sending && !streamingText) ? (
                  <div className="flex justify-start">
                    <div className="max-w-[85%] rounded-2xl border border-border/60 bg-card px-4 py-3 text-sm leading-relaxed">
                      {streamingText ? (
                        <p className="whitespace-pre-wrap">{streamingText}</p>
                      ) : (
                        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                      )}
                    </div>
                  </div>
                ) : null}

                <div ref={bottomRef} />
              </div>

              {error ? (
                <p
                  className="border-t border-border/40 px-4 py-2 text-sm text-destructive sm:px-6"
                  role="alert"
                >
                  {error}
                </p>
              ) : null}

              {revealedHint ? (
                <div className="border-t border-amber-200/60 bg-amber-50/60 px-4 py-2.5 text-sm text-amber-950 sm:px-6 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-100">
                  <span className="font-medium">Hint: </span>
                  {revealedHint}
                </div>
              ) : null}

              {isActive ? (
                <form
                  onSubmit={handleSend}
                  className="border-t border-border/60 px-4 py-3 sm:px-6"
                >
                  <textarea
                    value={draft}
                    onChange={(event) => setDraft(event.target.value)}
                    placeholder="Type your reply…"
                    rows={3}
                    disabled={sending}
                    className="w-full resize-none rounded-xl border border-border bg-background px-4 py-3 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:opacity-60"
                  />
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button type="submit" disabled={sending || !draft.trim()}>
                      {sending ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Sending…
                        </>
                      ) : (
                        "Send"
                      )}
                    </Button>
                    <span
                      className="inline-flex"
                      title={latestHint ? undefined : "No hint yet"}
                    >
                      <Button
                        type="button"
                        variant="outline"
                        disabled={!latestHint || sending}
                        onClick={handleHint}
                      >
                        <Lightbulb className="mr-1.5 h-4 w-4" />
                        Hint
                      </Button>
                    </span>
                  </div>
                </form>
              ) : (
                <div className="border-t border-border/60 px-4 py-5 text-center sm:px-6">
                  <p className="text-sm text-muted-foreground">
                    This session is no longer active.
                  </p>
                  <Button
                    type="button"
                    className="mt-3"
                    onClick={() => router.push("/ai-tutor")}
                  >
                    Back to topics
                  </Button>
                </div>
              )}
            </section>

            <TutorFeedbackRail
              items={feedbackItems}
              open={feedbackOpen}
              onOpenChange={setFeedbackOpen}
            />
          </div>
        )}
      </div>

      {summary ? (
        <SummaryModal
          summary={summary}
          onClose={() => router.push("/ai-tutor")}
        />
      ) : null}
    </div>
  );
}
