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

export type LessonForm = {
  title: string;
  rows: { label: string; pattern: string; example?: string }[];
};

export type LessonContent = {
  hook?: string | null;
  passage: { text: string; gloss?: string | null };
  form?: LessonForm | null;
  targets: LessonTarget[];
  checks: LessonCheck[];
  writing: {
    prompt: string;
    min_words: number;
    must_use: string[];
  };
  exit_check?: LessonCheck | null;
};

export type SkillLesson = {
  id: number;
  skill_id: number;
  pack_index?: number;
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
  pack_total?: number;
  pack_completed_count?: number;
  pack?: SkillLesson[];
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

export async function completeSkillLesson(
  skillId: number,
  packIndex = 0,
): Promise<SkillLessonResponse> {
  const res = await authFetch(
    `/api/v1/skills/${skillId}/lesson/complete?pack_index=${packIndex}`,
    {
      method: "POST",
    },
  );
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to complete lesson"));
  }
  return (await res.json()) as SkillLessonResponse;
}

export async function requestWritingFeedback(
  skillId: number,
  text: string,
  packIndex?: number,
): Promise<WritingFeedback> {
  const body: { text: string; pack_index?: number } = { text };
  if (packIndex != null) body.pack_index = packIndex;
  const res = await authFetch(`/api/v1/skills/${skillId}/lesson/writing/feedback`, {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to get writing feedback"));
  }
  return (await res.json()) as WritingFeedback;
}
