import { authFetch, extractErrorMessage } from "@/lib/api";

export type RoadmapWeekStatus = "locked" | "in_progress" | "completed";

export type RoadmapWeek = {
  week_number: number;
  roadmap_step_id: number;
  title: string;
  skill_id: number;
  skill_slug: string;
  skill_title: string | null;
  skill_type: string | null;
  difficulty_in_level: number;
  scenario_id: number;
  scenario_title: string;
  status: RoadmapWeekStatus;
  mastery: number;
  level: string;
  theme_unit_slug?: string | null;
  theme_unit_title?: string | null;
  theme_unit_can_do?: string | null;
  theme_unit_position?: number | null;
};

export type ThemeUnitGroup = {
  unitKey: string;
  title: string;
  canDo: string;
  weeks: RoadmapWeek[];
};

/** Group roadmap weeks by theme unit (order preserved). */
export function groupWeeksByThemeUnit(weeks: RoadmapWeek[]): ThemeUnitGroup[] {
  const groups: ThemeUnitGroup[] = [];
  const indexByKey = new Map<string, number>();
  for (const week of weeks) {
    const key = week.theme_unit_slug?.trim() || `_skill_${week.skill_id}`;
    const existing = indexByKey.get(key);
    if (existing == null) {
      indexByKey.set(key, groups.length);
      groups.push({
        unitKey: key,
        title: week.theme_unit_title?.trim() || week.skill_title || week.title,
        canDo: week.theme_unit_can_do?.trim() || "",
        weeks: [week],
      });
    } else {
      groups[existing].weeks.push(week);
    }
  }
  return groups;
}

export type CompleteRoadmapStepResult = {
  step_id: number;
  status: string;
  skill_id: number;
  mastery: number;
  unlocked_step_id: number | null;
  replanned?: boolean;
};

export type AssembleRoadmapOptions = {
  level?: string;
  max_steps?: number;
};

const CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1"] as const;

/** Next CEFR band after `level`, or null at C1 / unknown. */
export function nextCefrBand(level: string | null | undefined): string | null {
  if (!level) return null;
  const i = CEFR_ORDER.indexOf(level as (typeof CEFR_ORDER)[number]);
  if (i < 0 || i >= CEFR_ORDER.length - 1) return null;
  return CEFR_ORDER[i + 1];
}

export async function fetchRoadmap(): Promise<RoadmapWeek[]> {
  const res = await authFetch("/api/v1/roadmap");
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to load roadmap"));
  }
  const body = (await res.json()) as { data: RoadmapWeek[] };
  return body.data;
}

export async function assembleRoadmap(
  opts?: AssembleRoadmapOptions,
): Promise<RoadmapWeek[]> {
  const res = await authFetch("/api/v1/roadmap/assemble", {
    method: "POST",
    body: JSON.stringify({
      ...(opts?.level ? { level: opts.level } : {}),
      max_steps: opts?.max_steps ?? 30,
    }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to assemble roadmap"));
  }
  const body = (await res.json()) as { data: RoadmapWeek[] };
  return body.data;
}

export async function completeRoadmapStep(
  roadmapStepId: number,
): Promise<CompleteRoadmapStepResult> {
  const res = await authFetch(`/api/v1/roadmap/steps/${roadmapStepId}/complete`, {
    method: "POST",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to complete roadmap week"));
  }
  const body = (await res.json()) as { data: CompleteRoadmapStepResult };
  return body.data;
}
