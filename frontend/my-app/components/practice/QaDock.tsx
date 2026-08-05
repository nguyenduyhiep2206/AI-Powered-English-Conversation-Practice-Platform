"use client";

import LessonQaPanel from "@/components/lesson/LessonQaPanel";

export function QaDock({
  skillId,
  lessonTitle,
}: {
  skillId: number;
  lessonTitle?: string;
}) {
  return (
    <LessonQaPanel
      skillId={skillId}
      lessonTitle={lessonTitle}
      variant="dock"
    />
  );
}
