"use client";

import { useEffect, useId, useState } from "react";
import { Loader2 } from "lucide-react";
import { updateMe } from "@/lib/api";
import { AVATAR_PRESETS, isPresetAvatar } from "@/lib/avatar-presets";
import { cn } from "@/lib/utils";

type EditProfileDialogProps = {
  open: boolean;
  initialName: string;
  initialAvatarUrl: string | null;
  onClose: () => void;
  onSaved: (next: { full_name: string; avatar_url: string | null }) => void;
};

function resolveInitialAvatar(url: string | null): string {
  return isPresetAvatar(url) ? url! : AVATAR_PRESETS[0].url;
}

export default function EditProfileDialog({
  open,
  initialName,
  initialAvatarUrl,
  onClose,
  onSaved,
}: EditProfileDialogProps) {
  if (!open) return null;

  return (
    <EditProfileDialogPanel
      key={`${initialName}::${initialAvatarUrl ?? ""}`}
      initialName={initialName}
      initialAvatarUrl={initialAvatarUrl}
      onClose={onClose}
      onSaved={onSaved}
    />
  );
}

function EditProfileDialogPanel({
  initialName,
  initialAvatarUrl,
  onClose,
  onSaved,
}: Omit<EditProfileDialogProps, "open">) {
  const titleId = useId();
  const [name, setName] = useState(initialName);
  const [avatarUrl, setAvatarUrl] = useState(
    resolveInitialAvatar(initialAvatarUrl),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && !saving) onClose();
    }

    document.addEventListener("keydown", onKeyDown);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = prev;
    };
  }, [onClose, saving]);

  async function handleSave() {
    const nextName = name.trim();
    if (!nextName) {
      setError("Name is required");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const saved = await updateMe({
        full_name: nextName,
        avatar_url: avatarUrl,
      });
      onSaved({
        full_name: saved.full_name ?? nextName,
        avatar_url: saved.avatar_url ?? avatarUrl,
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Close dialog"
        className="absolute inset-0 bg-[#1F1B15]/40 backdrop-blur-[2px]"
        disabled={saving}
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative z-10 w-full max-w-md rounded-[1.75rem] bg-white p-6 shadow-[0_24px_60px_rgba(31,27,21,0.18)] ring-1 ring-[#1F1B15]/06 sm:p-7"
      >
        <h2
          id={titleId}
          className="text-[1.75rem] font-semibold tracking-tight text-[#1F1B15]"
        >
          Edit profile
        </h2>
        <p className="mt-1.5 text-[0.875rem] text-[#8A8178]">
          Pick an avatar and how your name shows on the path.
        </p>

        <div className="mt-6 flex justify-center">
          <div className="h-20 w-20 overflow-hidden rounded-2xl bg-[#FFFAF5] shadow-[0_8px_20px_rgba(31,27,21,0.08)] ring-1 ring-[#E9D7C9]">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={avatarUrl}
              alt=""
              className="h-full w-full object-cover"
            />
          </div>
        </div>

        <p className="mt-5 text-[0.875rem] font-medium text-[#6B6258]">
          Avatar
        </p>
        <div className="mt-2 grid grid-cols-4 gap-2">
          {AVATAR_PRESETS.map((preset) => {
            const selected = avatarUrl === preset.url;
            return (
              <button
                key={preset.id}
                type="button"
                aria-label={preset.label}
                aria-pressed={selected}
                disabled={saving}
                onClick={() => setAvatarUrl(preset.url)}
                className={cn(
                  "overflow-hidden rounded-xl ring-2 transition-[box-shadow,ring-color] focus-visible:outline-none focus-visible:ring-[#E85D04]",
                  selected
                    ? "shadow-[0_4px_12px_rgba(232,93,4,0.25)] ring-[#E85D04]"
                    : "ring-transparent hover:ring-[#E9D7C9]",
                )}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={preset.url}
                  alt=""
                  className="aspect-square w-full object-cover"
                />
              </button>
            );
          })}
        </div>

        <label className="mt-5 block">
          <span className="text-[0.875rem] font-medium text-[#6B6258]">
            Display name
          </span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={saving}
            maxLength={100}
            className="mt-2 h-11 w-full rounded-2xl border border-[#E9D7C9] bg-[#FFFAF5] px-3.5 text-[0.9375rem] text-[#1F1B15] outline-none transition-[border-color,box-shadow] placeholder:text-[#A89F94] focus-visible:border-[#E85D04] focus-visible:ring-2 focus-visible:ring-[#E85D04]/25 disabled:opacity-60"
            aria-label="Display name"
            aria-invalid={Boolean(error && !name.trim())}
          />
        </label>

        {error ? (
          <p
            className="mt-3 rounded-2xl bg-[#FFE4E6] px-3.5 py-2 text-[0.875rem] text-[#BE123C] ring-1 ring-[#BE123C]/25"
            role="alert"
          >
            {error}
          </p>
        ) : null}

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            disabled={saving}
            onClick={onClose}
            className="inline-flex h-11 items-center rounded-2xl px-4 text-[0.875rem] font-medium text-[#6B6258] transition-colors hover:bg-[#FFF5EB] hover:text-[#1F1B15] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04] disabled:opacity-60"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={saving}
            aria-busy={saving}
            onClick={handleSave}
            className="inline-flex h-11 items-center gap-1.5 rounded-2xl bg-[#E85D04] px-5 text-[0.875rem] font-semibold text-white shadow-[0_10px_24px_rgba(232,93,4,0.28)] transition-[transform,background-color] hover:bg-[#D04F00] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04] active:scale-[0.98] disabled:opacity-60"
          >
            {saving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                Saving…
              </>
            ) : (
              "Save"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
