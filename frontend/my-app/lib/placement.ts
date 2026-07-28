import { authFetch, extractErrorMessage } from "@/lib/api";

export type PlacementFormItem = {
  id: number;
  toeic_part?: string | null;
  stem?: string | null;
  options?: string[] | null;
  skill_id?: number | null;
  cefr_level?: string | null;
  passage_id?: number | null;
  prompt_words?: string[] | null;
  media_url?: string | null;
  task_brief?: Record<string, unknown> | null;
  question_type?: string | null;
};

export type PlacementForm = {
  reading_items: PlacementFormItem[];
  writing_items: PlacementFormItem[];
  passages: Record<string, { id?: number; body?: string; media_url?: string | null }>;
};

export type PlacementSession = {
  done: boolean;
  attempt_id: number;
  section?: string | null;
  section_ends_at?: string | null;
  form?: PlacementForm | null;
  saved_answers?: Record<string, string> | null;
  reading_raw?: number | null;
  reading_scale?: number | null;
  writing_raw?: number | null;
  writing_scale?: number | null;
  placement_score?: number | null;
  current_level?: string | null;
  writing_feedback?: Array<{ item_id: number; score: number; feedback?: string }> | null;
  onboarding_complete?: boolean | null;
};

export type PlacementAccessStatus = {
  can_start: boolean;
  has_in_progress: boolean;
};

async function parseSession(res: Response, fallback: string): Promise<PlacementSession> {
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, fallback));
  }
  const body = (await res.json()) as { data: PlacementSession };
  return body.data;
}

let startSessionInFlight: Promise<PlacementSession> | null = null;

export async function startPlacementSession(): Promise<PlacementSession> {
  if (startSessionInFlight) return startSessionInFlight;
  startSessionInFlight = (async () => {
    const res = await authFetch("/api/v1/onboarding/placement/sessions", {
      method: "POST",
    });
    return parseSession(res, "Failed to start placement session");
  })().finally(() => {
    startSessionInFlight = null;
  });
  return startSessionInFlight;
}

export async function getCurrentPlacementSession(): Promise<PlacementSession | null> {
  const res = await authFetch("/api/v1/onboarding/placement/sessions/current");
  if (res.status === 404) return null;
  return parseSession(res, "Failed to load placement session");
}

export async function submitReadingAnswers(
  attemptId: number,
  answers: Array<{ item_id: number; given_answer: string }>,
): Promise<PlacementSession> {
  const res = await authFetch(
    `/api/v1/onboarding/placement/sessions/${attemptId}/reading-answers`,
    {
      method: "POST",
      body: JSON.stringify({ answers }),
    },
  );
  return parseSession(res, "Failed to submit reading answers");
}

export async function submitWritingAnswer(
  attemptId: number,
  payload: { item_id: number; text: string },
): Promise<PlacementSession> {
  const res = await authFetch(
    `/api/v1/onboarding/placement/sessions/${attemptId}/writing-answers`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
  return parseSession(res, "Failed to submit writing answer");
}

export async function advancePlacementSection(attemptId: number): Promise<PlacementSession> {
  const res = await authFetch(
    `/api/v1/onboarding/placement/sessions/${attemptId}/advance-section`,
    { method: "POST" },
  );
  return parseSession(res, "Failed to advance section");
}

export async function completePlacementSession(attemptId: number): Promise<PlacementSession> {
  const res = await authFetch(
    `/api/v1/onboarding/placement/sessions/${attemptId}/complete`,
    { method: "POST" },
  );
  return parseSession(res, "Failed to complete placement");
}

export async function fetchPlacementAccessStatus(): Promise<PlacementAccessStatus> {
  const res = await authFetch("/api/v1/onboarding/placement/access-status");
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to load placement access"));
  }
  const body = (await res.json()) as { data: PlacementAccessStatus };
  return body.data;
}
