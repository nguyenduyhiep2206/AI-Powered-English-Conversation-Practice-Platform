"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type {
  LessonCheck,
  LessonContent,
  WritingFeedback,
} from "@/lib/lesson";
import { requestWritingFeedback } from "@/lib/lesson";

type Step =
  | "hook"
  | "notice"
  | "form"
  | "meaning"
  | "check"
  | "write"
  | "feedback"
  | "exit";

type Props = {
  skillId: number;
  title: string;
  objective: string;
  content: LessonContent;
  onFinished: () => void;
  /** Compact title/objective header for PracticeShell (no modal title bar). */
  embedded?: boolean;
  packIndex?: number;
  packLabel?: string | null;
};

const PRIMARY_BTN =
  "h-11 w-full rounded-2xl bg-[#FF8A6B] font-semibold text-white hover:bg-[#F47A5A]";

const PANEL =
  "space-y-5 rounded-[1.75rem] border border-[#EDE6E0] bg-white p-6 shadow-[0_12px_40px_rgba(42,36,56,0.04)]";

const EYEBROW =
  "text-[0.75rem] font-medium uppercase tracking-[0.14em] text-[#8A8396]";

function buildStepOrder(content: LessonContent): Step[] {
  const steps: Step[] = [];
  if (content.hook?.trim()) steps.push("hook");
  steps.push("notice");
  if (content.form?.rows?.length) steps.push("form");
  if (content.targets?.length) steps.push("meaning");
  if (content.checks?.length) steps.push("check");
  steps.push("write");
  steps.push("feedback");
  if (content.exit_check) steps.push("exit");
  return steps;
}

function CheckPanel({
  label,
  check,
  answer,
  revealed,
  onAnswer,
  onReveal,
  onContinue,
}: {
  label: string;
  check: LessonCheck;
  answer: string;
  revealed: boolean;
  onAnswer: (v: string) => void;
  onReveal: () => void;
  onContinue: () => void;
}) {
  const correct =
    answer.trim().toLowerCase() === check.answer.trim().toLowerCase();

  return (
    <div className={PANEL}>
      <p className={EYEBROW}>{label}</p>
      <p className="text-[0.9375rem] font-medium text-[#2A2438]">
        {check.prompt}
      </p>

      {check.type === "mcq" && check.options?.length ? (
        <div className="grid gap-2">
          {check.options.map((option) => {
            const selected = answer === option;
            const isCorrect = option === check.answer;
            return (
              <button
                key={option}
                type="button"
                disabled={revealed}
                onClick={() => onAnswer(option)}
                className={`rounded-[12px] border px-4 py-3 text-left text-[0.875rem] transition-colors ${
                  revealed && isCorrect
                    ? "border-[#8CC6E8]/50 bg-[rgba(140,198,232,0.18)] text-[#3D7FA0]"
                    : selected
                      ? "border-[#FF8A6B] bg-[#FFF0E8] text-[#2A2438]"
                      : "border-[#EDE6E0] text-[#6B6478] hover:border-[#FF8A6B]/40"
                }`}
              >
                {option}
              </button>
            );
          })}
        </div>
      ) : (
        <Input
          value={answer}
          disabled={revealed}
          onChange={(e) => onAnswer(e.target.value)}
          placeholder="Your answer"
          className="h-11 rounded-[12px] border-[#EDE6E0] bg-[#FFFCF9] text-[0.875rem] text-[#2A2438] placeholder:text-[#8A8396] focus-visible:border-[#FF8A6B] focus-visible:ring-0"
        />
      )}

      {revealed ? (
        <div className="space-y-3">
          <p
            className={`text-[0.875rem] ${
              correct ? "text-[#3D7FA0]" : "text-[#C24B3A]"
            }`}
          >
            {correct ? "Correct" : `Answer: ${check.answer}`}
          </p>
          <Button type="button" size="lg" className={PRIMARY_BTN} onClick={onContinue}>
            Continue
          </Button>
        </div>
      ) : (
        <Button
          type="button"
          size="lg"
          className={PRIMARY_BTN}
          disabled={!answer.trim()}
          onClick={onReveal}
        >
          Check
        </Button>
      )}
    </div>
  );
}

export default function LessonMiniUnit({
  skillId,
  title,
  objective,
  content,
  onFinished,
  embedded = false,
  packIndex,
  packLabel,
}: Props) {
  const order = buildStepOrder(content);
  const [step, setStep] = useState<Step>(order[0] ?? "notice");
  const [checkIndex, setCheckIndex] = useState(0);
  const [checkAnswer, setCheckAnswer] = useState("");
  const [checkRevealed, setCheckRevealed] = useState(false);
  const [exitAnswer, setExitAnswer] = useState("");
  const [exitRevealed, setExitRevealed] = useState(false);
  const [writingText, setWritingText] = useState("");
  const [writingBusy, setWritingBusy] = useState(false);
  const [writingError, setWritingError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<WritingFeedback | null>(null);

  const checks = content.checks ?? [];
  const currentCheck: LessonCheck | undefined = checks[checkIndex];

  function goTo(next: Step) {
    setStep(next);
  }

  function advanceFrom(current: Step) {
    const i = order.indexOf(current);
    const next = order[i + 1];
    if (!next) {
      onFinished();
      return;
    }
    if (next === "feedback") {
      // feedback only after writing submit
      goTo("write");
      return;
    }
    goTo(next);
  }

  function goNextAfterCheck() {
    setCheckAnswer("");
    setCheckRevealed(false);
    if (checkIndex + 1 >= checks.length) {
      goTo("write");
      return;
    }
    setCheckIndex((i) => i + 1);
  }

  async function submitWriting() {
    setWritingBusy(true);
    setWritingError(null);
    try {
      const result = await requestWritingFeedback(skillId, writingText, packIndex);
      setFeedback(result);
      goTo("feedback");
    } catch (err) {
      setWritingError(err instanceof Error ? err.message : "Feedback failed");
    } finally {
      setWritingBusy(false);
    }
  }

  function finishAfterFeedback() {
    if (content.exit_check) {
      goTo("exit");
      return;
    }
    onFinished();
  }

  return (
    <section className="space-y-6 text-[#2A2438]">
      {embedded ? (
        <div className="mb-5 border-b border-[#EDE6E0] pb-4">
          {packLabel ? (
            <p className="text-[0.75rem] font-medium text-[#FF8A6B]">
              Part {packLabel}
            </p>
          ) : null}
          <h2 className="text-[1.25rem] font-semibold tracking-tight text-[#2A2438]">
            {title}
          </h2>
          {objective ? (
            <p className="mt-1 text-[0.875rem] text-[#8A8396]">{objective}</p>
          ) : null}
        </div>
      ) : (
        <div>
          <p className={EYEBROW}>
            Learn{packLabel ? ` · ${packLabel}` : ""} · {step}
          </p>
          <h1 className="mt-2 text-[1.75rem] font-semibold tracking-tight text-[#2A2438]">
            {title}
          </h1>
          {objective ? (
            <p className="mt-2 text-[0.875rem] leading-relaxed text-[#6B6478]">
              {objective}
            </p>
          ) : null}
        </div>
      )}

      {step === "hook" && content.hook ? (
        <div className={PANEL}>
          <p className={EYEBROW}>Hook</p>
          <p className="text-[0.9375rem] leading-relaxed text-[#2A2438]">
            {content.hook}
          </p>
          <Button
            type="button"
            size="lg"
            className={PRIMARY_BTN}
            onClick={() => advanceFrom("hook")}
          >
            Continue
          </Button>
        </div>
      ) : null}

      {step === "notice" ? (
        <div className={PANEL}>
          <p className={EYEBROW}>Notice</p>
          {content.passage.gloss ? (
            <p className="text-[0.875rem] text-[#6B6478]">{content.passage.gloss}</p>
          ) : null}
          <p className="whitespace-pre-wrap text-[0.9375rem] leading-relaxed text-[#2A2438]">
            {content.passage.text}
          </p>
          <Button
            type="button"
            size="lg"
            className={PRIMARY_BTN}
            onClick={() => advanceFrom("notice")}
          >
            Continue
          </Button>
        </div>
      ) : null}

      {step === "form" && content.form?.rows?.length ? (
        <div className={PANEL}>
          <p className={EYEBROW}>Form</p>
          <h2 className="text-[1.25rem] font-medium text-[#2A2438]">
            {content.form.title || "Pattern"}
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[280px] border-collapse text-[0.875rem]">
              <thead>
                <tr className="border-b border-[#EDE6E0] text-left text-[#6B6478]">
                  <th className="py-2 pr-3 font-medium">Label</th>
                  <th className="py-2 pr-3 font-medium">Pattern</th>
                  <th className="py-2 font-medium">Example</th>
                </tr>
              </thead>
              <tbody>
                {content.form.rows.map((row, i) => (
                  <tr key={`${row.pattern}-${i}`} className="border-b border-[#EDE6E0]/70">
                    <td className="py-2.5 pr-3 text-[#6B6478]">{row.label || "—"}</td>
                    <td className="py-2.5 pr-3 font-medium text-[#2A2438]">
                      {row.pattern}
                    </td>
                    <td className="py-2.5 text-[#2A2438]">{row.example || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Button
            type="button"
            size="lg"
            className={PRIMARY_BTN}
            onClick={() => advanceFrom("form")}
          >
            Continue
          </Button>
        </div>
      ) : null}

      {step === "meaning" ? (
        <div className={PANEL}>
          <p className={EYEBROW}>Meaning</p>
          <ul className="flex flex-wrap gap-2">
            {content.targets.map((t) => {
              const gloss = t.gloss || "";
              return (
                <li
                  key={t.surface}
                  className="rounded-[12px] border border-[#EDE6E0] bg-[#FFFCF9] px-3 py-2 text-[0.875rem]"
                >
                  <span className="font-medium text-[#2A2438]">{t.surface}</span>
                  {gloss ? (
                    <span className="ml-2 text-[#6B6478]"> — {gloss}</span>
                  ) : null}
                </li>
              );
            })}
          </ul>
          <Button
            type="button"
            size="lg"
            className={PRIMARY_BTN}
            onClick={() => advanceFrom("meaning")}
          >
            Continue
          </Button>
        </div>
      ) : null}

      {step === "check" && currentCheck ? (
        <CheckPanel
          label={`Check ${checkIndex + 1}/${checks.length}`}
          check={currentCheck}
          answer={checkAnswer}
          revealed={checkRevealed}
          onAnswer={setCheckAnswer}
          onReveal={() => setCheckRevealed(true)}
          onContinue={goNextAfterCheck}
        />
      ) : null}

      {step === "write" ? (
        <div className={PANEL}>
          <p className="text-[0.9375rem] font-medium text-[#2A2438]">
            {content.writing.prompt}
          </p>
          {content.writing.must_use?.length ? (
            <p className="text-[0.875rem] text-[#6B6478]">
              Try to use: {content.writing.must_use.join(", ")}
            </p>
          ) : null}
          <textarea
            className="min-h-[140px] w-full rounded-[12px] border border-[#EDE6E0] bg-[#FFFCF9] px-3 py-2 text-[0.875rem] text-[#2A2438] outline-none placeholder:text-[#8A8396] focus:border-[#FF8A6B]"
            value={writingText}
            onChange={(e) => setWritingText(e.target.value)}
            placeholder="Write in English…"
          />
          {writingError ? (
            <p className="text-[0.875rem] text-[#C24B3A]" role="alert">
              {writingError}
            </p>
          ) : null}
          <Button
            type="button"
            size="lg"
            className={PRIMARY_BTN}
            disabled={writingBusy || !writingText.trim()}
            onClick={() => void submitWriting()}
          >
            {writingBusy ? "Getting feedback…" : "Get feedback"}
          </Button>
        </div>
      ) : null}

      {step === "feedback" && feedback ? (
        <div className={PANEL}>
          <div>
            <p className={EYEBROW}>Your writing</p>
            <p className="mt-2 whitespace-pre-wrap text-[0.875rem] leading-relaxed text-[#6B6478]">
              {feedback.original}
            </p>
          </div>
          <div>
            <p className={EYEBROW}>Suggested</p>
            <p className="mt-2 whitespace-pre-wrap text-[0.875rem] leading-relaxed text-[#2A2438]">
              {feedback.corrected}
            </p>
          </div>
          {feedback.notes.length ? (
            <ul className="list-disc space-y-1 pl-5 text-[0.875rem] text-[#6B6478]">
              {feedback.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          ) : null}
          <Button
            type="button"
            size="lg"
            className={PRIMARY_BTN}
            onClick={finishAfterFeedback}
          >
            {content.exit_check ? "One more check" : "Continue to practice"}
          </Button>
        </div>
      ) : null}

      {step === "exit" && content.exit_check ? (
        <CheckPanel
          label="Exit check"
          check={content.exit_check}
          answer={exitAnswer}
          revealed={exitRevealed}
          onAnswer={setExitAnswer}
          onReveal={() => setExitRevealed(true)}
          onContinue={onFinished}
        />
      ) : null}
    </section>
  );
}
