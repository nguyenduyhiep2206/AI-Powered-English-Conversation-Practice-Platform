"use client";

import { useEffect, useMemo, useState, type JSX } from "react";
import { ArrowRight, Check, Loader2, Undo2, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { SkillQuizQuestion } from "@/lib/quiz";

function quizTypeLabel(type: string): string {
  switch (type) {
    case "mcq":
      return "Multiple choice";
    case "cloze":
      return "Fill in the blank";
    case "fix_grammar":
      return "Fix the sentence";
    case "sentence_build":
      return "Build the sentence";
    case "matching":
      return "Match";
    case "multi_select":
      return "Choose all that apply";
    default:
      return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

/** TOEIC-style Directions + how to interact — shown above the stem. */
function learnerGuide(
  type: string,
  itemKind: string | null | undefined
): { directions: string; howTo: string } {
  if (type === "cloze") {
    return {
      directions:
        "A word or phrase is missing. Type the correct form of the word in parentheses.",
      howTo: "Type your answer in the box, then Check.",
    };
  }
  if (type === "fix_grammar") {
    return {
      directions: "The sentence below has a mistake. Rewrite it correctly.",
      howTo: "Type the full corrected sentence, then Check.",
    };
  }
  if (type === "sentence_build") {
    return {
      directions: "Build a correct English sentence using the word chips.",
      howTo: "Tap chips in order to build the sentence. Tap a chip again to remove it.",
    };
  }
  if (type === "matching") {
    return {
      directions: "Match each item on the left with the best item on the right.",
      howTo: "Tap a left item, then tap its match on the right.",
    };
  }
  if (type === "multi_select") {
    return {
      directions: "More than one option may be correct. Select every answer that fits.",
      howTo: "Tap all correct options, then Check.",
    };
  }
  // mcq (+ item_kind variants)
  switch (itemKind) {
    case "spot_error":
      return {
        directions:
          "Four parts of the sentence are underlined and labeled (A)–(D). Choose the incorrect part.",
        howTo: "Tap one answer (A–D), then Check.",
      };
    case "dialogue_complete":
      return {
        directions:
          "Read the short dialogue. Choose the best reply or completion for the blank.",
        howTo: "Tap one answer, then Check.",
      };
    case "paraphrase":
      return {
        directions:
          "Choose the option that means nearly the same as the given sentence or phrase.",
        howTo: "Tap one answer, then Check.",
      };
    case "reading_target":
      return {
        directions:
          "Read the short text (if shown), then answer the question. Only one answer is correct.",
        howTo: "Tap one answer, then Check.",
      };
    case "contrast":
      return {
        directions:
          "Choose the form that fits the blank (word form, tense, article, etc.).",
        howTo: "Tap one answer, then Check.",
      };
    default:
      return {
        directions:
          "A word or phrase is missing from the sentence. Choose the best answer to complete it.",
        howTo: "Tap one answer, then Check.",
      };
  }
}

/** Strip redundant task prefixes the model sometimes stuffs into stem. */
function displayStem(type: string, stem: string): string {
  let text = stem.trim();
  if (type === "multi_select") {
    text = text.replace(
      /^(choose all that apply\.?\s*)+/i,
      "",
    );
  }
  if (type === "mcq" || type === "cloze") {
    text = text.replace(
      /^(choose the (best |correct )?answer\.?\s*)+/i,
      "",
    );
  }
  return text.trim() || stem.trim();
}

function optionLetter(index: number): string {
  return String.fromCharCode(65 + index); // A, B, C, …
}

type StemMark = { start: number; end: number; letter: string; text: string };

function findSpotErrorMarks(stem: string, options: string[]): StemMark[] {
  const occupied: Array<{ start: number; end: number }> = [];
  const marks: StemMark[] = [];

  const overlaps = (start: number, end: number): boolean =>
    occupied.some((range) => start < range.end && end > range.start);

  options.forEach((option, index) => {
    const needle = option.trim();
    if (!needle) return;

    const escaped = needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const re = new RegExp(`(^|[^A-Za-z0-9])(${escaped})(?=[^A-Za-z0-9]|$)`, "i");
    const match = re.exec(stem);
    if (!match || match.index == null) return;

    const prefixLen = match[1]?.length ?? 0;
    const start = match.index + prefixLen;
    const end = start + (match[2]?.length ?? needle.length);
    if (overlaps(start, end)) return;

    occupied.push({ start, end });
    marks.push({
      start,
      end,
      letter: optionLetter(index),
      text: stem.slice(start, end),
    });
  });

  return marks.sort((a, b) => a.start - b.start);
}

function SpotErrorStem(props: {
  stem: string;
  options: string[];
}): JSX.Element {
  const { stem, options } = props;
  const marks = findSpotErrorMarks(stem, options);

  if (marks.length === 0) {
    return (
      <p className="text-base font-medium leading-relaxed text-[#1F1B15] [overflow-wrap:anywhere]">
        {stem}
      </p>
    );
  }

  const parts: JSX.Element[] = [];
  let cursor = 0;
  marks.forEach((mark, index) => {
    if (mark.start > cursor) {
      parts.push(
        <span key={`t-${index}`}>{stem.slice(cursor, mark.start)}</span>,
      );
    }
    parts.push(
      <span key={`m-${index}`} className="whitespace-nowrap">
        <span className="align-super text-[0.7em] font-semibold text-[#9A3412]">
          ({mark.letter})
        </span>
        <span className="mx-0.5 border-b-2 border-[#1F1B15] font-semibold text-[#1F1B15]">
          {mark.text}
        </span>
      </span>,
    );
    cursor = mark.end;
  });
  if (cursor < stem.length) {
    parts.push(<span key="tail">{stem.slice(cursor)}</span>);
  }

  return (
    <p className="text-base font-medium leading-relaxed text-[#1F1B15] [overflow-wrap:anywhere]">
      {parts}
    </p>
  );
}

function OptionLabel(props: {
  index: number;
  children: string;
}): JSX.Element {
  return (
    <span className="flex items-start gap-2">
      <span className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-[#FFE8D6] text-[0.75rem] font-semibold text-[#9A3412] ring-1 ring-[#E85D04]/25">
        {optionLetter(props.index)}
      </span>
      <span>{props.children}</span>
    </span>
  );
}

function itemKindEyebrow(kind: string | null | undefined): string | null {
  switch (kind) {
    case "spot_error":
      return "Find the mistake";
    case "dialogue_complete":
      return "Complete the dialogue";
    default:
      return null;
  }
}

type MatchingPair = { left: string; right: string };

function parseMatchingOptions(options: string[]): MatchingPair[] {
  return options.flatMap((option) => {
    const pipe = option.indexOf("|");
    if (pipe === -1) return [];
    const left = option.slice(0, pipe).trim();
    const right = option.slice(pipe + 1).trim();
    if (!left || !right) return [];
    return [{ left, right }];
  });
}

function shuffleWithSeed<T>(items: T[], seed: number): T[] {
  const arr = [...items];
  let state = seed;
  for (let index = arr.length - 1; index > 0; index -= 1) {
    state = (state * 1103515245 + 12345) & 0x7fffffff;
    const swapIndex = state % (index + 1);
    [arr[index], arr[swapIndex]] = [arr[swapIndex], arr[index]];
  }
  return arr;
}

function serializeMatchingAnswer(pairs: Record<string, string>): string {
  return Object.keys(pairs)
    .sort((leftA, leftB) => leftA.localeCompare(leftB))
    .map((left) => `${left}=>${pairs[left]}`)
    .join(";");
}

function serializeMultiSelectAnswer(selected: string[]): string {
  return [...selected].sort((a, b) => a.localeCompare(b)).join(" | ");
}

const PRIMARY_BTN =
  "h-11 rounded-2xl bg-[#E85D04] font-semibold text-white hover:bg-[#D04F00]";

const SELECTED_OPTION =
  "border-[#E85D04] bg-[#FFE8D6] text-[#1F1B15]";

const UNSELECTED_OPTION =
  "border-[#E9D7C9] bg-[#FFFAF5] text-[#6B6258] hover:border-[#E85D04]/40 hover:text-[#1F1B15]";

const INPUT_CLASS =
  "h-11 rounded-[12px] border-[#E9D7C9] bg-[#FFFAF5] text-[0.875rem] text-[#1F1B15] placeholder:text-[#6B6258] focus-visible:border-[#E85D04] focus-visible:ring-0";

const TOKEN_CHIP =
  "inline-flex items-center rounded-xl border px-3 py-1.5 text-[0.875rem] font-medium";

function MatchingEditor(props: {
  questionId: number;
  options: string[];
  onAnswerChange: (value: string) => void;
  locked?: boolean;
}): JSX.Element {
  const { questionId, options, onAnswerChange, locked = false } = props;
  const pairs = useMemo(() => parseMatchingOptions(options), [options]);
  const leftItems = useMemo(() => pairs.map((pair) => pair.left), [pairs]);
  const rightItems = useMemo(() => pairs.map((pair) => pair.right), [pairs]);

  const shuffledLeft = shuffleWithSeed(leftItems, questionId * 17 + 3);
  const shuffledRight = shuffleWithSeed(rightItems, questionId * 31 + 7);

  const [selectedLeft, setSelectedLeft] = useState<string | null>(null);
  const [matches, setMatches] = useState<Record<string, string>>({});

  useEffect(() => {
    setSelectedLeft(null);
    setMatches({});
  }, [questionId]);

  useEffect(() => {
    const allMatched = leftItems.every((left) => matches[left]);
    onAnswerChange(allMatched ? serializeMatchingAnswer(matches) : "");
  }, [leftItems, matches, onAnswerChange]);

  const matchedRights = new Set(Object.values(matches));

  function handleLeftClick(left: string): void {
    if (locked) return;
    if (matches[left]) {
      setMatches((prev) => {
        const next = { ...prev };
        delete next[left];
        return next;
      });
    }
    setSelectedLeft(left);
  }

  function handleRightClick(right: string): void {
    if (locked) return;
    if (!selectedLeft || matchedRights.has(right)) return;
    setMatches((prev) => ({ ...prev, [selectedLeft]: right }));
    setSelectedLeft(null);
  }

  const matchedEntries = Object.entries(matches).sort(([leftA], [leftB]) =>
    leftA.localeCompare(leftB),
  );

  return (
    <div className="mt-5 space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-2">
          <p className="text-[0.75rem] font-medium uppercase tracking-[0.14em] text-[#6B6258]">
            Words
          </p>
          {shuffledLeft.map((left) => {
            const paired = matches[left];
            const isSelected = selectedLeft === left;
            return (
              <button
                key={left}
                type="button"
                disabled={locked}
                onClick={() => handleLeftClick(left)}
                className={`w-full rounded-[12px] border px-4 py-3 text-left text-[0.875rem] transition-colors ${
                  isSelected || paired ? SELECTED_OPTION : UNSELECTED_OPTION
                } ${locked ? "cursor-default" : ""}`}
              >
                {left}
              </button>
            );
          })}
        </div>

        <div className="space-y-2">
          <p className="text-[0.75rem] font-medium uppercase tracking-[0.14em] text-[#6B6258]">
            Meanings
          </p>
          {shuffledRight.map((right) => {
            const isUsed = matchedRights.has(right);
            const isTarget = Boolean(selectedLeft) && !isUsed && !locked;
            return (
              <button
                key={right}
                type="button"
                disabled={locked || !isTarget}
                onClick={() => handleRightClick(right)}
                className={`w-full rounded-[12px] border px-4 py-3 text-left text-[0.875rem] transition-colors ${
                  isUsed
                    ? "border-[#E9D7C9] bg-[#FFFAF5] text-[#6B6258] opacity-60"
                    : isTarget
                      ? UNSELECTED_OPTION
                      : "border-[#E9D7C9] bg-[#FFFAF5] text-[#6B6258] opacity-80"
                } ${locked ? "cursor-default" : ""}`}
              >
                {right}
              </button>
            );
          })}
        </div>
      </div>

      <div className="rounded-[12px] border border-[#E9D7C9] bg-[#FFFAF5] px-4 py-3">
        <p className="text-[0.75rem] font-medium uppercase tracking-[0.14em] text-[#6B6258]">
          Your matches
        </p>
        <div className="mt-2 min-h-[2rem] space-y-1">
          {matchedEntries.length === 0 ? (
            <p className="text-sm text-[#6B6258]">
              Tap a word, then tap its meaning
            </p>
          ) : (
            matchedEntries.map(([left, right]) => (
              <p key={left} className="text-sm text-[#1F1B15]">
                <span className="font-medium">{left}</span>
                <span className="mx-2 text-[#6B6258]">→</span>
                <span>{right}</span>
              </p>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function MultiSelectEditor(props: {
  questionId: number;
  options: string[];
  onAnswerChange: (value: string) => void;
  locked?: boolean;
}): JSX.Element {
  const { questionId, options, onAnswerChange, locked = false } = props;
  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => {
    setSelected(new Set());
  }, [questionId]);

  useEffect(() => {
    onAnswerChange(serializeMultiSelectAnswer([...selected]));
  }, [selected, onAnswerChange]);

  function toggleOption(option: string): void {
    if (locked) return;
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(option)) {
        next.delete(option);
      } else {
        next.add(option);
      }
      return next;
    });
  }

  return (
    <div className="mt-5 grid gap-2">
      {options.map((option, index) => {
        const isSelected = selected.has(option);
        return (
          <button
            key={option}
            type="button"
            disabled={locked}
            onClick={() => toggleOption(option)}
            className={`rounded-[12px] border px-4 py-3 text-left text-[0.875rem] transition-colors ${
              isSelected ? SELECTED_OPTION : UNSELECTED_OPTION
            } ${locked ? "cursor-default" : ""}`}
          >
            <OptionLabel index={index}>{option}</OptionLabel>
          </button>
        );
      })}
    </div>
  );
}

function SentenceBuildEditor(props: {
  questionId: number;
  options: string[];
  onAnswerChange: (value: string) => void;
  locked?: boolean;
}): JSX.Element {
  const { questionId, options, onAnswerChange, locked = false } = props;
  const [builtIndices, setBuiltIndices] = useState<number[]>([]);

  useEffect(() => {
    setBuiltIndices([]);
  }, [questionId]);

  useEffect(() => {
    onAnswerChange(builtIndices.map((index) => options[index]).join(" "));
  }, [builtIndices, options, onAnswerChange]);

  const builtTokens = builtIndices.map((index) => options[index]);
  const usedIndices = new Set(builtIndices);

  return (
    <div className="mt-5 space-y-4">
      <div className="rounded-[12px] border border-[#E9D7C9] bg-[#FFFAF5] px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-[0.75rem] font-medium uppercase tracking-[0.14em] text-[#6B6258]">
            Your sentence
          </p>
          {!locked && builtIndices.length > 0 ? (
            <button
              type="button"
              onClick={() => setBuiltIndices((prev) => prev.slice(0, -1))}
              className="inline-flex items-center gap-1 text-[0.8125rem] font-medium text-[#6B6258] transition-colors hover:text-[#1F1B15]"
            >
              <Undo2 className="h-3.5 w-3.5" aria-hidden />
              Undo
            </button>
          ) : null}
        </div>
        <div className="mt-2 flex min-h-[2.25rem] flex-wrap items-center gap-2">
          {builtTokens.length === 0 ? (
            <span className="text-sm text-[#6B6258]">
              Tap words below to build the sentence
            </span>
          ) : (
            builtTokens.map((token, position) => (
              <span
                key={`${position}-${builtIndices[position]}`}
                className={`${TOKEN_CHIP} ${SELECTED_OPTION}`}
              >
                {token}
              </span>
            ))
          )}
        </div>
      </div>

      {!locked ? (
        <div className="flex flex-wrap gap-2">
          {options.map((token, index) => {
            if (usedIndices.has(index)) return null;
            return (
              <button
                key={index}
                type="button"
                onClick={() => setBuiltIndices((prev) => [...prev, index])}
                className={`${TOKEN_CHIP} transition-colors ${UNSELECTED_OPTION}`}
              >
                {token}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

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

  const kindEyebrow = itemKindEyebrow(question.item_kind);
  const locked = Boolean(feedback);
  const guide = learnerGuide(question.question_type, question.item_kind);

  function renderAnswerInput(): JSX.Element | null {
    if (question.question_type === "mcq" && question.options?.length) {
      return (
        <div className="mt-5 grid gap-2">
          {question.options.map((option, optionIndex) => {
            const selected = answer === option;
            return (
              <button
                key={option}
                type="button"
                disabled={locked}
                onClick={() => onAnswerChange(option)}
                className={`rounded-[12px] border px-4 py-3 text-left text-[0.875rem] transition-colors ${
                  selected ? SELECTED_OPTION : UNSELECTED_OPTION
                } ${locked ? "cursor-default" : ""}`}
              >
                <OptionLabel index={optionIndex}>{option}</OptionLabel>
              </button>
            );
          })}
        </div>
      );
    }

    if (question.question_type === "cloze") {
      return (
        <Input
          className={`mt-5 ${INPUT_CLASS}`}
          value={answer}
          disabled={locked}
          onChange={(e) => onAnswerChange(e.target.value)}
          placeholder="Type the missing word or phrase"
          autoComplete="off"
        />
      );
    }

    if (question.question_type === "sentence_build" && question.options?.length) {
      return (
        <SentenceBuildEditor
          questionId={question.id}
          options={question.options}
          onAnswerChange={onAnswerChange}
          locked={locked}
        />
      );
    }

    if (question.question_type === "matching" && question.options?.length) {
      return (
        <MatchingEditor
          questionId={question.id}
          options={question.options}
          onAnswerChange={onAnswerChange}
          locked={locked}
        />
      );
    }

    if (question.question_type === "multi_select" && question.options?.length) {
      return (
        <MultiSelectEditor
          questionId={question.id}
          options={question.options}
          onAnswerChange={onAnswerChange}
          locked={locked}
        />
      );
    }

    return (
      <Input
        className={`mt-5 ${INPUT_CLASS}`}
        value={answer}
        disabled={locked}
        onChange={(e) => onAnswerChange(e.target.value)}
        placeholder={
          question.question_type === "fix_grammar"
            ? "Type the full corrected sentence"
            : "Type your answer"
        }
      />
    );
  }

  return (
    <section className="rounded-[2.5rem] border border-[#E9D7C9] bg-white/85 p-6 shadow-[0_24px_60px_-40px_rgba(31,27,21,0.45)] sm:p-7">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="inline-flex min-h-8 items-center rounded-2xl bg-[#FFE8D6] px-3 text-[0.75rem] font-medium text-[#9A3412] ring-1 ring-[#E85D04]/25">
          Question {index + 1} / {total}
        </span>
        <span className="inline-flex min-h-8 items-center rounded-2xl bg-[#FFFAF5] px-3 text-[0.75rem] font-medium text-[#6B6258] ring-1 ring-[#E9D7C9]">
          {quizTypeLabel(question.question_type)}
        </span>
        {kindEyebrow ? (
          <span className="inline-flex min-h-8 items-center rounded-2xl bg-[#D8F3DC] px-3 text-[0.75rem] font-medium text-[#2F9E44] ring-1 ring-[#0D9488]/35">
            {kindEyebrow}
          </span>
        ) : null}
        {question.toeic_part ? (
          <span className="inline-flex min-h-8 items-center rounded-2xl bg-[#FFFAF5] px-3 text-[0.75rem] font-medium text-[#6B6258] ring-1 ring-[#E9D7C9]">
            {`TOEIC Part ${question.toeic_part.replace(/^r/i, "").toUpperCase()}`}
          </span>
        ) : null}
      </div>

      {question.passage ? (
        <div className="mb-5 rounded-2xl bg-[#FFFAF5] px-4 py-3 ring-1 ring-[#E9D7C9]">
          <p className="text-[0.75rem] font-medium uppercase tracking-[0.14em] text-[#6B6258]">
            Passage
          </p>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-[#1F1B15]">
            {question.passage}
          </p>
        </div>
      ) : null}

      <div className="mb-4 rounded-2xl bg-[#FFFAF5] px-4 py-3 ring-1 ring-[#E9D7C9]">
        <p className="text-[0.75rem] font-medium uppercase tracking-[0.14em] text-[#6B6258]">
          Directions
        </p>
        <p className="mt-1.5 text-sm leading-relaxed text-[#1F1B15]">
          {guide.directions}
        </p>
        <p className="mt-2 text-[0.8125rem] leading-relaxed text-[#6B6258]">
          {guide.howTo}
        </p>
      </div>

      {question.question_type === "fix_grammar" ? (
        <>
          <p className="text-base font-medium leading-relaxed text-[#1F1B15]">
            Incorrect sentence
          </p>
          <p className="mt-3 rounded-[12px] border border-[#E9D7C9] bg-[#FFFAF5] px-4 py-3 text-sm leading-relaxed text-[#1F1B15] [overflow-wrap:anywhere]">
            {question.stem}
          </p>
        </>
      ) : question.item_kind === "spot_error" &&
        question.options &&
        question.options.length > 0 ? (
        <SpotErrorStem
          stem={displayStem(question.question_type, question.stem)}
          options={question.options}
        />
      ) : (
        <p className="text-base font-medium leading-relaxed text-[#1F1B15] [overflow-wrap:anywhere]">
          {displayStem(question.question_type, question.stem)}
        </p>
      )}

      {renderAnswerInput()}

      {feedback ? (
        <div className="mt-5 space-y-4">
          <div
            className={`flex items-start gap-2 rounded-lg border px-4 py-3 text-sm ${
              feedback.correct
                ? "border-[#2F9E44]/40 bg-[#D8F3DC] text-[#2F9E44]"
                : "border-[#BE123C]/25 bg-[#FFE4E6] text-[#BE123C]"
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
                <p className="mt-1 text-[0.8125rem] text-[#6B6258]">
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
              Mastery reached · back to path
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
          {error ? (
            <p className="mt-4 text-sm text-[#BE123C]" role="alert">
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
