import { authFetch, extractErrorMessage } from "@/lib/api";
import { listAdminLessonSkills, type AdminLessonSkillRow } from "@/lib/admin-lessons";

export type { AdminLessonSkillRow };

export type SkillWorkspace = {
  skill: {
    id: number;
    title: string;
    skill_type: string;
    cefr_level: string;
  };
  lesson: {
    status: string | null;
    id: number | null;
    title: string | null;
  };
  book_source: {
    book_id: number;
    unit_id: number;
    unit_title: string | null;
    is_primary: boolean;
  } | null;
  quiz: {
    draft_count: number;
    published_count: number;
    draft_skill_drill_count: number;
    can_generate_skill_drill: boolean;
    block_reason: string | null;
  };
};

export async function listAdminSkills(
  cefrLevel?: string,
): Promise<AdminLessonSkillRow[]> {
  return listAdminLessonSkills(cefrLevel);
}

export async function fetchSkillWorkspace(
  skillId: number,
): Promise<SkillWorkspace> {
  const res = await authFetch(`/api/v1/admin/skills/${skillId}/workspace`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to load skill workspace"));
  }
  const body = (await res.json()) as { data: SkillWorkspace };
  return body.data;
}

export function blockReasonLabel(reason: string | null): string | null {
  if (!reason) return null;
  if (reason === "grammar_requires_published_lesson") {
    return "Publish a lesson first (grammar skill_drill needs lesson targets/form).";
  }
  if (reason === "no_book_source") {
    return "Attach a book unit to this skill (Open Attach) before generating.";
  }
  return reason;
}
