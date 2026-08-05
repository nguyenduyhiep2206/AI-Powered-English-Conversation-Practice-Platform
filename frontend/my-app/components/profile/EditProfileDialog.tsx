"use client";

import { useEffect, useId, useState } from "react";
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
  const [avatarUrl, setAvatarUrl] = useState(resolveInitialAvatar(initialAvatarUrl));
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
        className="absolute inset-0 bg-[#111111]/30"
        disabled={saving}
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative z-10 w-full max-w-md rounded-[12px] border border-[#EAEAEA] bg-white p-6 shadow-[0_2px_8px_rgba(0,0,0,0.04)]"
      >
        <h2 id={titleId} className="font-display text-2xl tracking-[-0.03em] text-[#111111]">
          Edit profile
        </h2>

        <div className="mt-6 flex justify-center">
          <div className="h-20 w-20 overflow-hidden rounded-[12px] border border-[#EAEAEA] bg-[#F9F9F8]">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={avatarUrl} alt="" className="h-full w-full object-cover" />
          </div>
        </div>

        <p className="mt-5 text-[11px] font-medium uppercase tracking-[0.12em] text-[#787774]">
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
                  "overflow-hidden rounded-[8px] border transition-colors",
                  selected
                    ? "border-[#111111]"
                    : "border-[#EAEAEA] hover:border-[#111111]/40",
                )}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={preset.url} alt="" className="aspect-square w-full object-cover" />
              </button>
            );
          })}
        </div>

        <label className="mt-5 block">
          <span className="text-[11px] font-medium uppercase tracking-[0.12em] text-[#787774]">
            Display name
          </span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={saving}
            maxLength={100}
            className="mt-2 h-10 w-full rounded-[6px] border border-[#EAEAEA] bg-white px-3 text-sm text-[#111111] outline-none focus-visible:border-[#111111]"
            aria-label="Display name"
          />
        </label>

        {error ? (
          <p className="mt-3 text-sm text-[#9F2F2D]" role="alert">
            {error}
          </p>
        ) : null}

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            disabled={saving}
            onClick={onClose}
            className="h-9 rounded-[6px] px-3 text-sm text-[#787774] transition-colors hover:bg-[#F9F9F8] hover:text-[#111111]"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={saving}
            onClick={handleSave}
            className="h-9 rounded-[6px] bg-[#111111] px-4 text-sm font-medium text-white transition-colors hover:bg-[#333333] disabled:opacity-60"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
