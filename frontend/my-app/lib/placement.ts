import { authFetch, extractErrorMessage } from "@/lib/api";

export type PlacementQuestion = {
  id: number;
  skill_id: number;
  cefr_level: string;
  question_type: string;
  stem: string;
  passage?: string | null;
  options?: string[] | null;
  difficulty: string;
};

export type PlacementProgress = {
  asked: number;
  min_questions: number;
  max_questions: number;
};

export type PlacementSession = {
  done: boolean;
  attempt_id: number;
  question?: PlacementQuestion | null;
  progress?: PlacementProgress | null;
  placement_score?: number | null;
  current_level?: string | null;
  questions_asked?: number | null;
  onboarding_complete?: boolean | null;
};

export type PlacementRetakeStatus = {
  allowed: boolean;
  has_in_progress: boolean;
  retry_after_at?: string | null;
};

async function parseSession(res: Response, fallback: string): Promise<PlacementSession> {
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, fallback));
  }
  const body = (await res.json()) as { data: PlacementSession };
  return body.data;
}

/** Dedup concurrent POSTs (double-click / React Strict Mode remount). */
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

export async function submitPlacementAnswer(
  attemptId: number,
  payload: { question_id: number; answer: string },
): Promise<PlacementSession> {
  const res = await authFetch(
    `/api/v1/onboarding/placement/sessions/${attemptId}/answers`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
  return parseSession(res, "Failed to submit placement answer");
}

export async function fetchRetakeStatus(): Promise<PlacementRetakeStatus> {
  const res = await authFetch("/api/v1/onboarding/placement/retake-status");
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to load retake status"));
  }
  const body = (await res.json()) as { data: PlacementRetakeStatus };
  return body.data;
}
