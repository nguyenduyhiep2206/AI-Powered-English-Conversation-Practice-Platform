"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type { WeakSkill } from "@/lib/roadmap";
import { cn } from "@/lib/utils";

type Props = {
  skills: WeakSkill[];
  level: string | null;
};

export function WeakSkillsReview({ skills, level }: Props) {
  if (skills.length === 0) return null;

  return (
    <section className="mt-10 rounded-[2.5rem] border border-[#E9D7C9] bg-white/75 px-5 py-6 shadow-[0_24px_60px_-40px_rgba(31,27,21,0.35)] sm:px-6">
      <h2 className="text-xl font-semibold tracking-tight text-[#1F1B15]">
        Strengthen weak skills
      </h2>
      <p className="mt-1.5 max-w-md text-[0.9375rem] leading-relaxed text-[#6B6258]">
        {level
          ? `Below 70% mastery at ${level}. Open a skill to practice again.`
          : "Below 70% mastery. Open a skill to practice again."}
      </p>
      <ul className="mt-5 space-y-2">
        {skills.map((skill) => {
          const pct = Math.round(skill.mastery * 100);
          return (
            <li key={skill.skill_id}>
              <Link
                href={`/dashboard/practice/${skill.skill_id}`}
                className="group flex items-center gap-3 rounded-2xl bg-[#FFFAF5] px-4 py-3.5 ring-1 ring-[#E9D7C9] transition-[background-color,box-shadow] hover:bg-white hover:shadow-[0_8px_20px_-14px_rgba(31,27,21,0.35)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-3">
                    <span className="truncate text-[0.875rem] font-semibold text-[#1F1B15]">
                      {skill.title}
                    </span>
                    <span className="shrink-0 text-[0.75rem] font-semibold tabular-nums text-[#9A3412]">
                      {pct}%
                    </span>
                  </div>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[#FFE8D6]">
                    <div
                      className={cn(
                        "h-full rounded-full",
                        pct >= 70 ? "bg-[#2F9E44]" : "bg-[#E85D04]",
                      )}
                      style={{ width: `${Math.min(100, pct)}%` }}
                    />
                  </div>
                </div>
                <ArrowRight
                  className="h-4 w-4 shrink-0 text-[#A89F94] transition-colors group-hover:text-[#E85D04]"
                  aria-hidden
                />
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
