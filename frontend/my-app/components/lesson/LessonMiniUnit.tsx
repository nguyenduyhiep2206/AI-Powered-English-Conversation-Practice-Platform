"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type {
  LessonCheck,
  LessonContent,
  WritingFeedback,
} from "@/lib/lesson";
import { requestWritingFeedback } from "@/lib/lesson";
import { cn } from "@/lib/utils";

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
  /** Display-ready label, e.g. "Part 2/3" or "Review". */
  packLabel?: string | null;
  /** When true, show step jumper for review navigation (no auto-finish). */
  reviewMode?: boolean;
  onStepChange?: (info: { step: Step; index: number; total: number }) => void;
  /** Called when learner presses Back on the first mini-unit step (e.g. previous pack). */
  onBackFromStart?: () => void;
};

const PRIMARY_BTN =
  "h-11 w-full rounded-2xl bg-[#FF8A6B] font-semibold text-white hover:bg-[#F47A5A]";

const SECONDARY_BTN =
  "h-11 w-full rounded-2xl border border-[#EDE6E0] bg-white font-semibold text-[#2A2438] hover:bg-[#FFF0E8]";

const PANEL =
  "space-y-5 rounded-[1.75rem] border border-[#EDE6E0] bg-white p-6 shadow-[0_12px_40px_rgba(42,36,56,0.04)]";

const EYEBROW =
  "text-[0.75rem] font-medium uppercase tracking-[0.14em] text-[#6B6478]";

const STEP_LABEL: Record<Step, string> = {
  hook: "Hook",
  notice: "Notice",
  form: "Form",
  meaning: "Meaning",
  check: "Check",
  write: "Write",
  feedback: "Feedback",
  exit: "Exit check",
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

function StepActions({
  onBack,
  children,
}: {
  onBack?: () => void;
  children: ReactNode;
}) {
  if (!onBack) return <>{children}</>;
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      <Button
        type="button"
        size="lg"
        variant="outline"
        className={SECONDARY_BTN}
        onClick={onBack}
      >
        Back
      </Button>
      {children}
    </div>
  );
}

/** Keeps passage + targets visible during Check / Write (Memory Bridge). */
function LessonContextStrip({ content }: { content: LessonContent }) {
  const [open, setOpen] = useState(true);
  const passage = content.passage?.text?.trim() ?? "";
  const targets = content.targets ?? [];
  if (!passage && targets.length === 0) return null;

  return (
    <div className="rounded-2xl border border-[#EDE6E0] bg-[#FFFCF9] px-4 py-3 ring-1 ring-[#2A2438]/04">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-3 text-left text-[0.8125rem] font-medium text-[#5C5468] cursor-pointer"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span>Lesson reference</span>
        <span className="text-[#7B6EF6]">{open ? "Hide" : "Show"}</span>
      </button>
      {open ? (
        <div className="mt-3 space-y-3">
          {passage ? (
            <p className="max-h-36 overflow-y-auto whitespace-pre-wrap text-[0.875rem] leading-relaxed text-[#2A2438]">
              {passage}
            </p>
          ) : null}
          {targets.length > 0 ? (
            <ul className="flex flex-wrap gap-1.5">
              {targets.map((t) => (
                <li
                  key={t.surface}
                  className="rounded-[10px] border border-[#EDE6E0] bg-white px-2.5 py-1 text-[0.75rem] text-[#2A2438]"
                >
                  <span className="font-medium">{t.surface}</span>
                  {t.gloss ? (
                    <span className="text-[#6B6478]"> — {t.gloss}</span>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function CheckPanel({
  label,
  check,
  answer,
  revealed,
  onAnswer,
  onReveal,
  onContinue,
  onBack,
}: {
  label: string;
  check: LessonCheck;
  answer: string;
  revealed: boolean;
  onAnswer: (v: string) => void;
  onReveal: () => void;
  onContinue: () => void;
  onBack?: () => void;
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
          className="h-11 rounded-[12px] border-[#EDE6E0] bg-[#FFFCF9] text-[0.875rem] text-[#2A2438] placeholder:text-[#6B6478] focus-visible:border-[#FF8A6B] focus-visible:ring-0"
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
          <StepActions onBack={onBack}>
            <Button
              type="button"
              size="lg"
              className={PRIMARY_BTN}
              onClick={onContinue}
            >
              Continue
            </Button>
          </StepActions>
        </div>
      ) : (
        <StepActions onBack={onBack}>
          <Button
            type="button"
            size="lg"
            className={PRIMARY_BTN}
            disabled={!answer.trim()}
            onClick={onReveal}
          >
            Check
          </Button>
        </StepActions>
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
  reviewMode = false,
  onStepChange,
  onBackFromStart,
}: Props) {
  const order = buildStepOrder(content);
  const [step, setStep] = useState<Step>(order[0] ?? "notice");

  function reportStep(next: Step) {
    onStepChange?.({
      step: next,
      index: order.indexOf(next),
      total: order.length,
    });
  }

  useEffect(() => {
    reportStep(order[0] ?? "notice");
    // Report initial step once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
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
  const stepPos = Math.max(0, order.indexOf(step));
  const canGoBack =
    stepPos > 0 ||
    (step === "check" && checkIndex > 0) ||
    Boolean(onBackFromStart);
  const showContextStrip =
    step === "check" ||
    step === "write" ||
    step === "feedback" ||
    step === "exit";

  function goTo(next: Step) {
    setStep(next);
    reportStep(next);
  }

  function resetCheckDraft() {
    setCheckAnswer("");
    setCheckRevealed(false);
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

  function goBack() {
    if (step === "check" && checkIndex > 0) {
      setCheckIndex((i) => i - 1);
      resetCheckDraft();
      return;
    }

    const i = order.indexOf(step);
    if (i <= 0) {
      onBackFromStart?.();
      return;
    }
    const prev = order[i - 1];

    if (prev === "check" && checks.length > 0) {
      setCheckIndex(checks.length - 1);
      resetCheckDraft();
    }

    goTo(prev);
  }

  function goNextAfterCheck() {
    resetCheckDraft();
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
      const result = await requestWritingFeedback(
        skillId,
        writingText,
        packIndex,
      );
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

  const backHandler = canGoBack ? goBack : undefined;
  const progressLabel = `${STEP_LABEL[step]} · ${stepPos + 1} of ${order.length}`;

  return (
    <section className="space-y-6 text-[#2A2438]">
      {embedded ? (
        <div className="mb-5 border-b border-[#EDE6E0] pb-4">
          {packLabel ? (
            <p className="text-[0.75rem] font-medium text-[#C45D42]">
              {packLabel}
            </p>
          ) : null}
          {objective ? (
            <p className="mt-1 text-[0.875rem] text-[#6B6478]">{objective}</p>
          ) : null}
          <p className="mt-2 text-[0.75rem] font-medium text-[#6B6478]">
            {progressLabel}
          </p>
        </div>
      ) : (
        <div>
          <p className={EYEBROW}>
            Learn{packLabel ? ` · ${packLabel}` : ""} · {progressLabel}
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

      {reviewMode ? (
        <div
          className="flex flex-wrap gap-1.5"
          role="navigation"
          aria-label="Lesson steps"
        >
          {order.map((s) => {
            const disabled = s === "feedback" && !feedback;
            const active = s === step;
            return (
              <button
                key={s}
                type="button"
                disabled={disabled}
                onClick={() => {
                  if (s === "check") {
                    setCheckIndex(0);
                    resetCheckDraft();
                  }
                  goTo(s);
                }}
                className={cn(
                  "rounded-2xl px-2.5 py-1.5 text-[0.75rem] font-medium ring-1",
                  active
                    ? "bg-[#FFF0E8] text-[#C45D42] ring-[#FF8A6B]/35"
                    : "bg-white text-[#6B6478] ring-[#EDE6E0]",
                  disabled && "opacity-40",
                )}
              >
                {STEP_LABEL[s]}
              </button>
            );
          })}
        </div>
      ) : null}

      {showContextStrip ? <LessonContextStrip content={content} /> : null}

      {step === "hook" && content.hook ? (
        <div className={PANEL}>
          <p className={EYEBROW}>Hook</p>
          <p className="text-[0.9375rem] leading-relaxed text-[#2A2438]">
            {content.hook}
          </p>
          <StepActions onBack={backHandler}>
            <Button
              type="button"
              size="lg"
              className={PRIMARY_BTN}
              onClick={() => advanceFrom("hook")}
            >
              Continue
            </Button>
          </StepActions>
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
          <StepActions onBack={backHandler}>
            <Button
              type="button"
              size="lg"
              className={PRIMARY_BTN}
              onClick={() => advanceFrom("notice")}
            >
              Continue
            </Button>
          </StepActions>
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
                  <tr
                    key={`${row.pattern}-${i}`}
                    className="border-b border-[#EDE6E0]/70"
                  >
                    <td className="py-2.5 pr-3 text-[#6B6478]">
                      {row.label || "—"}
                    </td>
                    <td className="py-2.5 pr-3 font-medium text-[#2A2438]">
                      {row.pattern}
                    </td>
                    <td className="py-2.5 text-[#2A2438]">
                      {row.example || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <StepActions onBack={backHandler}>
            <Button
              type="button"
              size="lg"
              className={PRIMARY_BTN}
              onClick={() => advanceFrom("form")}
            >
              Continue
            </Button>
          </StepActions>
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
          <StepActions onBack={backHandler}>
            <Button
              type="button"
              size="lg"
              className={PRIMARY_BTN}
              onClick={() => advanceFrom("meaning")}
            >
              Continue
            </Button>
          </StepActions>
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
          onBack={backHandler}
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
            className="min-h-[140px] w-full rounded-[12px] border border-[#EDE6E0] bg-[#FFFCF9] px-3 py-2 text-[0.875rem] text-[#2A2438] outline-none placeholder:text-[#6B6478] focus:border-[#FF8A6B]"
            value={writingText}
            onChange={(e) => setWritingText(e.target.value)}
            placeholder="Write in English…"
          />
          {writingError ? (
            <p className="text-[0.875rem] text-[#C24B3A]" role="alert">
              {writingError}
            </p>
          ) : null}
          <StepActions onBack={backHandler}>
            <Button
              type="button"
              size="lg"
              className={PRIMARY_BTN}
              disabled={writingBusy || !writingText.trim()}
              onClick={() => void submitWriting()}
            >
              {writingBusy ? "Getting feedback…" : "Get feedback"}
            </Button>
          </StepActions>
        </div>
      ) : null}

      {step === "feedback" && feedback ? (
        <div className={PANEL}>
          <div>
            <p className={EYEBROW}>Your task</p>
            <p className="mt-2 text-[0.9375rem] font-medium leading-relaxed text-[#2A2438]">
              {content.writing.prompt}
            </p>
            {content.writing.must_use?.length ? (
              <p className="mt-2 text-[0.875rem] text-[#6B6478]">
                Try to use: {content.writing.must_use.join(", ")}
              </p>
            ) : null}
          </div>

          <div>
            <p className={EYEBROW}>Your writing</p>
            <p className="mt-2 whitespace-pre-wrap text-[0.875rem] leading-relaxed text-[#6B6478]">
              {feedback.original}
            </p>
          </div>

          <div>
            <p className={EYEBROW}>
              {feedback.usable === false ? "Example answer" : "Suggested rewrite"}
            </p>
            <p className="mt-2 whitespace-pre-wrap text-[0.875rem] leading-relaxed text-[#2A2438]">
              {feedback.corrected}
            </p>
          </div>

          {feedback.notes.length ? (
            <div>
              <p className={EYEBROW}>Coach notes</p>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-[0.875rem] text-[#6B6478]">
                {feedback.notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {content.form?.rows?.length ? (
            <div className="rounded-[12px] border border-[#EDE6E0] bg-[#FFFCF9] px-4 py-3">
              <p className={EYEBROW}>Remember</p>
              <ul className="mt-2 space-y-1.5 text-[0.8125rem] leading-relaxed text-[#5C5468]">
                {content.form.rows.slice(0, 4).map((row, i) => (
                  <li key={`${row.pattern}-${i}`}>
                    {row.label ? (
                      <span className="font-medium text-[#2A2438]">
                        {row.label}
                        {": "}
                      </span>
                    ) : null}
                    <span>{row.pattern}</span>
                    {row.example ? (
                      <span className="text-[#6B6478]"> — {row.example}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <StepActions onBack={backHandler}>
            <Button
              type="button"
              size="lg"
              className={PRIMARY_BTN}
              onClick={finishAfterFeedback}
            >
              {content.exit_check ? "One more check" : "Continue to practice"}
            </Button>
          </StepActions>
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
          onBack={backHandler}
        />
      ) : null}
    </section>
  );
}
