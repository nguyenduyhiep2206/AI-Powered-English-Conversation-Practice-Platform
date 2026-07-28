import { authFetch } from "@/lib/api";

export type SurveyQuestionType = "single_choice" | "text";

export type SurveyOption = {
  value: string;
  label: string;
};

export type SurveyQuestion = {
  id: number;
  prompt: string;
  question_type: SurveyQuestionType;
  options?: SurveyOption[] | null;
  is_required: boolean;
};

type SurveyQuestionsResponse = {
  success: boolean;
  data: { questions: SurveyQuestion[] };
};

export type SurveyAnswerPayload = {
  question_id: number;
  answer: { value?: string; text?: string };
};

export type LevelResolution =
  | { mode: "beginner" }
  | { mode: "self_selected"; cefr_level: "A1" | "A2" | "B1" | "B2" | "C1" }
  | { mode: "placement" };

export type SubmitSurveyResult = {
  survey_done: boolean;
  next_step: "placement" | "completed";
};

export async function fetchSurveyQuestions(): Promise<SurveyQuestion[]> {
  const res = await authFetch("/api/v1/onboarding/survey/questions");
  if (res.status === 409) {
    throw new Error("SURVEY_ALREADY_DONE");
  }
  if (!res.ok) {
    throw new Error("Failed to load survey questions");
  }
  const body = (await res.json()) as SurveyQuestionsResponse;
  return body.data.questions;
}

export async function submitSurvey(
  answers: SurveyAnswerPayload[],
  level_resolution: LevelResolution,
): Promise<SubmitSurveyResult> {
  const res = await authFetch("/api/v1/onboarding/survey", {
    method: "POST",
    body: JSON.stringify({ answers, level_resolution }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    const detail = (error as { detail?: string }).detail;
    throw new Error(detail || "Failed to submit survey");
  }
  const body = (await res.json()) as {
    data: SubmitSurveyResult;
  };
  return body.data;
}
