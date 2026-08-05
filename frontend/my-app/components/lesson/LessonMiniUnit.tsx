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
  /** Hide title block when shown inside LessonContentWindow. */
  embedded?: boolean;
  packIndex?: number;
  packLabel?: string | null;
};

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
    <div className="space-y-5 rounded-[12px] border border-[#EAEAEA] bg-white p-6">
      <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
        {label}
      </p>
      <p className="text-base font-medium text-[#2F3437]">{check.prompt}</p>

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
                className={`rounded-[8px] border px-4 py-3 text-left text-sm ${
                  revealed && isCorrect
                    ? "border-[#346538]/40 bg-[#EDF3EC] text-[#346538]"
                    : selected
                      ? "border-[#2F3437] bg-[#F7F6F3] text-[#2F3437]"
                      : "border-[#EAEAEA] text-[#787774]"
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
        />
      )}

      {revealed ? (
        <div className="space-y-3">
          <p className={`text-sm ${correct ? "text-[#346538]" : "text-[#9F2F2D]"}`}>
            {correct ? "Correct" : `Answer: ${check.answer}`}
          </p>
          <Button type="button" size="lg" className="w-full" onClick={onContinue}>
            Continue
          </Button>
        </div>
      ) : (
        <Button
          type="button"
          size="lg"
          className="w-full"
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
    <section className="space-y-6">
      {embedded ? (
        <div>
          <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
            Learn{packLabel ? ` · ${packLabel}` : ""} · {step}
          </p>
          <p className="mt-2 text-sm leading-relaxed text-[#787774]">{objective}</p>
        </div>
      ) : (
        <div>
          <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
            Learn{packLabel ? ` · ${packLabel}` : ""} · {step}
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-[#2F3437]">
            {title}
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-[#787774]">{objective}</p>
        </div>
      )}

      {step === "hook" && content.hook ? (
        <div className="space-y-5 rounded-[12px] border border-[#EAEAEA] bg-white p-6">
          <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
            Hook
          </p>
          <p className="text-base leading-relaxed text-[#2F3437]">{content.hook}</p>
          <Button
            type="button"
            size="lg"
            className="w-full"
            onClick={() => advanceFrom("hook")}
          >
            Continue
          </Button>
        </div>
      ) : null}

      {step === "notice" ? (
        <div className="space-y-5 rounded-[12px] border border-[#EAEAEA] bg-white p-6">
          <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
            Notice
          </p>
          {content.passage.gloss ? (
            <p className="text-sm text-[#787774]">{content.passage.gloss}</p>
          ) : null}
          <p className="whitespace-pre-wrap text-base leading-relaxed text-[#2F3437]">
            {content.passage.text}
          </p>
          <Button
            type="button"
            size="lg"
            className="w-full"
            onClick={() => advanceFrom("notice")}
          >
            Continue
          </Button>
        </div>
      ) : null}

      {step === "form" && content.form?.rows?.length ? (
        <div className="space-y-5 rounded-[12px] border border-[#EAEAEA] bg-white p-6">
          <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
            Form
          </p>
          <h2 className="text-lg font-medium text-[#2F3437]">
            {content.form.title || "Pattern"}
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[280px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-[#EAEAEA] text-left text-[#787774]">
                  <th className="py-2 pr-3 font-medium">Label</th>
                  <th className="py-2 pr-3 font-medium">Pattern</th>
                  <th className="py-2 font-medium">Example</th>
                </tr>
              </thead>
              <tbody>
                {content.form.rows.map((row, i) => (
                  <tr key={`${row.pattern}-${i}`} className="border-b border-[#F0F0F0]">
                    <td className="py-2.5 pr-3 text-[#787774]">{row.label || "—"}</td>
                    <td className="py-2.5 pr-3 font-medium text-[#2F3437]">
                      {row.pattern}
                    </td>
                    <td className="py-2.5 text-[#2F3437]">{row.example || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Button
            type="button"
            size="lg"
            className="w-full"
            onClick={() => advanceFrom("form")}
          >
            Continue
          </Button>
        </div>
      ) : null}

      {step === "meaning" ? (
        <div className="space-y-5 rounded-[12px] border border-[#EAEAEA] bg-white p-6">
          <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
            Meaning
          </p>
          <ul className="flex flex-wrap gap-2">
            {content.targets.map((t) => {
              const gloss = t.gloss || "";
              return (
                <li
                  key={t.surface}
                  className="rounded-[8px] border border-[#EAEAEA] bg-[#F7F6F3] px-3 py-2 text-sm"
                >
                  <span className="font-medium text-[#2F3437]">{t.surface}</span>
                  {gloss ? (
                    <span className="ml-2 text-[#787774]"> — {gloss}</span>
                  ) : null}
                </li>
              );
            })}
          </ul>
          <Button
            type="button"
            size="lg"
            className="w-full"
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
        <div className="space-y-5 rounded-[12px] border border-[#EAEAEA] bg-white p-6">
          <p className="text-base font-medium text-[#2F3437]">{content.writing.prompt}</p>
          {content.writing.must_use?.length ? (
            <p className="text-sm text-[#787774]">
              Try to use: {content.writing.must_use.join(", ")}
            </p>
          ) : null}
          <textarea
            className="min-h-[140px] w-full rounded-[8px] border border-[#EAEAEA] bg-[#FBFBFA] px-3 py-2 text-sm text-[#2F3437] outline-none focus:border-[#2F3437]"
            value={writingText}
            onChange={(e) => setWritingText(e.target.value)}
            placeholder="Write in English…"
          />
          {writingError ? (
            <p className="text-sm text-[#9F2F2D]" role="alert">
              {writingError}
            </p>
          ) : null}
          <Button
            type="button"
            size="lg"
            className="w-full"
            disabled={writingBusy || !writingText.trim()}
            onClick={() => void submitWriting()}
          >
            {writingBusy ? "Getting feedback…" : "Get feedback"}
          </Button>
        </div>
      ) : null}

      {step === "feedback" && feedback ? (
        <div className="space-y-5 rounded-[12px] border border-[#EAEAEA] bg-white p-6">
          <div>
            <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
              Your writing
            </p>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-[#787774]">
              {feedback.original}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
              Suggested
            </p>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-[#2F3437]">
              {feedback.corrected}
            </p>
          </div>
          {feedback.notes.length ? (
            <ul className="list-disc space-y-1 pl-5 text-sm text-[#787774]">
              {feedback.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          ) : null}
          <Button type="button" size="lg" className="w-full" onClick={finishAfterFeedback}>
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
