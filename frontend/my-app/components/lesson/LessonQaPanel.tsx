"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, MessageCircle, Send, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  clearLessonQa,
  formatLessonQaCite,
  getLessonQa,
  streamLessonQaMessage,
  type LessonQaMessage,
  type LessonQaTurnMeta,
} from "@/lib/lesson-qa";

type DemoProps = {
  defaultOpen?: boolean;
  messages?: LessonQaMessage[];
  prompts?: string[];
};

type Props = {
  skillId: number;
  lessonTitle?: string;
  /** Visual/dev preview — skips API. */
  demo?: DemoProps;
};

function sourcesFromMeta(
  meta: LessonQaTurnMeta | Record<string, unknown> | null | undefined,
): { unit_title: string; score?: number }[] | null {
  if (!meta || typeof meta !== "object") return null;
  const raw = (meta as LessonQaTurnMeta).sources;
  if (!Array.isArray(raw) || raw.length === 0) return null;
  return raw.filter(
    (s): s is { unit_title: string; score?: number } =>
      Boolean(s && typeof s === "object" && typeof s.unit_title === "string"),
  );
}

function retrievalEmptyNote(
  meta: LessonQaTurnMeta | Record<string, unknown> | null | undefined,
): string | null {
  if (!meta || typeof meta !== "object") return null;
  const route = (meta as LessonQaTurnMeta).route;
  if (route === "retrieval_empty") {
    return "Chưa tìm thấy trong sách gắn skill này.";
  }
  return null;
}

function MessageBubble({ message }: { message: LessonQaMessage }) {
  const isUser = message.role === "user";
  const cite = !isUser
    ? formatLessonQaCite(sourcesFromMeta(message.meta))
    : null;
  const emptyNote = !isUser ? retrievalEmptyNote(message.meta) : null;

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[88%] px-3.5 py-2.5 text-[13px] leading-[1.55]",
          isUser
            ? "rounded-[12px_12px_4px_12px] bg-[#2F3437] text-white"
            : "rounded-[12px_12px_12px_4px] bg-[#F7F6F3] text-[#2F3437]",
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {cite ? (
          <p className="mt-2 text-[11px] leading-snug text-[#787774]">{cite}</p>
        ) : null}
        {emptyNote ? (
          <p className="mt-1.5 text-[11px] leading-snug text-[#9B9A97]">
            {emptyNote}
          </p>
        ) : null}
      </div>
    </div>
  );
}

export default function LessonQaPanel({ skillId, lessonTitle, demo }: Props) {
  const isDemo = Boolean(demo);
  const [open, setOpen] = useState(Boolean(demo?.defaultOpen));
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<LessonQaMessage[]>(
    demo?.messages ?? [],
  );
  const [prompts, setPrompts] = useState<string[]>(demo?.prompts ?? []);
  const [draft, setDraft] = useState("");
  const [streamingText, setStreamingText] = useState("");
  const [streamingMeta, setStreamingMeta] = useState<LessonQaTurnMeta | null>(
    null,
  );

  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const loadedRef = useRef(isDemo);

  const userMessageCount = messages.filter((m) => m.role === "user").length;
  const showChips = userMessageCount < 1 && prompts.length > 0 && !sending;

  useEffect(() => {
    if (isDemo) return;
    loadedRef.current = false;
    setMessages([]);
    setPrompts([]);
    setError(null);
    setStreamingText("");
    setStreamingMeta(null);
  }, [skillId, isDemo]);

  useEffect(() => {
    if (!open || loadedRef.current || isDemo) return;
    let cancelled = false;

    (async () => {
      setLoading(true);
      setError(null);
      try {
        const bundle = await getLessonQa(skillId);
        if (cancelled) return;
        setMessages(bundle.messages ?? []);
        setPrompts(bundle.suggested_prompts ?? []);
        loadedRef.current = true;
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load lesson Q&A",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [open, skillId, isDemo]);

  useEffect(() => {
    if (!open) return;
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [open, messages, streamingText]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  async function sendContent(content: string) {
    const text = content.trim();
    if (!text || sending) return;

    setSending(true);
    setError(null);
    setDraft("");
    setStreamingText("");
    setStreamingMeta(null);

    if (isDemo) {
      const now = Date.now();
      setMessages((prev) => [
        ...prev,
        {
          id: now,
          role: "user",
          content: text,
          meta: null,
          created_at: new Date().toISOString(),
        },
        {
          id: now + 1,
          role: "assistant",
          content:
            "A reservation is when you book a table for a future time.\n\nExample: I'd like to book a table for two.",
          meta: {
            route: "rag",
            sources: [{ unit_title: "Unit 3 – At a restaurant", score: 0.81 }],
          },
          created_at: new Date().toISOString(),
        },
      ]);
      setSending(false);
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamLessonQaMessage(
        skillId,
        text,
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
          onToken: (chunk) => {
            setStreamingText((prev) => prev + chunk);
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
        setError(
          err instanceof Error ? err.message : "Failed to send message",
        );
      }
    } finally {
      abortRef.current = null;
      setSending(false);
      setStreamingText("");
      setStreamingMeta(null);
    }
  }

  async function handleClear() {
    if (sending) return;
    setError(null);
    if (isDemo) {
      setMessages([]);
      setPrompts(demo?.prompts ?? []);
      return;
    }
    try {
      await clearLessonQa(skillId);
      setMessages([]);
      const bundle = await getLessonQa(skillId);
      setPrompts(bundle.suggested_prompts ?? []);
      setMessages(bundle.messages ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to clear chat");
    }
  }

  const streamingCite = formatLessonQaCite(sourcesFromMeta(streamingMeta));
  const streamingEmptyNote = retrievalEmptyNote(streamingMeta);

  if (!open) {
    return (
      <div className="pointer-events-none fixed bottom-5 right-5 z-[60]">
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="Hỏi về bài học"
          title={
            lessonTitle ? `Hỏi về bài học · ${lessonTitle}` : "Hỏi về bài học"
          }
          className="pointer-events-auto inline-flex h-11 items-center gap-2 rounded-[10px] border border-[#EAEAEA] bg-white px-3.5 text-[13px] font-medium text-[#2F3437] transition-[transform,background-color] duration-200 hover:bg-[#F7F6F3] active:scale-[0.98]"
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-[8px] bg-[#F7F6F3] text-[#2F3437]">
            <MessageCircle className="h-3.5 w-3.5" strokeWidth={2.25} />
          </span>
          Hỏi về bài
        </button>
      </div>
    );
  }

  return (
    <div className="pointer-events-none fixed inset-x-3 bottom-3 z-[60] flex justify-end sm:inset-x-auto sm:bottom-5 sm:right-5">
      <div
        className="pointer-events-auto flex max-h-[min(72vh,560px)] w-full max-w-[380px] flex-col overflow-hidden rounded-[12px] border border-[#EAEAEA] bg-white sm:w-[360px]"
        role="dialog"
        aria-label="Hỏi về bài học"
      >
        <header className="flex shrink-0 items-center justify-between gap-2 border-b border-[#EAEAEA] px-4 py-3">
          <div className="min-w-0">
            <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-[#787774]">
              Hỏi đáp
            </p>
            <p className="mt-0.5 truncate text-[13px] font-medium text-[#2F3437]">
              {lessonTitle || "Bài học hiện tại"}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-0.5">
            {messages.length > 0 ? (
              <button
                type="button"
                disabled={sending}
                onClick={() => void handleClear()}
                className="rounded-[6px] px-2 py-1 text-[11px] text-[#9B9A97] transition-colors hover:bg-[#F7F6F3] hover:text-[#787774] disabled:opacity-50"
              >
                Xóa
              </button>
            ) : null}
            <button
              type="button"
              aria-label="Đóng hỏi đáp"
              onClick={() => setOpen(false)}
              className="ml-0.5 flex h-7 w-7 items-center justify-center rounded-[6px] text-[#787774] transition-colors hover:bg-[#F7F6F3] hover:text-[#2F3437]"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </header>

        {error ? (
          <div className="shrink-0 border-b border-[#EAEAEA] bg-[#FDEBEC] px-4 py-2 text-[12px] text-[#9F2F2D]">
            {error}
          </div>
        ) : null}

        <div
          className={cn(
            "flex min-h-0 flex-col gap-2.5 overflow-y-auto px-3.5",
            messages.length === 0 && !streamingText && !sending
              ? "py-1"
              : "flex-1 py-3.5",
          )}
        >
          {loading ? (
            <div className="flex flex-1 items-center justify-center gap-2 py-10 text-[13px] text-[#787774]">
              <Loader2 className="h-4 w-4 animate-spin" />
              Đang tải…
            </div>
          ) : messages.length === 0 && !streamingText && !sending ? (
            <p className="px-1 py-2 text-[11px] leading-snug text-[#9B9A97]">
              Hỏi từ vựng / ngữ pháp trong bài — trả lời theo sách gắn skill.
            </p>
          ) : (
            <>
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
              {streamingText || (sending && !streamingText) ? (
                <div className="flex justify-start">
                  <div className="max-w-[88%] rounded-[12px_12px_12px_4px] bg-[#F7F6F3] px-3.5 py-2.5 text-[13px] leading-[1.55] text-[#2F3437]">
                    {streamingText ? (
                      <>
                        <p className="whitespace-pre-wrap">{streamingText}</p>
                        {streamingCite ? (
                          <p className="mt-2 text-[11px] text-[#787774]">
                            {streamingCite}
                          </p>
                        ) : null}
                        {streamingEmptyNote ? (
                          <p className="mt-1.5 text-[11px] text-[#9B9A97]">
                            {streamingEmptyNote}
                          </p>
                        ) : null}
                      </>
                    ) : (
                      <Loader2 className="h-4 w-4 animate-spin text-[#787774]" />
                    )}
                  </div>
                </div>
              ) : null}
            </>
          )}
          <div ref={bottomRef} />
        </div>

        {showChips ? (
          <div className="shrink-0 space-y-1.5 border-t border-[#EAEAEA] px-3.5 py-2.5">
            <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-[#9B9A97]">
              Gợi ý
            </p>
            <div className="flex flex-col gap-1">
              {prompts.slice(0, 4).map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  disabled={sending || loading}
                  onClick={() => void sendContent(prompt)}
                  className="rounded-[8px] border border-[#EAEAEA] bg-[#FBFBFA] px-3 py-2 text-left text-[12px] leading-snug text-[#2F3437] transition-colors hover:border-[#D4D4D4] hover:bg-[#F7F6F3] disabled:opacity-50"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        <form
          className="flex shrink-0 items-center gap-2 border-t border-[#EAEAEA] px-3 py-2.5"
          onSubmit={(e) => {
            e.preventDefault();
            void sendContent(draft);
          }}
        >
          <Input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Hỏi về bài học…"
            disabled={sending || loading}
            className="h-9 rounded-[8px] border-[#EAEAEA] bg-[#FBFBFA] text-[13px] text-[#2F3437] placeholder:text-[#9B9A97] focus-visible:border-[#2F3437] focus-visible:ring-0"
          />
          <Button
            type="submit"
            disabled={sending || loading || !draft.trim()}
            className="h-9 w-9 shrink-0 rounded-[8px] bg-[#2F3437] p-0 text-white hover:bg-[#2F3437]/90 active:scale-[0.98]"
            aria-label="Gửi"
          >
            {sending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Send className="h-3.5 w-3.5" />
            )}
          </Button>
        </form>
      </div>
    </div>
  );
}
