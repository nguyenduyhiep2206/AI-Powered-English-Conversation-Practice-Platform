import { authFetch, extractErrorMessage } from "@/lib/api";

export type TutorSessionStatus = "active" | "completed" | "abandoned";

export type TutorTurnMeta = {
  correction: { original: string; better: string; why: string } | null;
  hint: string | null;
  goal_progress: "none" | "partial" | "done";
  off_topic?: boolean;
};

export type TutorDebugInfo = {
  route: "roleplay" | "rag" | "off_topic" | string;
  cache_hit: boolean;
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

export type TutorMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  meta: TutorTurnMeta | Record<string, unknown> | null;
  created_at: string;
};

export type TutorScenario = {
  id: number;
  title: string;
  slug: string;
  description: string | null;
  category: string;
  level: string;
  ai_role: string;
  user_role: string;
  goal_prompt: string;
  suggested_vocab: string[] | null;
  order_index: number;
};

export type TutorSession = {
  id: number;
  user_id: number;
  roadmap_step_id: number | null;
  scenario_id: number;
  status: TutorSessionStatus;
  target_skill_ids: number[];
  message_count: number;
  summary: TutorSummary | null;
  started_at: string;
  ended_at: string | null;
  messages?: TutorMessage[];
  scenario?: TutorScenario | null;
};

export type TutorSessionDetail = TutorSession & {
  messages: TutorMessage[];
};

export type TutorSummary = {
  went_well: string[];
  fix_next: string[];
  soft_skill_signals: {
    skill_id: number;
    signal: string;
    note: string;
  }[];
};

/** Shared SSE sink used by tutor + lesson Q&A streams. */
export type SseStreamHandlers = {
  onUserMessage?: (msg: { id: number; content: string }) => void;
  onToken?: (text: string) => void;
  onMeta?: (meta: Record<string, unknown>) => void;
  onAssistantMessage?: (msg: {
    id: number;
    content: string;
    meta: Record<string, unknown> | null;
  }) => void;
  onDebug?: (info: Record<string, unknown>) => void;
  onError?: (err: { code?: string; message: string }) => void;
  onDone?: () => void;
};

export type StreamTutorMessageHandlers = {
  onUserMessage?: (msg: { id: number; content: string }) => void;
  onToken?: (text: string) => void;
  onMeta?: (meta: TutorTurnMeta) => void;
  onAssistantMessage?: (msg: {
    id: number;
    content: string;
    meta: TutorTurnMeta | null;
  }) => void;
  onDebug?: (info: TutorDebugInfo) => void;
  onError?: (err: { code?: string; message: string }) => void;
  onDone?: () => void;
};

const TUTOR_PREFIX = "/api/v1/tutor";

async function parseApiError(res: Response, fallback: string): Promise<never> {
  const error = await res.json().catch(() => ({}));
  throw new Error(extractErrorMessage(error, fallback));
}

function dispatchSseBlock(
  block: string,
  handlers: SseStreamHandlers,
): void {
  let event = "message";
  let data = "";

  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      data += line.slice(5).trim();
    }
  }

  if (!data) return;

  const payload = JSON.parse(data) as Record<string, unknown>;

  switch (event) {
    case "user_message":
      handlers.onUserMessage?.({
        id: Number(payload.id),
        content: String(payload.content ?? ""),
      });
      break;
    case "token":
      handlers.onToken?.(String(payload.text ?? ""));
      break;
    case "meta":
      handlers.onMeta?.(payload);
      break;
    case "assistant_message":
      handlers.onAssistantMessage?.({
        id: Number(payload.id),
        content: String(payload.content ?? ""),
        meta:
          payload.meta && typeof payload.meta === "object"
            ? (payload.meta as Record<string, unknown>)
            : null,
      });
      break;
    case "debug":
      handlers.onDebug?.(payload);
      break;
    case "error":
      handlers.onError?.({
        code: typeof payload.code === "string" ? payload.code : undefined,
        message: String(payload.message ?? "Stream failed"),
      });
      break;
    case "done":
      handlers.onDone?.();
      break;
    default:
      break;
  }
}

export async function readSseStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  handlers: SseStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      if (signal?.aborted) {
        await reader.cancel();
        return;
      }

      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        if (block.trim()) {
          dispatchSseBlock(block, handlers);
        }
        boundary = buffer.indexOf("\n\n");
      }
    }

    if (buffer.trim()) {
      dispatchSseBlock(buffer, handlers);
    }
  } finally {
    reader.releaseLock();
  }
}

export async function listTutorScenarios(
  level?: string,
): Promise<TutorScenario[]> {
  const qs = level ? `?level=${encodeURIComponent(level)}` : "";
  const res = await authFetch(`${TUTOR_PREFIX}/scenarios${qs}`);

  if (!res.ok) {
    await parseApiError(res, "Failed to load tutor scenarios");
  }

  const body = (await res.json()) as { data: TutorScenario[] };
  return body.data;
}

export async function startTutorSession(input: {
  scenarioId: number;
}): Promise<TutorSession> {
  const res = await authFetch(`${TUTOR_PREFIX}/sessions`, {
    method: "POST",
    body: JSON.stringify({ scenario_id: input.scenarioId }),
  });

  if (!res.ok) {
    await parseApiError(res, "Failed to start tutor session");
  }

  const json = (await res.json()) as { data: TutorSession };
  return json.data;
}

export async function getTutorSession(id: number): Promise<TutorSessionDetail> {
  const res = await authFetch(`${TUTOR_PREFIX}/sessions/${id}`);

  if (!res.ok) {
    await parseApiError(res, "Failed to load tutor session");
  }

  const body = (await res.json()) as { data: TutorSessionDetail };
  return body.data;
}

export async function streamTutorMessage(
  sessionId: number,
  content: string,
  handlers: StreamTutorMessageHandlers,
  options?: { signal?: AbortSignal; debug?: boolean },
): Promise<void> {
  const res = await authFetch(`${TUTOR_PREFIX}/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify({
      content,
      debug: Boolean(options?.debug),
    }),
    signal: options?.signal,
  });

  if (!res.ok) {
    await parseApiError(res, "Failed to send message");
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
        ? (meta) => handlers.onMeta?.(meta as TutorTurnMeta)
        : undefined,
      onAssistantMessage: handlers.onAssistantMessage
        ? (msg) =>
            handlers.onAssistantMessage?.({
              id: msg.id,
              content: msg.content,
              meta: (msg.meta as TutorTurnMeta | null) ?? null,
            })
        : undefined,
      onDebug: handlers.onDebug
        ? (info) => handlers.onDebug?.(info as TutorDebugInfo)
        : undefined,
      onError: handlers.onError,
      onDone: handlers.onDone,
    },
    options?.signal,
  );
}

export async function endTutorSession(id: number): Promise<TutorSummary> {
  const res = await authFetch(`${TUTOR_PREFIX}/sessions/${id}/end`, {
    method: "POST",
  });

  if (!res.ok) {
    await parseApiError(res, "Failed to end tutor session");
  }

  const body = (await res.json()) as { data: TutorSummary };
  return body.data;
}
