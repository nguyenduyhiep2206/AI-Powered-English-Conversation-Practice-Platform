"use client";

import type { JSX } from "react";
import { ArrowRight, Check, Loader2, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { SkillQuizQuestion } from "@/lib/quiz";

const PRIMARY_BTN =
  "h-11 rounded-2xl bg-[#FF8A6B] font-semibold text-white hover:bg-[#F47A5A]";

const SELECTED_OPTION =
  "border-[#FF8A6B] bg-[#FFF0E8] text-[#2A2438]";

const UNSELECTED_OPTION =
  "border-border bg-background/40 text-muted-foreground hover:border-[#FF8A6B]/40 hover:text-foreground";

export function QuizCard(props: {
  question: SkillQuizQuestion;
  index: number;
  total: number;
  answer: string;
  onAnswerChange: (value: string) => void;
  feedback: {
    correct: boolean;
    explanation: string | null;
  } | null;
  submitting: boolean;
  error: string | null;
  readyToComplete: boolean;
  onSubmit: () => void;
  onNext: () => void;
  onBackToPath: () => void;
}): JSX.Element {
  const {
    question,
    index,
    total,
    answer,
    onAnswerChange,
    feedback,
    submitting,
    error,
    readyToComplete,
    onSubmit,
    onNext,
    onBackToPath,
  } = props;

  return (
    <section className="rounded-xl border border-border bg-card/60 p-6">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Badge variant="secondary">
          Question {index + 1} / {total}
        </Badge>
        <Badge variant="outline">{question.question_type}</Badge>
        {question.toeic_part ? (
          <Badge variant="outline">{question.toeic_part.toUpperCase()}</Badge>
        ) : null}
      </div>

      {question.passage ? (
        <div className="mb-5 border-l-2 border-primary/40 pl-4">
          <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
            Passage
          </p>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-foreground/90">
            {question.passage}
          </p>
        </div>
      ) : null}

      <p className="text-base font-medium leading-relaxed">
        {question.question_type === "fix_grammar"
          ? "Fix the sentence"
          : question.stem}
      </p>
      {question.question_type === "fix_grammar" ? (
        <p className="mt-3 rounded-lg border border-border bg-muted/40 px-4 py-3 text-sm leading-relaxed text-foreground/90">
          {question.stem}
        </p>
      ) : null}

      {feedback ? (
        <div className="mt-5 space-y-4">
          <div
            className={`flex items-start gap-2 rounded-lg border px-4 py-3 text-sm ${
              feedback.correct
                ? "border-[#8CC6E8]/45 bg-[#E8F4FB] text-[#3D7FA0]"
                : "border-[#FF8A6B]/30 bg-[#FFF0EE] text-[#C24B3A]"
            }`}
          >
            {feedback.correct ? (
              <Check className="mt-0.5 h-4 w-4 shrink-0" />
            ) : (
              <X className="mt-0.5 h-4 w-4 shrink-0" />
            )}
            <div>
              <p>{feedback.correct ? "Correct" : "Not quite"}</p>
              {feedback.explanation ? (
                <p className="mt-1 text-muted-foreground">
                  {feedback.explanation}
                </p>
              ) : null}
            </div>
          </div>

          {readyToComplete ? (
            <Button
              type="button"
              size="lg"
              className={`w-full ${PRIMARY_BTN}`}
              onClick={onBackToPath}
            >
              Mastery reached — back to path
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          ) : (
            <Button
              type="button"
              size="lg"
              className={`w-full ${PRIMARY_BTN}`}
              onClick={onNext}
            >
              Next question
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          )}
        </div>
      ) : (
        <>
          {question.question_type === "mcq" && question.options?.length ? (
            <div className="mt-5 grid gap-2">
              {question.options.map((option) => {
                const selected = answer === option;
                return (
                  <button
                    key={option}
                    type="button"
                    onClick={() => onAnswerChange(option)}
                    className={`rounded-lg border px-4 py-3 text-left text-sm transition-colors ${
                      selected ? SELECTED_OPTION : UNSELECTED_OPTION
                    }`}
                  >
                    {option}
                  </button>
                );
              })}
            </div>
          ) : question.question_type === "cloze" ? (
            <div className="mt-5 space-y-3">
              {question.options?.length ? (
                <div className="grid gap-2">
                  {question.options.map((option) => {
                    const selected = answer === option;
                    return (
                      <button
                        key={option}
                        type="button"
                        onClick={() => onAnswerChange(option)}
                        className={`rounded-lg border px-4 py-3 text-left text-sm transition-colors ${
                          selected ? SELECTED_OPTION : UNSELECTED_OPTION
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
                  onChange={(e) => onAnswerChange(e.target.value)}
                  placeholder="Fill the blank"
                />
              )}
            </div>
          ) : (
            <Input
              className="mt-5"
              value={answer}
              onChange={(e) => onAnswerChange(e.target.value)}
              placeholder={
                question.question_type === "fix_grammar"
                  ? "Type the corrected sentence"
                  : "Your answer"
              }
            />
          )}

          {error ? (
            <p className="mt-4 text-sm text-destructive" role="alert">
              {error}
            </p>
          ) : null}

          <Button
            type="button"
            size="lg"
            className={`mt-6 w-full ${PRIMARY_BTN}`}
            disabled={submitting || !answer.trim()}
            onClick={onSubmit}
          >
            {submitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Checking…
              </>
            ) : (
              "Check answer"
            )}
          </Button>
        </>
      )}
    </section>
  );
}
