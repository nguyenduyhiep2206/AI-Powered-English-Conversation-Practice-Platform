"use client";

import { Pencil } from "lucide-react";
import { isPresetAvatar } from "@/lib/avatar-presets";
import { cn } from "@/lib/utils";

function initialLetter(name: string): string {
  return (name.charAt(0) || "U").toUpperCase();
}

type ProfileHeroProps = {
  name: string;
  avatarUrl: string | null;
  onEdit: () => void;
  size?: "md" | "lg";
  subtitle?: string | null;
};

export default function ProfileHero({
  name,
  avatarUrl,
  onEdit,
  size = "lg",
  subtitle,
}: ProfileHeroProps) {
  const large = size === "lg";

  return (
    <section className="relative overflow-hidden rounded-[1.75rem] bg-white px-6 py-10 text-center shadow-[0_18px_50px_rgba(31,27,21,0.06)] ring-1 ring-[#1F1B15]/06 sm:px-8">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 70% 60% at 50% 0%, rgba(232, 93, 4, 0.14), transparent 58%), radial-gradient(ellipse 45% 40% at 90% 100%, rgba(13, 148, 136, 0.1), transparent 55%)",
        }}
      />

      <div className="relative">
        <div
          className={cn(
            "mx-auto flex items-center justify-center overflow-hidden rounded-full bg-[#E85D04] font-semibold text-white shadow-[0_10px_28px_rgba(232,93,4,0.28)] ring-4 ring-[#FFE8D6]",
            large ? "h-28 w-28 text-[1.75rem]" : "h-24 w-24 text-[1.25rem]",
          )}
        >
          {isPresetAvatar(avatarUrl) ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={avatarUrl!}
              alt=""
              className="h-full w-full object-cover"
            />
          ) : (
            initialLetter(name)
          )}
        </div>

        <p
          className={cn(
            "mt-5 font-semibold tracking-tight text-[#1F1B15]",
            large
              ? "text-[1.75rem] md:text-[2rem]"
              : "text-[1.25rem] md:text-[1.75rem]",
          )}
        >
          {name}
        </p>
        {subtitle ? (
          <p className="mt-1.5 text-[0.875rem] text-[#8A8178]">{subtitle}</p>
        ) : null}

        <button
          type="button"
          onClick={onEdit}
          className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-2xl bg-[#FFFAF5] px-4 text-[0.875rem] font-semibold text-[#9A3412] ring-1 ring-[#E9D7C9] transition-[background-color,transform] duration-200 hover:bg-[#FFE8D6] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04] active:scale-[0.98]"
        >
          <Pencil className="h-4 w-4" aria-hidden />
          Edit profile
        </button>
      </div>
    </section>
  );
}
