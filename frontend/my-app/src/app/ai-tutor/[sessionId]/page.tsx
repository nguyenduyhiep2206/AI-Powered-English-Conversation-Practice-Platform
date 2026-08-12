"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Lightbulb, Loader2 } from "lucide-react";
import AppHeader from "@/components/AppHeader";
import TutorFeedbackRail from "@/components/tutor/TutorFeedbackRail";
import TutorScenarioRail from "@/components/tutor/TutorScenarioRail";
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
          "max-w-[85%] px-4 py-3 text-[0.9375rem] leading-relaxed",
          isUser
            ? "rounded-[1.25rem_1.25rem_0.35rem_1.25rem] bg-[#E85D04] text-white shadow-[0_8px_20px_rgba(232,93,4,0.22)]"
            : "rounded-[1.25rem_1.25rem_1.25rem_0.35rem] bg-white text-[#1F1B15] shadow-[0_6px_18px_rgba(31,27,21,0.06)] ring-1 ring-[#E9D7C9]",
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
        className="absolute inset-0 bg-[#1F1B15]/40 backdrop-blur-[2px]"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="tutor-summary-title"
        className="relative z-10 max-h-[85vh] w-full max-w-md overflow-y-auto rounded-[1.75rem] bg-white p-6 shadow-[0_24px_60px_rgba(31,27,21,0.18)] ring-1 ring-[#1F1B15]/06 sm:p-7"
      >
        <h2
          id="tutor-summary-title"
          className="text-[1.75rem] font-semibold tracking-tight text-[#1F1B15]"
        >
          Session summary
        </h2>

        {summary.went_well.length > 0 ? (
          <section className="mt-5">
            <h3 className="text-[0.9375rem] font-semibold text-[#2F9E44]">
              Went well
            </h3>
            <ul className="mt-2 space-y-1.5 text-[0.9375rem] text-[#1F1B15]">
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
            <h3 className="text-[0.9375rem] font-semibold text-[#9A3412]">
              Fix next
            </h3>
            <ul className="mt-2 space-y-1.5 text-[0.9375rem] text-[#1F1B15]">
              {summary.fix_next.map((item) => (
                <li key={item} className="leading-relaxed">
                  {item}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {hasSignals ? (
          <p className="mt-5 text-[0.875rem] text-[#6B6258]">
            Some target skills may need more practice — review weak skills on
            your dashboard.
          </p>
        ) : null}

        <div className="mt-6 flex flex-col gap-2 sm:flex-row">
          {hasSignals ? (
            <Link
              href="/dashboard"
              className="inline-flex h-11 flex-1 items-center justify-center rounded-2xl bg-[#FFFAF5] text-[0.875rem] font-semibold text-[#9A3412] ring-1 ring-[#E9D7C9] transition-colors hover:bg-[#FFE8D6] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]"
            >
              Review weak skills
            </Link>
          ) : null}
          <button
            type="button"
            className="inline-flex h-11 flex-1 items-center justify-center rounded-2xl bg-[#E85D04] text-[0.875rem] font-semibold text-white shadow-[0_10px_24px_rgba(232,93,4,0.28)] transition-[transform,background-color] hover:bg-[#D04F00] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04] active:scale-[0.98]"
            onClick={onClose}
          >
            Back to topics
          </button>
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
    <div className="relative flex min-h-screen flex-col overflow-x-hidden bg-[#FFF5EB] text-[#1F1B15]">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 50% 35% at 8% 0%, rgba(232, 93, 4, 0.12), transparent 55%), radial-gradient(ellipse 40% 30% at 92% 8%, rgba(13, 148, 136, 0.1), transparent 50%)",
        }}
      />

      <div className="relative flex min-h-screen flex-col">
        <AppHeader />

        <div className="flex min-h-0 flex-1 flex-col">
          <header className="flex flex-wrap items-center gap-3 border-b border-[#E9D7C9]/80 bg-[#FFFAF5]/80 px-4 py-3 backdrop-blur-md sm:px-6">
            <Link
              href="/ai-tutor"
              className="inline-flex min-h-11 items-center gap-1.5 rounded-2xl px-3 text-[0.875rem] font-medium text-[#9A3412] transition-colors hover:bg-white hover:text-[#E85D04] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden />
              Topics
            </Link>

            {scenario ? (
              <span className="rounded-2xl bg-[#FFE8D6] px-2.5 py-1 text-[0.75rem] font-semibold text-[#9A3412]">
                {scenario.level}
              </span>
            ) : null}

            <div className="min-w-0 flex-1">
              <h1 className="truncate text-[1.25rem] font-semibold tracking-tight text-[#1F1B15]">
                {title}
              </h1>
              <p className="text-[0.8125rem] text-[#8A8178]">
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
              <button
                type="button"
                disabled={ending || loading}
                aria-busy={ending}
                onClick={() => void handleEnd()}
                className="inline-flex min-h-11 items-center rounded-2xl bg-white px-4 text-[0.875rem] font-semibold text-[#BE123C] ring-1 ring-[#E9D7C9] transition-colors hover:bg-[#FFE4E6] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#BE123C] disabled:opacity-60"
              >
                {ending ? "Ending…" : "End session"}
              </button>
            ) : null}
          </header>

          {loading ? (
            <div className="flex flex-1 items-center justify-center gap-2 text-[0.875rem] text-[#8A8178]">
              <Loader2 className="h-5 w-5 animate-spin text-[#E85D04]" aria-hidden />
              Loading session…
            </div>
          ) : error && !session ? (
            <div className="mx-auto w-full max-w-lg px-4 py-8">
              <div
                className="rounded-2xl bg-[#FFE4E6] px-4 py-6 text-[0.875rem] text-[#BE123C] ring-1 ring-[#BE123C]/25"
                role="alert"
              >
                {error}
              </div>
            </div>
          ) : (
            <div className="relative flex min-h-0 flex-1">
              {scenario ? (
                <TutorScenarioRail
                  scenario={scenario}
                  status={session?.status}
                />
              ) : null}

              <section className="flex min-w-0 flex-1 flex-col">
                <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 py-4 sm:px-6">
                  {messages.length === 0 && !isStreaming ? (
                    <p className="py-8 text-center text-[0.875rem] text-[#8A8178]">
                      Send your first message to start the conversation.
                    </p>
                  ) : null}

                  {messages.map((message) => (
                    <MessageBubble key={message.id} message={message} />
                  ))}

                  {streamingText || (sending && !streamingText) ? (
                    <div className="flex justify-start">
                      <div className="max-w-[85%] rounded-[1.25rem_1.25rem_1.25rem_0.35rem] bg-white px-4 py-3 text-[0.9375rem] leading-relaxed shadow-[0_6px_18px_rgba(31,27,21,0.06)] ring-1 ring-[#E9D7C9]">
                        {streamingText ? (
                          <p className="whitespace-pre-wrap">{streamingText}</p>
                        ) : (
                          <Loader2
                            className="h-4 w-4 animate-spin text-[#8A8178]"
                            aria-hidden
                          />
                        )}
                      </div>
                    </div>
                  ) : null}

                  <div ref={bottomRef} />
                </div>

                {error ? (
                  <p
                    className="border-t border-[#E9D7C9] bg-[#FFE4E6] px-4 py-2.5 text-[0.875rem] text-[#BE123C] sm:px-6"
                    role="alert"
                  >
                    {error}
                  </p>
                ) : null}

                {revealedHint ? (
                  <div className="border-t border-[#0D9488]/20 bg-[#CCFBF1]/50 px-4 py-2.5 text-[0.875rem] text-[#115E59] sm:px-6">
                    <span className="font-semibold">Hint: </span>
                    {revealedHint}
                  </div>
                ) : null}

                {isActive ? (
                  <form
                    onSubmit={handleSend}
                    className="border-t border-[#E9D7C9] bg-[#FFFAF5]/90 px-4 py-3 backdrop-blur-sm sm:px-6"
                  >
                    <textarea
                      value={draft}
                      onChange={(event) => setDraft(event.target.value)}
                      placeholder="Type your reply…"
                      rows={3}
                      disabled={sending}
                      className="w-full resize-none rounded-2xl border border-[#E9D7C9] bg-white px-4 py-3 text-[0.9375rem] leading-relaxed text-[#1F1B15] placeholder:text-[#A89F94] focus-visible:border-[#E85D04] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]/25 disabled:opacity-60"
                    />
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        type="submit"
                        disabled={sending || !draft.trim()}
                        aria-busy={sending}
                        className="inline-flex h-11 items-center rounded-2xl bg-[#E85D04] px-5 text-[0.875rem] font-semibold text-white shadow-[0_10px_24px_rgba(232,93,4,0.28)] transition-[transform,background-color] hover:bg-[#D04F00] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04] active:scale-[0.98] disabled:opacity-60"
                      >
                        {sending ? (
                          <>
                            <Loader2
                              className="mr-2 h-4 w-4 animate-spin"
                              aria-hidden
                            />
                            Sending…
                          </>
                        ) : (
                          "Send"
                        )}
                      </button>
                      <span
                        className="inline-flex"
                        title={latestHint ? undefined : "No hint yet"}
                      >
                        <button
                          type="button"
                          disabled={!latestHint || sending}
                          onClick={handleHint}
                          className="inline-flex h-11 items-center rounded-2xl bg-white px-4 text-[0.875rem] font-semibold text-[#115E59] ring-1 ring-[#E9D7C9] transition-colors hover:bg-[#CCFBF1] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0D9488] disabled:opacity-50"
                        >
                          <Lightbulb className="mr-1.5 h-4 w-4" aria-hidden />
                          Hint
                        </button>
                      </span>
                    </div>
                  </form>
                ) : (
                  <div className="border-t border-[#E9D7C9] px-4 py-5 text-center sm:px-6">
                    <p className="text-[0.875rem] text-[#8A8178]">
                      This session is no longer active.
                    </p>
                    <button
                      type="button"
                      className="mt-3 inline-flex h-11 items-center rounded-2xl bg-[#E85D04] px-5 text-[0.875rem] font-semibold text-white shadow-[0_10px_24px_rgba(232,93,4,0.28)] transition-[transform,background-color] hover:bg-[#D04F00] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04] active:scale-[0.98]"
                      onClick={() => router.push("/ai-tutor")}
                    >
                      Back to topics
                    </button>
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
