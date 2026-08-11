"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { ArrowRight, Loader2 } from "lucide-react";
import EditProfileDialog from "@/components/profile/EditProfileDialog";
import ProfileHero from "@/components/profile/ProfileHero";
import { fetchCurrentUserClient, type MeData } from "@/lib/auth";
import { logout } from "@/lib/api";
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
        "relative h-7 w-12 shrink-0 rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04] focus-visible:ring-offset-2",
        checked ? "bg-[#E85D04]" : "bg-[#E9D7C9]",
      )}
    >
      <span
        className={cn(
          "absolute top-0.5 left-0.5 h-6 w-6 rounded-full bg-white shadow-[0_2px_6px_rgba(31,27,21,0.16)] transition-transform",
          checked && "translate-x-5",
        )}
      />
    </button>
  );
}

function SettingsGroup({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="overflow-hidden rounded-[1.75rem] bg-white shadow-[0_18px_50px_rgba(31,27,21,0.06)] ring-1 ring-[#1F1B15]/06">
      <h2 className="border-b border-[#E9D7C9] px-5 py-3.5 text-[0.9375rem] font-semibold text-[#1F1B15]">
        {title}
      </h2>
      <div className="divide-y divide-[#E9D7C9]">{children}</div>
    </section>
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
          setError(
            err instanceof Error ? err.message : "Failed to load settings",
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

  async function handleSignOut() {
    setSigningOut(true);
    await logout();
  }

  return (
    <>
      <div className="ef-fade-up" style={{ ["--ef-index" as string]: 0 }}>
        <h1 className="text-[1.75rem] font-semibold tracking-tight text-[#1F1B15] md:text-[2rem]">
          Settings
        </h1>
        <p className="mt-1 text-[0.875rem] text-[#8A8178]">
          Account details and learning preferences.
        </p>
      </div>

      {loading ? (
        <p className="text-[0.875rem] text-[#8A8178]">Loading settings…</p>
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
              size="md"
              subtitle={email || undefined}
              onEdit={() => setDialogOpen(true)}
            />
          </div>

          <div
            className="ef-fade-up"
            style={{ ["--ef-index" as string]: 2 }}
          >
            <SettingsGroup title="Account">
              <div className="flex min-h-[3.5rem] items-center justify-between gap-3 px-5 py-4 text-[0.9375rem]">
                <span className="font-medium text-[#1F1B15]">Email</span>
                <span className="max-w-[60%] truncate text-[#6B6258]">
                  {email || "—"}
                </span>
              </div>
              <div className="flex min-h-[3.5rem] items-center justify-between gap-3 px-5 py-4 text-[0.9375rem]">
                <span className="font-medium text-[#1F1B15]">Password</span>
                <span className="text-[#8A8178]">Coming soon</span>
              </div>
            </SettingsGroup>
          </div>

          <div
            className="ef-fade-up"
            style={{ ["--ef-index" as string]: 3 }}
          >
            <SettingsGroup title="Preferences">
              <div className="flex min-h-[3.5rem] items-center justify-between gap-3 px-5 py-4 text-[0.9375rem]">
                <p className="font-medium text-[#1F1B15]">Sound effects</p>
                <Toggle
                  checked={soundOn}
                  label="Sound effects"
                  onChange={(next) => setSoundEffectsEnabled(next)}
                />
              </div>
              <div className="flex min-h-[3.5rem] items-center justify-between gap-3 px-5 py-4 text-[0.9375rem]">
                <div className="pr-4">
                  <p className="font-medium text-[#1F1B15]">Dyslexia mode</p>
                  <p className="mt-0.5 text-[0.75rem] text-[#8A8178]">
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
                className="flex min-h-[3.5rem] items-center justify-between gap-3 px-5 py-4 text-[0.9375rem] transition-colors hover:bg-[#FFFAF5] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#E85D04]"
              >
                <span className="font-medium text-[#1F1B15]">
                  Terms and policies
                </span>
                <ArrowRight className="h-4 w-4 text-[#8A8178]" aria-hidden />
              </Link>
              <a
                href={`mailto:${CONTACT_EMAIL}`}
                className="flex min-h-[3.5rem] items-center justify-between gap-3 px-5 py-4 text-[0.9375rem] transition-colors hover:bg-[#FFFAF5] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#E85D04]"
              >
                <span className="font-medium text-[#1F1B15]">Contact us</span>
                <ArrowRight className="h-4 w-4 text-[#8A8178]" aria-hidden />
              </a>
            </SettingsGroup>
          </div>

          <button
            type="button"
            disabled={signingOut}
            aria-busy={signingOut}
            onClick={handleSignOut}
            className="ef-fade-up inline-flex min-h-11 items-center gap-2 text-[0.9375rem] font-semibold text-[#BE123C] transition-opacity hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#BE123C] disabled:opacity-50"
            style={{ ["--ef-index" as string]: 4 }}
          >
            {signingOut ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                Signing out…
              </>
            ) : (
              "Sign out"
            )}
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
