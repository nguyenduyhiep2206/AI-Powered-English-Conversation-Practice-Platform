import { authFetch, extractErrorMessage } from "@/lib/api";
import type { LessonContent, SkillLesson } from "@/lib/lesson";

export type AdminLessonSkillRow = {
  skill_id: number;
  title: string;
  skill_type: string;
  cefr_level: string;
  lesson_status: string | null;
  lesson_id: number | null;
};

export async function listAdminLessonSkills(
  cefrLevel?: string,
): Promise<AdminLessonSkillRow[]> {
  const q = cefrLevel ? `?cefr_level=${encodeURIComponent(cefrLevel)}` : "";
  const res = await authFetch(`/api/v1/admin/lessons/skills${q}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to list skills"));
  }
  const body = (await res.json()) as { data: AdminLessonSkillRow[] };
  return body.data;
}

export async function generateAdminLesson(skillId: number): Promise<SkillLesson> {
  const res = await authFetch(`/api/v1/admin/lessons/skills/${skillId}/generate`, {
    method: "POST",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to generate lesson"));
  }
  const body = (await res.json()) as { data: SkillLesson };
  return body.data;
}

export async function publishAdminLesson(skillId: number): Promise<SkillLesson> {
  const res = await authFetch(`/api/v1/admin/lessons/skills/${skillId}/publish`, {
    method: "POST",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to publish lesson"));
  }
  const body = (await res.json()) as { data: SkillLesson };
  return body.data;
}

export async function getAdminLesson(skillId: number): Promise<SkillLesson> {
  const res = await authFetch(`/api/v1/admin/lessons/skills/${skillId}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to load lesson"));
  }
  const body = (await res.json()) as { data: SkillLesson };
  return body.data;
}

export function summarizeContent(content: LessonContent): string {
  const nTargets = content.targets?.length ?? 0;
  const nChecks = content.checks?.length ?? 0;
  return `${nTargets} targets · ${nChecks} checks · writing`;
}
