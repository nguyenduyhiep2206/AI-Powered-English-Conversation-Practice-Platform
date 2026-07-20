import { authFetch, extractErrorMessage } from "@/lib/api";
import type { PlacementQuestion } from "@/lib/placement";

export type LevelChallengeQuestions = {
  target_level: string;
  question_count: number;
  questions: PlacementQuestion[];
};

export type LevelChallengeResult = {
  passed: boolean;
  correct_count: number;
  total: number;
  current_level: string;
  placement_score: number | null;
  target_level: string;
};

export async function fetchLevelChallengeQuestions(
  targetLevel?: string,
): Promise<LevelChallengeQuestions> {
  const query = targetLevel
    ? `?target_level=${encodeURIComponent(targetLevel)}`
    : "";
  const res = await authFetch(`/api/v1/onboarding/level-challenge${query}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(
      extractErrorMessage(error, "Failed to load level challenge questions"),
    );
  }
  const body = (await res.json()) as { data: LevelChallengeQuestions };
  return body.data;
}

export async function submitLevelChallenge(body: {
  target_level: string;
  answers: Array<{ question_id: number; answer: string }>;
}): Promise<LevelChallengeResult> {
  const res = await authFetch("/api/v1/onboarding/level-challenge", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to submit level challenge"));
  }
  const result = (await res.json()) as { data: LevelChallengeResult };
  return result.data;
}
