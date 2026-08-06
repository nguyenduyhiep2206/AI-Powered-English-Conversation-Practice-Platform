import { authFetch, extractErrorMessage } from "@/lib/api";

export type SkillQuizQuestion = {
  id: number;
  skill_id: number;
  /** mcq | cloze | fix_grammar | sentence_build | matching | multi_select */
  question_type: string;
  item_kind?: string | null;
  stem: string;
  passage?: string | null;
  toeic_part?: string | null;
  options?: string[] | null;
  difficulty?: string | null;
};

export type QuizAnswerResult = {
  correct: boolean;
  mastery: number;
  explanation: string | null;
};

export async function fetchSkillQuestions(
  skillId: number,
  limit = 5,
): Promise<SkillQuizQuestion[]> {
  const res = await authFetch(
    `/api/v1/quiz/skills/${skillId}/questions?limit=${limit}`,
  );
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to load practice questions"));
  }
  const body = (await res.json()) as { data: SkillQuizQuestion[] };
  return body.data;
}

export async function submitQuizAnswer(
  questionId: number,
  answer: string,
): Promise<QuizAnswerResult> {
  const res = await authFetch("/api/v1/quiz/answer", {
    method: "POST",
    body: JSON.stringify({ question_id: questionId, answer }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to submit answer"));
  }
  return (await res.json()) as QuizAnswerResult;
}
