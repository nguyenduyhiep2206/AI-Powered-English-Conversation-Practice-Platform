"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import LessonQaPanel from "@/components/lesson/LessonQaPanel";
import type { LessonQaMessage } from "@/lib/lesson-qa";

const DEMO_PROMPTS = [
  'What does "reservation" mean?',
  'How do I use "I\'d like to…"?',
  "Give an example sentence for this lesson.",
  "How should I start the phone call?",
];

const DEMO_MESSAGES: LessonQaMessage[] = [
  {
    id: 1,
    role: "user",
    content: 'What does "reservation" mean?',
    meta: null,
    created_at: new Date().toISOString(),
  },
  {
    id: 2,
    role: "assistant",
    content:
      "A reservation is when you book a table for a future time.\n\nExample: I'd like to book a table for two.",
    meta: {
      route: "rag",
      sources: [{ unit_title: "Unit 3 – At a restaurant", score: 0.81 }],
    },
    created_at: new Date().toISOString(),
  },
];

function PreviewInner() {
  const params = useSearchParams();
  const closed = params.get("closed") === "1";
  const empty = params.get("empty") === "1";

  return (
    <div className="min-h-screen bg-[#F7F6F3]">
      <div className="mx-auto max-w-2xl px-6 py-16">
        <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-[#787774]">
          Dev preview
        </p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-[#2F3437]">
          Lesson Q&A panel
        </h1>
        <p className="mt-2 max-w-md text-sm leading-relaxed text-[#787774]">
          Mock lesson window. FAB sits bottom-right. Use{" "}
          <code className="rounded bg-white px-1 text-[12px]">?closed=1</code>{" "}
          or <code className="rounded bg-white px-1 text-[12px]">?empty=1</code>.
        </p>

        <div className="relative mt-10 min-h-[70vh] overflow-hidden rounded-[12px] border border-[#EAEAEA] bg-white">
          <div className="border-b border-[#EAEAEA] px-5 py-4">
            <h2 className="text-lg font-semibold tracking-tight text-[#2F3437]">
              Making a reservation
            </h2>
            <p className="mt-1 text-sm text-[#787774]">
              Book a table politely on the phone.
            </p>
          </div>
          <div className="space-y-4 px-5 py-6 text-sm leading-relaxed text-[#2F3437]">
            <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
              Hook
            </p>
            <p>You call a restaurant to book a table for Friday evening.</p>
            <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
              Notice
            </p>
            <p className="rounded-[8px] bg-[#F7F6F3] px-4 py-3">
              I'd like to book a table for two at 7 p.m., please.
            </p>
          </div>

          <LessonQaPanel
            skillId={0}
            lessonTitle="Making a reservation"
            demo={{
              defaultOpen: !closed,
              messages: empty ? [] : DEMO_MESSAGES,
              prompts: DEMO_PROMPTS,
            }}
          />
        </div>
      </div>
    </div>
  );
}

export default function LessonQaPreviewPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#F7F6F3]" />}>
      <PreviewInner />
    </Suspense>
  );
}
