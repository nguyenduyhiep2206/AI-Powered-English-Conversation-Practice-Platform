import { authFetch, extractErrorMessage } from "@/lib/api";

export type LessonTarget = {
  surface: string;
  gloss: string;
  note?: string;
};

export type LessonCheck = {
  type: "mcq" | "cloze";
  prompt: string;
  options: string[];
  answer: string;
};

export type LessonContent = {
  passage: { text: string; gloss?: string | null };
  targets: LessonTarget[];
  checks: LessonCheck[];
  writing: {
    prompt: string;
    min_words: number;
    must_use: string[];
  };
};

export type SkillLesson = {
  id: number;
  skill_id: number;
  title: string;
  objective: string;
  content: LessonContent;
  source: string;
  status: string;
  book_source_id?: number | null;
};

export type SkillLessonResponse = {
  learn_available: boolean;
  can_skip: boolean;
  lesson_completed: boolean;
  mastery: number;
  lesson: SkillLesson | null;
};

export type WritingFeedback = {
  original: string;
  corrected: string;
  notes: string[];
};

export async function fetchSkillLesson(skillId: number): Promise<SkillLessonResponse> {
  const res = await authFetch(`/api/v1/skills/${skillId}/lesson`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to load lesson"));
  }
  return (await res.json()) as SkillLessonResponse;
}

export async function completeSkillLesson(skillId: number): Promise<SkillLessonResponse> {
  const res = await authFetch(`/api/v1/skills/${skillId}/lesson/complete`, {
    method: "POST",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to complete lesson"));
  }
  return (await res.json()) as SkillLessonResponse;
}

export async function requestWritingFeedback(
  skillId: number,
  text: string,
): Promise<WritingFeedback> {
  const res = await authFetch(`/api/v1/skills/${skillId}/lesson/writing/feedback`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to get writing feedback"));
  }
  return (await res.json()) as WritingFeedback;
}
