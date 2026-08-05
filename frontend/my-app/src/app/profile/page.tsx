"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchCurrentUserClient, type MeData } from "@/lib/auth";
import {
  fetchOnboardingStatus,
  type OnboardingStatusPayload,
} from "@/lib/onboarding-status";
import { isPresetAvatar } from "@/lib/avatar-presets";
import EditProfileDialog from "@/components/profile/EditProfileDialog";
import { ArrowRightIcon } from "lucide-react";

function displayName(user: MeData | null): string {
  if (!user) return "Learner";
  const name = user.full_name?.trim();
  if (name) return name;
  return user.username || "Learner";
}

function initialLetter(name: string): string {
  return (name.charAt(0) || "U").toUpperCase();
}

function formatDailyGoal(minutes: number | null | undefined): string {
  if (minutes == null || minutes <= 0) return "Not set";
  return `${minutes} min`;
}

function IconSettings() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20">
      <path d="M20.3 12.7c-.3-.4-.3-.9 0-1.3l1.3-1.4c.3-.3.3-.8.1-1.2l-2-3.5c-.2-.4-.6-.6-1.1-.5l-1.9.4c-.5.1-1-.2-1.1-.7L15 2.7c-.2-.4-.6-.7-1-.7h-4c-.4 0-.8.3-.9.7l-.7 1.8c-.1.5-.6.8-1.1.7l-1.9-.4c-.4-.1-.8.1-1.1.5l-2 3.5c-.2.3-.1.8.2 1.1l1.3 1.4c.3.4.3.9 0 1.3L2.5 14c-.3.3-.3.8-.1 1.2l2 3.5c.2.4.6.6 1.1.5l1.9-.4c.5-.1 1 .2 1.1.7l.6 1.8c.1.4.5.7.9.7h4c.4 0 .8-.3.9-.7l.6-1.8c.2-.5.7-.8 1.1-.7l1.9.4c.4.1.9-.1 1.1-.5l2-3.5c.2-.4.2-.8-.1-1.2zM12 15c-1.7 0-3-1.3-3-3s1.3-3 3-3 3 1.3 3 3-1.3 3-3 3">
      </path>
    </svg>
  );
}

function IconPencil() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20">
      <path d="M22 7.24a1 1 0 0 0-.29-.71l-4.24-4.24a1 1 0 0 0-.71-.29 1 1 0 0 0-.71.29l-2.83 2.83L2.29 16.05a1 1 0 0 0-.29.71V21a1 1 0 0 0 1 1h4.24a1 1 0 0 0 .76-.29l10.87-10.93L21.71 8a1.2 1.2 0 0 0 .22-.33q.015-.12 0-.24a.7.7 0 0 0 0-.14zM6.83 20H4v-2.83l9.93-9.93 2.83 2.83zM18.17 8.66l-2.83-2.83 1.42-1.41 2.82 2.82z">
      </path>
    </svg>
  );
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
          setError(err instanceof Error ? err.message : "Failed to load profile");
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
      <div
        className="ef-fade-up flex items-center justify-between gap-3"
        style={{ ["--ef-index" as string]: 0 }}
      >
        <h1 className="font-display text-3xl tracking-[-0.03em]">Profile</h1>
        <Link
          href="/profile/settings"
          aria-label="Open settings"
          className="inline-flex h-10 w-10 items-center justify-center rounded-[6px] text-[#111111] transition-colors hover:bg-[#F9F9F8]"
        >
          <IconSettings />
        </Link>
      </div>

      {loading ? (
        <p className="text-sm text-[#787774]">Loading profile…</p>
      ) : error ? (
        <div className="rounded-[8px] border border-[#EAEAEA] bg-[#FDEBEC] px-4 py-3 text-sm text-[#9F2F2D]">
          {error}
        </div>
      ) : (
        <>
          <section
            className="ef-fade-up rounded-[12px] border border-[#EAEAEA] bg-[#FBF3DB] px-6 py-12 text-center"
            style={{ ["--ef-index" as string]: 1 }}
          >
            <div className="mx-auto flex h-28 w-28 items-center justify-center overflow-hidden rounded-full bg-[#111111] text-3xl font-semibold text-white">
              {isPresetAvatar(avatarUrl) ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={avatarUrl!} alt="" className="h-full w-full object-cover" />
              ) : (
                initialLetter(name)
              )}
            </div>
            <div className="relative mx-auto mt-5 w-fit">
              <p className="font-display text-3xl tracking-[-0.03em] text-[#111111] md:text-4xl">
                {name}
              </p>
              <button
                type="button"
                onClick={() => setDialogOpen(true)}
                aria-label="Edit profile"
                className="absolute left-full top-1/2 ml-2 inline-flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-[6px] text-[#787774] transition-colors hover:bg-white/70 hover:text-[#111111]"
              >
                <IconPencil />
              </button>
            </div>
          </section>

          <section
            className="ef-fade-up space-y-0 overflow-hidden rounded-[12px] border border-[#EAEAEA] bg-white"
            style={{ ["--ef-index" as string]: 2 }}
          >
            <Link
              href="/dashboard"
              className="flex items-center justify-between border-b border-[#EAEAEA] px-5 py-4 text-sm transition-colors hover:bg-[#F9F9F8]"
            >
              <span className="font-medium">My path</span>
              <div className="flex items-center gap-2">
                <span className="text-[#787774]">Open plan</span>
                <ArrowRightIcon className="h-4 w-4 text-[#787774]" />
              </div>
            </Link>
            <div className="flex items-center justify-between border-b border-[#EAEAEA] px-5 py-4 text-sm">
              <span className="font-medium">My level</span>
              <span className="text-[#787774]">
                English · {status?.current_level ?? "—"}
              </span>
            </div>
            <div className="flex items-center justify-between px-5 py-4 text-sm">
              <span className="font-medium">Daily goal</span>
              <span className="text-[#787774]">
                {formatDailyGoal(status?.daily_time_min)}
              </span>
            </div>
          </section>

          <section
            className="ef-fade-up space-y-3"
            style={{ ["--ef-index" as string]: 3 }}
          >
            <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-[#787774]">
              Handy links
            </p>
            <ul className="space-y-2">
              <li>
                <a
                  href=""
                  className="text-sm text-[#111111] underline-offset-4 hover:underline"
                >
                  Our blog
                </a>
              </li>
              <li>
                <a
                  href=""
                  className="text-sm text-[#111111] underline-offset-4 hover:underline"
                >
                  FAQ
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
