"use client";

import { Badge } from "@/components/ui/badge";
import { summarizeContent } from "@/lib/admin-lessons";
import type { SkillLesson } from "@/lib/lesson";
import LessonContentWindow from "@/components/lesson/LessonContentWindow";

type Props = {
  lesson: SkillLesson | null;
  onClose: () => void;
};

export default function LessonContentPreview({ lesson, onClose }: Props) {
  return (
    <LessonContentWindow
      open={lesson != null}
      title={lesson?.title}
      onClose={onClose}
    >
      {lesson ? (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">{lesson.status}</Badge>
            <span className="text-xs uppercase tracking-[0.12em] text-[#787774]">
              {summarizeContent(lesson.content)}
            </span>
          </div>
          <p className="text-sm leading-relaxed text-[#787774]">
            {lesson.objective}
          </p>

          {lesson.content.passage.gloss ? (
            <p className="text-sm text-[#787774]">{lesson.content.passage.gloss}</p>
          ) : null}
          <div>
            <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
              Passage
            </p>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-[#2F3437]">
              {lesson.content.passage.text}
            </p>
          </div>

          <div>
            <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
              Targets
            </p>
            <ul className="mt-3 flex flex-wrap gap-2">
              {lesson.content.targets.map((t) => (
                <li
                  key={t.surface}
                  className="rounded-[8px] border border-[#EAEAEA] bg-[#F7F6F3] px-3 py-2 text-sm"
                >
                  <span className="font-medium text-[#2F3437]">{t.surface}</span>
                  {t.gloss ? (
                    <span className="ml-2 text-[#787774]">{t.gloss}</span>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>

          {lesson.content.checks?.length ? (
            <div>
              <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
                Checks
              </p>
              <ul className="mt-3 space-y-3">
                {lesson.content.checks.map((c, i) => (
                  <li
                    key={`${c.prompt}-${i}`}
                    className="rounded-[8px] border border-[#EAEAEA] px-3 py-3 text-sm"
                  >
                    <p className="text-[#2F3437]">{c.prompt}</p>
                    <p className="mt-1 text-[#787774]">Answer: {c.answer}</p>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div>
            <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
              Writing
            </p>
            <p className="mt-2 text-sm text-[#2F3437]">
              {lesson.content.writing.prompt}
            </p>
            {lesson.content.writing.must_use?.length ? (
              <p className="mt-2 text-sm text-[#787774]">
                Must use: {lesson.content.writing.must_use.join(", ")}
              </p>
            ) : null}
          </div>
        </div>
      ) : null}
    </LessonContentWindow>
  );
}
