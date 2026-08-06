"use client";

import LessonQaPanel from "@/components/lesson/LessonQaPanel";

export function QaDock({
  skillId,
  lessonTitle,
  showSuggestions = true,
}: {
  skillId: number;
  lessonTitle?: string;
  showSuggestions?: boolean;
}) {
  return (
    <LessonQaPanel
      skillId={skillId}
      lessonTitle={lessonTitle}
      variant="dock"
      showSuggestions={showSuggestions}
    />
  );
}
