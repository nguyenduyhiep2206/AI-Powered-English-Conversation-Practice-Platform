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

type Step = "read" | "check" | "write" | "feedback";

type Props = {
  skillId: number;
  title: string;
  objective: string;
  content: LessonContent;
  onFinished: () => void;
  /** Hide title block when shown inside LessonContentWindow. */
  embedded?: boolean;
};

export default function LessonMiniUnit({
  skillId,
  title,
  objective,
  content,
  onFinished,
  embedded = false,
}: Props) {
  const [step, setStep] = useState<Step>("read");
  const [checkIndex, setCheckIndex] = useState(0);
  const [checkAnswer, setCheckAnswer] = useState("");
  const [checkRevealed, setCheckRevealed] = useState(false);
  const [writingText, setWritingText] = useState("");
  const [writingBusy, setWritingBusy] = useState(false);
  const [writingError, setWritingError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<WritingFeedback | null>(null);

  const checks = content.checks ?? [];
  const currentCheck: LessonCheck | undefined = checks[checkIndex];

  function goNextAfterCheck() {
    setCheckAnswer("");
    setCheckRevealed(false);
    if (checkIndex + 1 >= checks.length) {
      setStep("write");
      return;
    }
    setCheckIndex((i) => i + 1);
  }

  async function submitWriting() {
    setWritingBusy(true);
    setWritingError(null);
    try {
      const result = await requestWritingFeedback(skillId, writingText);
      setFeedback(result);
      setStep("feedback");
    } catch (err) {
      setWritingError(err instanceof Error ? err.message : "Feedback failed");
    } finally {
      setWritingBusy(false);
    }
  }

  return (
    <section className="space-y-6">
      {embedded ? (
        <div>
          <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
            Learn · {step}
          </p>
          <p className="mt-2 text-sm leading-relaxed text-[#787774]">{objective}</p>
        </div>
      ) : (
        <div>
          <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
            Learn · {step}
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-[#2F3437]">
            {title}
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-[#787774]">{objective}</p>
        </div>
      )}

      {step === "read" ? (
        <div className="space-y-5 rounded-[12px] border border-[#EAEAEA] bg-white p-6">
          {content.passage.gloss ? (
            <p className="text-sm text-[#787774]">{content.passage.gloss}</p>
          ) : null}
          <p className="whitespace-pre-wrap text-base leading-relaxed text-[#2F3437]">
            {content.passage.text}
          </p>
          <div>
            <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
              Notice
            </p>
            <ul className="mt-3 flex flex-wrap gap-2">
              {content.targets.map((t) => {
                const gloss = t.gloss || "";
                return (
                <li
                  key={t.surface}
                  className="rounded-[8px] border border-[#EAEAEA] bg-[#F7F6F3] px-3 py-2 text-sm"
                >
                  <span className="font-medium text-[#2F3437]">{t.surface}</span>
                  {gloss ? (
                    <span className="ml-2 text-[#787774]">{gloss}</span>
                  ) : null}
                </li>
                );
              })}
            </ul>
          </div>
          <Button
            type="button"
            size="lg"
            className="w-full"
            onClick={() => setStep(checks.length ? "check" : "write")}
          >
            Continue
          </Button>
        </div>
      ) : null}

      {step === "check" && currentCheck ? (
        <div className="space-y-5 rounded-[12px] border border-[#EAEAEA] bg-white p-6">
          <p className="text-[11px] uppercase tracking-[0.14em] text-[#787774]">
            Check {checkIndex + 1}/{checks.length}
          </p>
          <p className="text-base font-medium text-[#2F3437]">{currentCheck.prompt}</p>

          {currentCheck.type === "mcq" && currentCheck.options?.length ? (
            <div className="grid gap-2">
              {currentCheck.options.map((option) => {
                const selected = checkAnswer === option;
                const show = checkRevealed;
                const correct = option === currentCheck.answer;
                return (
                  <button
                    key={option}
                    type="button"
                    disabled={checkRevealed}
                    onClick={() => setCheckAnswer(option)}
                    className={`rounded-[8px] border px-4 py-3 text-left text-sm ${
                      show && correct
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
              value={checkAnswer}
              disabled={checkRevealed}
              onChange={(e) => setCheckAnswer(e.target.value)}
              placeholder="Your answer"
            />
          )}

          {checkRevealed ? (
            <div className="space-y-3">
              <p
                className={`text-sm ${
                  checkAnswer.trim().toLowerCase() ===
                  currentCheck.answer.trim().toLowerCase()
                    ? "text-[#346538]"
                    : "text-[#9F2F2D]"
                }`}
              >
                {checkAnswer.trim().toLowerCase() ===
                currentCheck.answer.trim().toLowerCase()
                  ? "Correct"
                  : `Answer: ${currentCheck.answer}`}
              </p>
              <Button type="button" size="lg" className="w-full" onClick={goNextAfterCheck}>
                Continue
              </Button>
            </div>
          ) : (
            <Button
              type="button"
              size="lg"
              className="w-full"
              disabled={!checkAnswer.trim()}
              onClick={() => setCheckRevealed(true)}
            >
              Check
            </Button>
          )}
        </div>
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
          <Button type="button" size="lg" className="w-full" onClick={onFinished}>
            Continue to practice
          </Button>
        </div>
      ) : null}
    </section>
  );
}
