"use client";

import Link from "next/link";
import type { WeakSkill } from "@/lib/roadmap";

type Props = {
  skills: WeakSkill[];
  level: string | null;
};

export function WeakSkillsReview({ skills, level }: Props) {
  if (skills.length === 0) return null;

  return (
    <section className="ef-fade-up mt-12 rounded-xl border border-border/60 bg-card/30 px-5 py-6">
      <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
        Review
      </p>
      <h2 className="mt-1 text-lg font-semibold tracking-tight text-foreground">
        Strengthen weak skills
      </h2>
      <p className="mt-1.5 max-w-md text-sm leading-relaxed text-muted-foreground">
        {level
          ? `Skills at ${level} you've practiced but haven't reached 70% mastery yet.`
          : "Skills you've practiced but haven't reached 70% mastery yet."}
      </p>
      <ul className="mt-5 space-y-2">
        {skills.map((skill) => {
          const pct = Math.round(skill.mastery * 100);
          return (
            <li key={skill.skill_id}>
              <Link
                href={`/dashboard/practice/${skill.skill_id}`}
                className="flex items-center justify-between gap-3 rounded-lg border border-border/50 bg-background/60 px-3.5 py-3 text-sm transition-colors hover:border-border hover:bg-muted/20"
              >
                <span className="font-medium text-foreground">{skill.title}</span>
                <span className="shrink-0 tabular-nums text-muted-foreground">
                  {pct}%
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
