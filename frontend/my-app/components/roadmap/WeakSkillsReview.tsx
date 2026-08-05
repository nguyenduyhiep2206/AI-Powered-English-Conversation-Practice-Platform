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
    <section className="mt-12 rounded-[1.75rem] bg-white px-5 py-6 shadow-[0_12px_36px_rgba(42,36,56,0.05)] ring-1 ring-[#2A2438]/06 sm:px-6">
      <h2 className="text-xl font-semibold tracking-tight text-[#2A2438]">
        Strengthen weak skills
      </h2>
      <p className="mt-1.5 max-w-md text-[0.9375rem] leading-relaxed text-[#6B6478]">
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
                className="group flex items-center gap-3 rounded-2xl bg-[#FFFCF9] px-4 py-3.5 ring-1 ring-[#EDE6E0] transition-[background-color,box-shadow] hover:bg-[#FFF8F4] hover:shadow-[0_4px_14px_rgba(42,36,56,0.05)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#FF8A6B]"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-3">
                    <span className="truncate text-[0.875rem] font-semibold text-[#2A2438]">
                      {skill.title}
                    </span>
                    <span className="shrink-0 text-[0.75rem] font-semibold tabular-nums text-[#6B5B9A]">
                      {pct}%
                    </span>
                  </div>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[#FFF0E8]">
                    <div
                      className={cn(
                        "h-full rounded-full",
                        pct >= 70 ? "bg-[#8CC6E8]" : "bg-[#FF8A6B]",
                      )}
                      style={{ width: `${Math.min(100, pct)}%` }}
                    />
                  </div>
                </div>
                <ArrowRight
                  className="h-4 w-4 shrink-0 text-[#B0A9B8] transition-colors group-hover:text-[#FF8A6B]"
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
