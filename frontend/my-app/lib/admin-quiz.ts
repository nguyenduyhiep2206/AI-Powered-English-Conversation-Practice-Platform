import { authFetch, extractErrorMessage } from "@/lib/api";

export type SkillSourceRow = {
  id: number;
  skill_id: number;
  unit_id: number;
  unit_title: string;
  section_title?: string | null;
  is_excluded: boolean;
  is_primary: boolean;
};

export type SyncSkillsResult = {
  book_id: number;
  source_count: number;
  excluded: number;
  llm_used?: boolean;
  edge_count_added?: number;
  sources: SkillSourceRow[];
};

export type QuizQuestionRow = {
  id: number;
  skill_id: number;
  book_id: number;
  unit_id: number;
  question_type: string;
  stem: string;
  passage?: string | null;
  passage_id?: number | null;
  toeic_part?: string | null;
  prompt_words?: string[] | null;
  media_url?: string | null;
  task_brief?: Record<string, unknown> | null;
  options?: string[] | null;
  answer: string;
  explanation?: string | null;
  difficulty: string;
  status: string;
  generation_batch_id?: string | null;
};

export async function syncBookSkills(bookId: number): Promise<SyncSkillsResult> {
  const res = await authFetch(`/api/v1/admin/quiz/books/${bookId}/sync-skills`, {
    method: "POST",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to sync skills"));
  }
  const body = (await res.json()) as { data: SyncSkillsResult };
  return body.data;
}

export async function generateSkillQuiz(
  skillId: number,
  count = 8,
): Promise<QuizQuestionRow[]> {
  const res = await authFetch(`/api/v1/admin/quiz/skills/${skillId}/generate`, {
    method: "POST",
    body: JSON.stringify({ count }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to generate quiz"));
  }
  const body = (await res.json()) as { data: QuizQuestionRow[] };
  return body.data;
}

export async function generateSkillWriting(
  skillId: number,
  count = 2,
): Promise<QuizQuestionRow[]> {
  const res = await authFetch(
    `/api/v1/admin/quiz/skills/${skillId}/generate-writing`,
    {
      method: "POST",
      body: JSON.stringify({ count }),
    },
  );
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to generate writing"));
  }
  const body = (await res.json()) as { data: QuizQuestionRow[] };
  return body.data;
}

export async function listBookQuestions(
  bookId: number,
  statusFilter?: "draft" | "published",
): Promise<QuizQuestionRow[]> {
  const q = statusFilter ? `?status_filter=${statusFilter}` : "";
  const res = await authFetch(`/api/v1/admin/quiz/books/${bookId}/questions${q}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to load questions"));
  }
  const body = (await res.json()) as { data: QuizQuestionRow[] };
  return body.data;
}

export async function publishQuestions(
  questionIds: number[],
): Promise<{ published: number; skipped: number }> {
  const res = await authFetch(`/api/v1/admin/quiz/questions/publish`, {
    method: "POST",
    body: JSON.stringify({ question_ids: questionIds }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to publish questions"));
  }
  const body = (await res.json()) as {
    data: { published: number; skipped?: number };
  };
  return {
    published: body.data.published,
    skipped: body.data.skipped ?? 0,
  };
}
