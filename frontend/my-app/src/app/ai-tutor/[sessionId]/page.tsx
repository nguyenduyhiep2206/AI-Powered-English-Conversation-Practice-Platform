"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Loader2, MessageSquare } from "lucide-react";
import AppHeader from "@/components/AppHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  endTutorSession,
  getTutorSession,
  streamTutorMessage,
  type TutorDebugInfo,
  type TutorMessage,
  type TutorSessionDetail,
  type TutorSummary,
  type TutorTurnMeta,
} from "@/lib/tutor";

function isTurnMeta(
  meta: TutorMessage["meta"],
): meta is TutorTurnMeta {
  return meta != null && typeof meta === "object" && "goal_progress" in meta;
}

function CorrectionChip({ meta }: { meta: TutorTurnMeta }) {
  const correction = meta.correction;
  if (!correction) return null;

  return (
    <div className="mt-2 rounded-lg border border-amber-200/80 bg-amber-50/80 px-3 py-2 text-xs text-amber-950">
      <p>
        <span className="text-muted-foreground">Try: </span>
        <span className="font-medium">{correction.better}</span>
      </p>
      {correction.why ? (
        <p className="mt-1 text-muted-foreground">{correction.why}</p>
      ) : null}
    </div>
  );
}

function MessageBubble({ message }: { message: TutorMessage }) {
  const isUser = message.role === "user";
  const meta = isTurnMeta(message.meta) ? message.meta : null;

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
        {!isUser && meta ? (
          <>
            {meta.hint ? (
              <p className="mt-2 text-xs text-muted-foreground">{meta.hint}</p>
            ) : null}
            <CorrectionChip meta={meta} />
          </>
        ) : null}
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
  const [debugEnabled, setDebugEnabled] = useState(false);
  const [debugInfo, setDebugInfo] = useState<TutorDebugInfo | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

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

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText, streamingMeta]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const isActive = session?.status === "active";
  const isStreaming = sending && Boolean(streamingText || streamingMeta);

  async function handleSend(event: React.FormEvent) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || !session || !isActive || sending) return;

    setSending(true);
    setError(null);
    setDraft("");
    setStreamingText("");
    setStreamingMeta(null);
    setDebugInfo(null);

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
          onDebug: (info) => {
            setDebugInfo(info);
          },
          onError: (err) => {
            setError(err.message);
          },
          onDone: () => {
            setStreamingText("");
          },
        },
        { signal: controller.signal, debug: debugEnabled },
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

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <AppHeader />

      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 py-6 sm:px-6">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <Button asChild type="button" variant="ghost" size="sm">
            <Link href="/ai-tutor">
              <ArrowLeft className="mr-1.5 h-4 w-4" />
              Topics
            </Link>
          </Button>
          {session ? (
            <Badge variant="outline" className="capitalize">
              {session.status}
            </Badge>
          ) : null}
          <label className="ml-auto inline-flex items-center gap-2 text-xs text-muted-foreground">
            <input
              type="checkbox"
              checked={debugEnabled}
              onChange={(event) => setDebugEnabled(event.target.checked)}
              className="h-3.5 w-3.5 rounded border-border"
            />
            Debug
          </label>
        </div>

        <div className="mb-4">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-primary" />
            <h1 className="text-xl font-semibold tracking-tight text-foreground">
              Practice speaking
            </h1>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Role-play in text — stay in character and respond naturally.
          </p>
        </div>

        {loading ? (
          <div className="flex flex-1 items-center justify-center gap-2 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            Loading session…
          </div>
        ) : error && !session ? (
          <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-6 text-sm text-destructive">
            {error}
          </div>
        ) : (
          <>
            <div className="flex min-h-[320px] flex-1 flex-col gap-4 overflow-y-auto rounded-xl border border-border/60 bg-muted/10 p-4">
              {messages.length === 0 && !isStreaming ? (
                <p className="text-center text-sm text-muted-foreground">
                  Send your first message to start the conversation.
                </p>
              ) : null}

              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}

              {streamingText || streamingMeta ? (
                <div className="flex justify-start">
                  <div className="max-w-[85%] rounded-2xl border border-border/60 bg-card px-4 py-3 text-sm leading-relaxed">
                    {streamingText ? (
                      <p className="whitespace-pre-wrap">{streamingText}</p>
                    ) : (
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    )}
                    {streamingMeta ? <CorrectionChip meta={streamingMeta} /> : null}
                  </div>
                </div>
              ) : null}

              <div ref={bottomRef} />
            </div>

            {error ? (
              <p className="mt-3 text-sm text-destructive" role="alert">
                {error}
              </p>
            ) : null}

            {debugEnabled && debugInfo ? (
              <div className="mt-3 rounded-lg border border-border/70 bg-muted/20 px-3 py-3 font-mono text-xs text-muted-foreground">
                <p>
                  route={debugInfo.route} · cache=
                  {debugInfo.cache_hit ? "hit" : "miss"} · memory≈
                  {debugInfo.memory_tokens ?? "?"} · retrieved≈
                  {debugInfo.retrieved_tokens ?? "?"} · chunks=
                  {debugInfo.chunk_count ?? 0}
                </p>
                {debugInfo.chunks && debugInfo.chunks.length > 0 ? (
                  <ul className="mt-2 space-y-1">
                    {debugInfo.chunks.map((chunk, index) => (
                      <li key={`${chunk.unit_id ?? index}-${index}`}>
                        [{index + 1}] {chunk.unit_title ?? "unit"} (
                        {chunk.score ?? "?"}): {chunk.preview}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : null}

            {isActive ? (
              <form onSubmit={handleSend} className="mt-4 space-y-3">
                <textarea
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  placeholder="Type your reply…"
                  rows={3}
                  disabled={sending}
                  className="w-full resize-none rounded-xl border border-border bg-background px-4 py-3 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:opacity-60"
                />
                <div className="flex flex-wrap gap-2">
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
                  <Button
                    type="button"
                    variant="outline"
                    disabled={ending}
                    onClick={() => void handleEnd()}
                  >
                    {ending ? "Ending…" : "End session"}
                  </Button>
                </div>
              </form>
            ) : (
              <div className="mt-4 rounded-xl border border-border/60 bg-card/40 px-4 py-5 text-center">
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
          </>
        )}
      </main>

      {summary ? (
        <SummaryModal
          summary={summary}
          onClose={() => router.push("/ai-tutor")}
        />
      ) : null}
    </div>
  );
}
