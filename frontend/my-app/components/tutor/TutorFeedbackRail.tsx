"use client";

import { Lightbulb, PanelRightClose, PanelRightOpen } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { TutorFeedbackItem } from "@/lib/tutor-feedback";
import { cn } from "@/lib/utils";

type TutorFeedbackRailProps = {
  items: TutorFeedbackItem[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

function FeedbackCard({ item }: { item: TutorFeedbackItem }) {
  if (item.kind === "hint") {
    return (
      <article className="rounded-lg border border-border/60 bg-background px-3 py-2.5">
        <div className="flex items-center gap-1.5">
          <Lightbulb className="h-3.5 w-3.5 text-amber-600" />
          <Badge variant="secondary" className="text-[10px]">
            Hint
          </Badge>
        </div>
        <p className="mt-2 text-sm leading-relaxed text-foreground">
          {item.note}
        </p>
      </article>
    );
  }

  return (
    <article className="rounded-lg border border-amber-200/80 bg-amber-50/50 px-3 py-2.5 dark:border-amber-900/50 dark:bg-amber-950/20">
      <Badge variant="outline" className="border-amber-300/80 text-[10px] text-amber-900 dark:text-amber-200">
        Correction
      </Badge>
      {item.original ? (
        <p className="mt-2 text-sm text-muted-foreground line-through">
          {item.original}
        </p>
      ) : null}
      {item.corrected ? (
        <p className="mt-1 text-sm font-medium leading-relaxed text-foreground">
          {item.corrected}
        </p>
      ) : null}
      {item.note ? (
        <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
          {item.note}
        </p>
      ) : null}
    </article>
  );
}

export default function TutorFeedbackRail({
  items,
  open,
  onOpenChange,
}: TutorFeedbackRailProps) {
  if (!open) {
    return (
      <div className="pointer-events-none fixed bottom-20 right-4 z-40 sm:bottom-6">
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="pointer-events-auto shadow-sm"
          onClick={() => onOpenChange(true)}
        >
          <PanelRightOpen className="mr-1.5 h-4 w-4" />
          Show feedback
          {items.length > 0 ? (
            <span className="ml-1.5 rounded-md bg-muted px-1.5 py-0.5 text-[10px] font-semibold tabular-nums">
              {items.length}
            </span>
          ) : null}
        </Button>
      </div>
    );
  }

  return (
    <aside
      className={cn(
        "fixed inset-y-0 right-0 z-40 flex w-[min(100vw,20rem)] flex-col border-l border-border/60 bg-background shadow-lg",
        "lg:static lg:z-0 lg:w-72 lg:shrink-0 lg:shadow-none",
      )}
    >
      <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
        <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Feedback
        </p>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-label="Hide feedback"
          onClick={() => onOpenChange(false)}
        >
          <PanelRightClose className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {items.length === 0 ? (
          <p className="text-sm leading-relaxed text-muted-foreground">
            Corrections and hints from this session will show up here.
          </p>
        ) : (
          items.map((item) => <FeedbackCard key={item.id} item={item} />)
        )}
      </div>
    </aside>
  );
}
