"use client";

import { cn } from "@/lib/utils";
import type { PlacementFormItem } from "@/lib/placement";

export const R5_PAGE_SIZE = 10;
export const OPTION_LETTERS = ["A", "B", "C", "D", "E", "F"] as const;

export type ReadingPageItem = PlacementFormItem & { globalIndex: number };

export type ReadingPage = {
  key: string;
  label: string;
  passage: string | null;
  mediaUrl: string | null;
  part: string;
  items: ReadingPageItem[];
};

export type LocalDraft = {
  reading?: Record<string, string>;
  writingTextById?: Record<string, string>;
  markedIds?: number[];
};

export function draftKey(attemptId: number) {
  return `placement-draft-${attemptId}`;
}

export function loadDraft(attemptId: number): LocalDraft {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(draftKey(attemptId));
    if (!raw) return {};
    const parsed = JSON.parse(raw) as LocalDraft;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

export function saveDraft(attemptId: number, draft: LocalDraft) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(draftKey(attemptId), JSON.stringify(draft));
  } catch {
    /* ignore quota */
  }
}

export function clearDraft(attemptId: number) {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(draftKey(attemptId));
  } catch {
    /* ignore */
  }
}

export function formatTime(sec: number | null) {
  if (sec == null) return "--:--";
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function savedAnswersToMap(
  saved?: Record<string, string> | null,
): Record<number, string> {
  const out: Record<number, string> = {};
  if (!saved) return out;
  for (const [k, v] of Object.entries(saved)) {
    const id = Number(k);
    if (Number.isFinite(id) && v) out[id] = v;
  }
  return out;
}

export function blankIndexFromStem(stem?: string | null): number {
  if (!stem) return Number.MAX_SAFE_INTEGER;
  const m = stem.match(/blank\s*\((\d+)\)/i);
  return m ? Number(m[1]) : Number.MAX_SAFE_INTEGER;
}

export function buildReadingPages(
  items: PlacementFormItem[],
  passages: Record<string, { body?: string; media_url?: string | null }>,
): ReadingPage[] {
  const pages: ReadingPage[] = [];
  let i = 0;
  let r5Buffer: PlacementFormItem[] = [];
  let globalIndex = 1;
  const seenIds = new Set<number>();
  const uniqueItems = items.filter((it) => {
    if (seenIds.has(it.id)) return false;
    seenIds.add(it.id);
    return true;
  });

  const withIndex = (chunk: PlacementFormItem[]): ReadingPageItem[] =>
    chunk.map((it) => {
      const indexed = { ...it, globalIndex };
      globalIndex += 1;
      return indexed;
    });

  const flushR5 = () => {
    while (r5Buffer.length > 0) {
      const chunk = r5Buffer.splice(0, R5_PAGE_SIZE);
      pages.push({
        key: `r5-${pages.length}`,
        label: `Part 5 · Incomplete sentences (${chunk.length})`,
        passage: null,
        mediaUrl: null,
        part: "r5",
        items: withIndex(chunk),
      });
    }
  };

  while (i < uniqueItems.length) {
    const item = uniqueItems[i];
    const part = item.toeic_part ?? "";
    if (part === "r5" || !item.passage_id) {
      r5Buffer.push(item);
      i += 1;
      continue;
    }
    flushR5();
    const pid = item.passage_id;
    const group: PlacementFormItem[] = [];
    while (i < uniqueItems.length && uniqueItems[i].passage_id === pid) {
      group.push(uniqueItems[i]);
      i += 1;
    }
    group.sort(
      (a, b) =>
        blankIndexFromStem(a.stem) - blankIndexFromStem(b.stem) || a.id - b.id,
    );
    const passageMeta = passages[String(pid)];
    pages.push({
      key: `p-${pid}-${pages.length}`,
      label: `Part ${(part || "R").toUpperCase()} · Passage set (${group.length} Q)`,
      passage: passageMeta?.body ?? null,
      mediaUrl: passageMeta?.media_url ?? null,
      part: part || "r",
      items: withIndex(group),
    });
  }
  flushR5();
  return pages;
}

export function firstIncompleteReadingPage(
  pages: ReadingPage[],
  answers: Record<number, string>,
): number {
  for (let i = 0; i < pages.length; i += 1) {
    if (pages[i].items.some((it) => !answers[it.id])) return i;
  }
  return Math.max(0, pages.length - 1);
}

export function firstIncompleteWritingIndex(
  items: PlacementFormItem[],
  answers: Record<number, string>,
): number {
  for (let i = 0; i < items.length; i += 1) {
    if (!answers[items[i].id]) return i;
  }
  return Math.max(0, items.length - 1);
}

export function pageIndexForItem(
  pages: ReadingPage[],
  itemId: number,
): number {
  for (let i = 0; i < pages.length; i += 1) {
    if (pages[i].items.some((it) => it.id === itemId)) return i;
  }
  return 0;
}

export function countWords(text: string): number {
  const trimmed = text.trim();
  if (!trimmed) return 0;
  return trimmed.split(/\s+/).length;
}

export function optionClass(selected: boolean): string {
  return cn(
    "flex w-full items-start gap-2.5 rounded-[1rem] px-3.5 py-3 text-left text-[0.875rem] transition-[background-color,box-shadow] duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]",
    selected
      ? "bg-[#FFE8D6] font-semibold text-[#1F1B15] shadow-[0_4px_14px_rgba(232,93,4,0.18)] ring-2 ring-[#E85D04]"
      : "bg-[#FFFAF5] text-[#6B6258] ring-1 ring-[#E9D7C9] hover:bg-white hover:text-[#1F1B15]",
  );
}

export function primaryBtnClass(extra?: string): string {
  return cn(
    "inline-flex h-11 items-center justify-center rounded-[1rem] bg-[#E85D04] px-5 text-[0.875rem] font-semibold text-white shadow-[0_10px_24px_rgba(232,93,4,0.28)] transition-[transform,background-color] hover:bg-[#D04F00] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04] active:scale-[0.98] disabled:opacity-60",
    extra,
  );
}

export function secondaryBtnClass(extra?: string): string {
  return cn(
    "inline-flex h-11 items-center justify-center rounded-[1rem] bg-white px-5 text-[0.875rem] font-semibold text-[#9A3412] ring-1 ring-[#E9D7C9] transition-colors hover:bg-[#FFFAF5] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04] disabled:opacity-60",
    extra,
  );
}
