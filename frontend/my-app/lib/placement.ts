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

export type PlacementResult = {
  placement_score: number;
  current_level: string;
  correct_count: number;
  total: number;
  onboarding_complete: boolean;
};

export async function fetchPlacementQuestions(): Promise<PlacementQuestion[]> {
  const res = await authFetch("/api/v1/onboarding/questions");
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to load placement questions"));
  }
  const body = (await res.json()) as {
    data: { question_count: number; questions: PlacementQuestion[] };
  };
  return body.data.questions;
}

export async function submitPlacement(
  answers: { question_id: number; answer: string }[],
): Promise<PlacementResult> {
  const res = await authFetch("/api/v1/onboarding/placement", {
    method: "POST",
    body: JSON.stringify({ answers }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to submit placement"));
  }
  const body = (await res.json()) as { data: PlacementResult };
  return body.data;
}
