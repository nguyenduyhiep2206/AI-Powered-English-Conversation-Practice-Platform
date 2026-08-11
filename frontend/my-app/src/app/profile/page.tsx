"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  Clock3,
  Route,
} from "lucide-react";
import { fetchCurrentUserClient, type MeData } from "@/lib/auth";
import {
  fetchOnboardingStatus,
  type OnboardingStatusPayload,
} from "@/lib/onboarding-status";
import EditProfileDialog from "@/components/profile/EditProfileDialog";
import ProfileHero from "@/components/profile/ProfileHero";

function displayName(user: MeData | null): string {
  if (!user) return "Learner";
  const name = user.full_name?.trim();
  if (name) return name;
  return user.username || "Learner";
}

function formatDailyGoal(minutes: number | null | undefined): string {
  if (minutes == null || minutes <= 0) return "Not set";
  return `${minutes} min / day`;
}

export default function ProfilePage() {
  const [status, setStatus] = useState<OnboardingStatusPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("Learner");
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [me, onboarding] = await Promise.all([
          fetchCurrentUserClient(),
          fetchOnboardingStatus(),
        ]);
        if (cancelled) return;
        setStatus(onboarding);
        setName(displayName(me));
        setAvatarUrl(me.avatar_url ?? null);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load profile",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <div className="ef-fade-up" style={{ ["--ef-index" as string]: 0 }}>
        <h1 className="text-[1.75rem] font-semibold tracking-tight text-[#1F1B15] md:text-[2rem]">
          Profile
        </h1>
        <p className="mt-1 text-[0.875rem] text-[#8A8178]">
          Your name, level, and daily rhythm.
        </p>
      </div>

      {loading ? (
        <p className="text-[0.875rem] text-[#8A8178]">Loading profile…</p>
      ) : error ? (
        <div
          className="rounded-2xl bg-[#FFE4E6] px-4 py-3 text-[0.875rem] text-[#BE123C] ring-1 ring-[#BE123C]/25"
          role="alert"
        >
          {error}
        </div>
      ) : (
        <>
          <div
            className="ef-fade-up"
            style={{ ["--ef-index" as string]: 1 }}
          >
            <ProfileHero
              name={name}
              avatarUrl={avatarUrl}
              onEdit={() => setDialogOpen(true)}
            />
          </div>

          <section
            className="ef-fade-up overflow-hidden rounded-[1.75rem] bg-white shadow-[0_18px_50px_rgba(31,27,21,0.06)] ring-1 ring-[#1F1B15]/06"
            style={{ ["--ef-index" as string]: 2 }}
          >
            <Link
              href="/dashboard"
              className="flex min-h-[3.5rem] items-center justify-between gap-3 px-5 py-4 transition-colors hover:bg-[#FFFAF5] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#E85D04]"
            >
              <span className="inline-flex items-center gap-3 text-[0.9375rem] font-medium text-[#1F1B15]">
                <span className="grid h-9 w-9 place-items-center rounded-xl bg-[#FFE8D6] text-[#E85D04]">
                  <Route className="h-4 w-4" aria-hidden />
                </span>
                My path
              </span>
              <span className="inline-flex items-center gap-1.5 text-[0.875rem] text-[#8A8178]">
                Open plan
                <ArrowRight className="h-4 w-4" aria-hidden />
              </span>
            </Link>

            <div className="mx-5 h-px bg-[#E9D7C9]" />

            <div className="flex min-h-[3.5rem] items-center justify-between gap-3 px-5 py-4">
              <span className="inline-flex items-center gap-3 text-[0.9375rem] font-medium text-[#1F1B15]">
                <span className="grid h-9 w-9 place-items-center rounded-xl bg-[#CCFBF1] text-[#0D9488]">
                  <BookOpen className="h-4 w-4" aria-hidden />
                </span>
                My level
              </span>
              <span className="rounded-2xl bg-[#CCFBF1] px-3 py-1 text-[0.8125rem] font-semibold text-[#115E59]">
                English · {status?.current_level ?? "—"}
              </span>
            </div>

            <div className="mx-5 h-px bg-[#E9D7C9]" />

            <div className="flex min-h-[3.5rem] items-center justify-between gap-3 px-5 py-4">
              <span className="inline-flex items-center gap-3 text-[0.9375rem] font-medium text-[#1F1B15]">
                <span className="grid h-9 w-9 place-items-center rounded-xl bg-[#D8F3DC] text-[#2F9E44]">
                  <Clock3 className="h-4 w-4" aria-hidden />
                </span>
                Daily goal
              </span>
              <span className="text-[0.875rem] text-[#6B6258]">
                {formatDailyGoal(status?.daily_time_min)}
              </span>
            </div>
          </section>

          <section
            className="ef-fade-up"
            style={{ ["--ef-index" as string]: 3 }}
          >
            <h2 className="text-[1.25rem] font-semibold tracking-tight text-[#1F1B15]">
              Help &amp; policies
            </h2>
            <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-2">
              <li>
                <Link
                  href="/terms"
                  className="inline-flex min-h-11 items-center text-[0.875rem] font-medium text-[#9A3412] underline-offset-4 hover:text-[#E85D04] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]"
                >
                  Terms
                </Link>
              </li>
              <li>
                <Link
                  href="/privacy"
                  className="inline-flex min-h-11 items-center text-[0.875rem] font-medium text-[#9A3412] underline-offset-4 hover:text-[#E85D04] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]"
                >
                  Privacy
                </Link>
              </li>
              <li>
                <a
                  href="mailto:support@englishflow.app"
                  className="inline-flex min-h-11 items-center text-[0.875rem] font-medium text-[#9A3412] underline-offset-4 hover:text-[#E85D04] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]"
                >
                  Contact support
                </a>
              </li>
            </ul>
          </section>
        </>
      )}

      <EditProfileDialog
        open={dialogOpen}
        initialName={name}
        initialAvatarUrl={avatarUrl}
        onClose={() => setDialogOpen(false)}
        onSaved={(next) => {
          setName(next.full_name);
          setAvatarUrl(next.avatar_url);
        }}
      />
    </>
  );
}
