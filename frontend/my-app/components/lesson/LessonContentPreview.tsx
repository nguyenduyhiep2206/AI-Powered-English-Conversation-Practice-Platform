"use client";

import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { summarizeContent } from "@/lib/admin-lessons";
import type { SkillLesson } from "@/lib/lesson";
import LessonContentWindow from "@/components/lesson/LessonContentWindow";

type Props = {
  lesson: SkillLesson | null;
  /** Full LessonPack when available (L1–L3). Falls back to single `lesson`. */
  pack?: SkillLesson[] | null;
  onClose: () => void;
};

function LessonBody({ lesson }: { lesson: SkillLesson }) {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline">{lesson.status}</Badge>
        {typeof lesson.pack_index === "number" ? (
          <Badge variant="secondary">L{(lesson.pack_index ?? 0) + 1}</Badge>
        ) : null}
        <span className="text-xs uppercase tracking-[0.12em] text-[#787774]">
          {summarizeContent(lesson.content)}
        </span>
      </div>
      <p className="text-sm leading-relaxed text-[#787774]">{lesson.objective}</p>

      {lesson.content.passage.gloss ? (
        <p className="text-sm text-[#787774]">{lesson.content.passage.gloss}</p>
      ) : null}

      {lesson.content.hook ? (
        <div>
          <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
            Hook
          </p>
          <p className="mt-2 text-sm leading-relaxed text-[#2F3437]">
            {lesson.content.hook}
          </p>
        </div>
      ) : null}

      <div>
        <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
          Passage
        </p>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-[#2F3437]">
          {lesson.content.passage.text}
        </p>
      </div>

      {lesson.content.form?.rows?.length ? (
        <div>
          <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
            Form
          </p>
          <p className="mt-2 text-sm font-medium text-[#2F3437]">
            {lesson.content.form.title || "Pattern"}
          </p>
          <ul className="mt-3 space-y-2 text-sm">
            {lesson.content.form.rows.map((row, i) => (
              <li
                key={`${row.pattern}-${i}`}
                className="rounded-[8px] border border-[#EAEAEA] px-3 py-2"
              >
                <span className="text-[#787774]">{row.label || "—"}</span>
                <span className="mx-2 font-medium text-[#2F3437]">
                  {row.pattern}
                </span>
                {row.example ? (
                  <span className="text-[#787774]">· {row.example}</span>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

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
  );
}

export default function LessonContentPreview({ lesson, pack, onClose }: Props) {
  const lessons = useMemo(() => {
    if (pack && pack.length > 0) {
      return [...pack].sort(
        (a, b) => (a.pack_index ?? 0) - (b.pack_index ?? 0),
      );
    }
    return lesson ? [lesson] : [];
  }, [lesson, pack]);

  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    setActiveIndex(0);
  }, [lessons.map((l) => l.id).join(",")]);

  const active = lessons[activeIndex] ?? null;
  const multi = lessons.length > 1;

  return (
    <LessonContentWindow
      open={active != null}
      title={
        multi && active
          ? `L${(active.pack_index ?? activeIndex) + 1}: ${active.title}`
          : active?.title
      }
      onClose={onClose}
    >
      {active ? (
        <div className="space-y-5">
          {multi ? (
            <div className="flex flex-wrap items-center gap-2 border-b border-[#EAEAEA] pb-3">
              <span className="text-xs text-[#787774]">
                Pack · {lessons.length} micro-lessons
              </span>
              <div className="flex flex-wrap gap-1">
                {lessons.map((item, i) => (
                  <Button
                    key={item.id}
                    type="button"
                    size="sm"
                    variant={i === activeIndex ? "default" : "outline"}
                    onClick={() => setActiveIndex(i)}
                  >
                    L{(item.pack_index ?? i) + 1}
                  </Button>
                ))}
              </div>
            </div>
          ) : null}
          <LessonBody lesson={active} />
        </div>
      ) : null}
    </LessonContentWindow>
  );
}
