import type { TutorMessage, TutorTurnMeta } from "@/lib/tutor";

export type TutorFeedbackItem = {
  id: string;
  kind: "correction" | "hint";
  original?: string;
  corrected?: string;
  note: string;
};

export function isTutorTurnMeta(meta: unknown): meta is TutorTurnMeta {
  return (
    meta != null &&
    typeof meta === "object" &&
    "goal_progress" in meta
  );
}

export function collectFeedbackItems(
  messages: TutorMessage[],
): TutorFeedbackItem[] {
  const items: TutorFeedbackItem[] = [];
  for (const message of messages) {
    if (message.role !== "assistant") continue;
    if (!isTutorTurnMeta(message.meta)) continue;
    const meta = message.meta;
    if (meta.correction) {
      items.push({
        id: `c-${message.id}`,
        kind: "correction",
        original: meta.correction.original,
        corrected: meta.correction.better,
        note: meta.correction.why ?? "",
      });
    }
    if (meta.hint?.trim()) {
      items.push({
        id: `h-${message.id}`,
        kind: "hint",
        note: meta.hint.trim(),
      });
    }
  }
  return items;
}
