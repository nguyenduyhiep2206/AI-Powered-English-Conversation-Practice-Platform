"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { ArrowRightIcon } from "lucide-react";
import EditProfileDialog from "@/components/profile/EditProfileDialog";
import { fetchCurrentUserClient, type MeData } from "@/lib/auth";
import { logout } from "@/lib/api";
import { isPresetAvatar } from "@/lib/avatar-presets";
import {
  applyStoredDyslexiaMode,
  getDyslexiaModeEnabled,
  getSoundEffectsEnabled,
  setDyslexiaModeEnabled,
  setSoundEffectsEnabled,
  subscribeLearnerPrefs,
} from "@/lib/learner-prefs";
import { cn } from "@/lib/utils";

const CONTACT_EMAIL = "support@englishflow.app";

function displayName(user: MeData | null): string {
  if (!user) return "Learner";
  const name = user.full_name?.trim();
  if (name) return name;
  return user.username || "Learner";
}

function initialLetter(name: string): string {
  return (name.charAt(0) || "U").toUpperCase();
}

function IconPencil() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20">
      <path d="M22 7.24a1 1 0 0 0-.29-.71l-4.24-4.24a1 1 0 0 0-.71-.29 1 1 0 0 0-.71.29l-2.83 2.83L2.29 16.05a1 1 0 0 0-.29.71V21a1 1 0 0 0 1 1h4.24a1 1 0 0 0 .76-.29l10.87-10.93L21.71 8a1.2 1.2 0 0 0 .22-.33q.015-.12 0-.24a.7.7 0 0 0 0-.14zM6.83 20H4v-2.83l9.93-9.93 2.83 2.83zM18.17 8.66l-2.83-2.83 1.42-1.41 2.82 2.82z">
      </path>
    </svg>
  );
}

function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative h-6 w-11 shrink-0 rounded-full transition-colors",
        checked ? "bg-[#111111]" : "bg-[#EAEAEA]",
      )}
    >
      <span
        className={cn(
          "absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white transition-transform",
          checked && "translate-x-5",
        )}
      />
    </button>
  );
}

export default function ProfileSettingsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("Learner");
  const [email, setEmail] = useState("");
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  const soundOn = useSyncExternalStore(
    subscribeLearnerPrefs,
    getSoundEffectsEnabled,
    () => true,
  );
  const dyslexiaOn = useSyncExternalStore(
    subscribeLearnerPrefs,
    getDyslexiaModeEnabled,
    () => false,
  );

  useEffect(() => {
    applyStoredDyslexiaMode();
  }, [dyslexiaOn]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const me = await fetchCurrentUserClient();
        if (cancelled) return;
        setName(displayName(me));
        setEmail(me.email || "");
        setAvatarUrl(me.avatar_url ?? null);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load settings");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSignOut() {
    setSigningOut(true);
    await logout();
  }

  return (
    <>
      <div className="ef-fade-up" style={{ ["--ef-index" as string]: 0 }}>
        <h1 className="font-display text-3xl tracking-[-0.03em]">Settings</h1>
      </div>

      {loading ? (
        <p className="text-sm text-[#787774]">Loading settings…</p>
      ) : error ? (
        <div className="rounded-[8px] border border-[#EAEAEA] bg-[#FDEBEC] px-4 py-3 text-sm text-[#9F2F2D]">
          {error}
        </div>
      ) : (
        <>
          <section
            className="ef-fade-up rounded-[12px] border border-[#EAEAEA] bg-[#FBF3DB] px-6 py-10 text-center"
            style={{ ["--ef-index" as string]: 1 }}
          >
            <div className="mx-auto flex h-28 w-28 items-center justify-center overflow-hidden rounded-full bg-[#111111] text-2xl font-semibold text-white">
              {isPresetAvatar(avatarUrl) ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={avatarUrl!} alt="" className="h-full w-full object-cover" />
              ) : (
                initialLetter(name)
              )}
            </div>
            <div className="relative mx-auto mt-4 w-fit">
              <p className="font-display text-2xl tracking-[-0.03em] text-[#111111] md:text-3xl">
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
            <p className="border-b border-[#EAEAEA] px-5 py-3 text-[11px] font-medium uppercase tracking-[0.12em] text-[#787774]">
              Account info
            </p>
            <div className="flex items-center justify-between border-b border-[#EAEAEA] px-5 py-4 text-sm">
              <span className="font-medium">Email</span>
              <span className="max-w-[60%] truncate text-[#787774]">{email || "—"}</span>
            </div>
            <div className="flex items-center justify-between px-5 py-4 text-sm">
              <span className="font-medium">Password</span>
              <span className="text-[#787774]">Coming soon</span>
            </div>
          </section>

          <section
            className="ef-fade-up space-y-0 overflow-hidden rounded-[12px] border border-[#EAEAEA] bg-white"
            style={{ ["--ef-index" as string]: 3 }}
          >
            <p className="border-b border-[#EAEAEA] px-5 py-3 text-[11px] font-medium uppercase tracking-[0.12em] text-[#787774]">
              General
            </p>
            <div className="flex items-center justify-between border-b border-[#EAEAEA] px-5 py-4 text-sm">
              <p className="font-medium">Sound effects</p>
              <Toggle
                checked={soundOn}
                label="Sound effects"
                onChange={(next) => setSoundEffectsEnabled(next)}
              />
            </div>
            <div className="flex items-center justify-between border-b border-[#EAEAEA] px-5 py-4 text-sm">
              <div className="pr-4">
                <p className="font-medium">Dyslexia mode</p>
                <p className="mt-0.5 text-xs text-[#787774]">
                  Easier-to-read type when available
                </p>
              </div>
              <Toggle
                checked={dyslexiaOn}
                label="Dyslexia mode"
                onChange={(next) => setDyslexiaModeEnabled(next)}
              />
            </div>
            <Link
              href="/terms"
              className="flex items-center justify-between border-b border-[#EAEAEA] px-5 py-4 text-sm transition-colors hover:bg-[#F9F9F8]"
            >
              <span className="font-medium">Terms and policies</span>
              <ArrowRightIcon className="h-4 w-4 text-[#787774]" />
            </Link>
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="flex items-center justify-between px-5 py-4 text-sm transition-colors hover:bg-[#F9F9F8]"
            >
              <span className="font-medium">Contact us</span>
              <ArrowRightIcon className="h-4 w-4 text-[#787774]" />
            </a>
          </section>

          <button
            type="button"
            disabled={signingOut}
            onClick={handleSignOut}
            className="ef-fade-up text-left text-sm font-medium text-[#9F2F2D] transition-opacity hover:opacity-80 disabled:opacity-50"
            style={{ ["--ef-index" as string]: 4 }}
          >
            {signingOut ? "Signing out…" : "Sign out"}
          </button>
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
