import { authFetch, extractErrorMessage } from "@/lib/api";
import { readSseStream } from "@/lib/tutor";

export type LessonQaSource = {
  unit_title: string;
  score?: number;
};

export type LessonQaTurnMeta = {
  route?: "rag" | "retrieval_empty" | "off_topic" | "smalltalk" | string;
  sources?: LessonQaSource[];
  off_topic?: boolean;
  [key: string]: unknown;
};

export type LessonQaDebugInfo = {
  route: string;
  cefr?: string | null;
  cache_hit?: boolean;
  memory_tokens?: number;
  retrieved_tokens?: number;
  chunk_count?: number;
  chunks?: {
    score?: number;
    unit_title?: string | null;
    book_id?: number;
    unit_id?: number;
    preview?: string;
  }[];
};

export type LessonQaMessage = {
  id: number;
  role: "user" | "assistant" | "system" | string;
  content: string;
  meta: LessonQaTurnMeta | null;
  created_at: string;
};

export type LessonQaSession = {
  id: number;
  skill_id: number;
  status: string;
  message_count: number;
};

export type LessonQaBundle = {
  session: LessonQaSession;
  messages: LessonQaMessage[];
  suggested_prompts: string[];
};

export type StreamLessonQaHandlers = {
  onUserMessage?: (msg: { id: number; content: string }) => void;
  onToken?: (text: string) => void;
  onMeta?: (meta: LessonQaTurnMeta) => void;
  onAssistantMessage?: (msg: {
    id: number;
    content: string;
    meta: LessonQaTurnMeta | null;
  }) => void;
  onDebug?: (info: LessonQaDebugInfo) => void;
  onError?: (err: { code?: string; message: string }) => void;
  onDone?: () => void;
};

const LESSON_QA_PREFIX = "/api/v1/lessons";

async function parseApiError(res: Response, fallback: string): Promise<never> {
  const error = await res.json().catch(() => ({}));
  throw new Error(extractErrorMessage(error, fallback));
}

export async function getLessonQa(skillId: number): Promise<LessonQaBundle> {
  const res = await authFetch(`${LESSON_QA_PREFIX}/${skillId}/qa`);

  if (!res.ok) {
    await parseApiError(res, "Failed to load lesson Q&A");
  }

  const body = (await res.json()) as { data: LessonQaBundle };
  return body.data;
}

export async function streamLessonQaMessage(
  skillId: number,
  content: string,
  handlers: StreamLessonQaHandlers,
  options?: { signal?: AbortSignal; debug?: boolean },
): Promise<void> {
  const res = await authFetch(`${LESSON_QA_PREFIX}/${skillId}/qa/messages`, {
    method: "POST",
    body: JSON.stringify({
      content,
      debug: Boolean(options?.debug),
    }),
    signal: options?.signal,
  });

  if (!res.ok) {
    await parseApiError(res, "Failed to send lesson Q&A message");
  }

  const reader = res.body?.getReader();
  if (!reader) {
    throw new Error("Streaming response unavailable");
  }

  await readSseStream(
    reader,
    {
      onUserMessage: handlers.onUserMessage,
      onToken: handlers.onToken,
      onMeta: handlers.onMeta
        ? (meta) => handlers.onMeta?.(meta as LessonQaTurnMeta)
        : undefined,
      onAssistantMessage: handlers.onAssistantMessage
        ? (msg) =>
            handlers.onAssistantMessage?.({
              id: msg.id,
              content: msg.content,
              meta: (msg.meta as LessonQaTurnMeta | null) ?? null,
            })
        : undefined,
      onDebug: handlers.onDebug
        ? (info) => handlers.onDebug?.(info as LessonQaDebugInfo)
        : undefined,
      onError: handlers.onError,
      onDone: handlers.onDone,
    },
    options?.signal,
  );
}

export async function clearLessonQa(skillId: number): Promise<void> {
  const res = await authFetch(`${LESSON_QA_PREFIX}/${skillId}/qa/messages`, {
    method: "DELETE",
  });

  if (!res.ok) {
    await parseApiError(res, "Failed to clear lesson Q&A");
  }
}

export function formatLessonQaCite(
  sources: LessonQaSource[] | undefined | null,
): string | null {
  if (!sources?.length) return null;
  const titles = sources
    .map((s) => (s.unit_title || "").trim())
    .filter(Boolean)
    .slice(0, 3);
  if (titles.length === 0) return null;
  return `Theo sách: ${titles.join(" · ")}`;
}
