import {
  listAdminLessonSkills,
  type AdminLessonSkillRow,
} from "@/lib/admin-lessons";

export type { AdminLessonSkillRow };

export async function listAdminSkills(
  cefrLevel?: string,
): Promise<AdminLessonSkillRow[]> {
  return listAdminLessonSkills(cefrLevel);
}
