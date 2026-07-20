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
};

export type CompleteRoadmapStepResult = {
  step_id: number;
  status: string;
  skill_id: number;
  mastery: number;
  unlocked_step_id: number | null;
};

export type AssembleRoadmapOptions = {
  level?: string;
  max_steps?: number;
};

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
      ...(opts?.max_steps != null ? { max_steps: opts.max_steps } : {}),
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
