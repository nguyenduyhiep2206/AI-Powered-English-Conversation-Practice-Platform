"use client";

import { useEffect, type ReactNode } from "react";

type Props = {
  open: boolean;
  title?: string;
  onClose: () => void;
  /** When false, backdrop / X / Escape do not close the window. */
  dismissible?: boolean;
  children: ReactNode;
};

export default function LessonContentWindow({
  open,
  title,
  onClose,
  dismissible = true,
  children,
}: Props) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && dismissible) onClose();
    }
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose, dismissible]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      <button
        type="button"
        aria-label="Close"
        className="absolute inset-0 bg-[#2F3437]/35"
        onClick={() => {
          if (dismissible) onClose();
        }}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title || "Lesson content"}
        className="relative z-10 flex max-h-[min(88vh,840px)] w-full max-w-2xl flex-col overflow-hidden rounded-[12px] border border-[#EAEAEA] bg-white"
      >
        <div className="flex shrink-0 items-start justify-between gap-3 border-b border-[#EAEAEA] px-5 py-4">
          <div className="min-w-0">
            {title ? (
              <h2 className="truncate text-lg font-semibold tracking-tight text-[#2F3437]">
                {title}
              </h2>
            ) : null}
          </div>
          {dismissible ? (
            <button
              type="button"
              onClick={onClose}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] border border-[#EAEAEA] text-[#787774] transition-colors hover:bg-[#F7F6F3] hover:text-[#2F3437]"
              aria-label="Close window"
            >
              <span className="text-lg leading-none" aria-hidden>
                ×
              </span>
            </button>
          ) : null}
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">{children}</div>
      </div>
    </div>
  );
}
