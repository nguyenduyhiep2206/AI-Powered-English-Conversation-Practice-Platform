export type AvatarPreset = {
  id: string;
  url: string;
  label: string;
};

export const AVATAR_PRESETS: AvatarPreset[] = [
  { id: "01", url: "/avatars/Mask group.png", label: "Ink circle" },
  { id: "02", url: "/avatars/Mask group (1).png", label: "Soft square" },
  { id: "03", url: "/avatars/Mask group (2).png", label: "Blue mark" },
  { id: "04", url: "/avatars/Mask group (3).png", label: "Green mark" },
  { id: "05", url: "/avatars/Mask group (4).png", label: "Yellow mark" },
  { id: "06", url: "/avatars/Mask group (5).png", label: "Red mark" },
  { id: "07", url: "/avatars/Mask group (6).png", label: "Split mark" },
  { id: "08", url: "/avatars/Mask group (7).png", label: "Arc mark" },
  { id: "09", url: "/avatars/Mask group (8).png", label: "Star mark" },
  { id: "10", url: "/avatars/Mask group (9).png", label: "Heart mark" },
  { id: "11", url: "/avatars/Mask group (10).png", label: "Diamond mark" },
  { id: "12", url: "/avatars/Mask group (11).png", label: "Triangle mark" },
  { id: "13", url: "/avatars/Mask group (12).png", label: "Square mark" },
  { id: "14", url: "/avatars/Mask group (13).png", label: "Circle mark" },
];

const PRESET_URLS = new Set(AVATAR_PRESETS.map((p) => p.url));

export function isPresetAvatar(url: string | null | undefined): boolean {
  return Boolean(url && PRESET_URLS.has(url));
}

export function pickRandomAvatarPreset(): AvatarPreset {
  const index = Math.floor(Math.random() * AVATAR_PRESETS.length);
  return AVATAR_PRESETS[index] ?? AVATAR_PRESETS[0];
}

export function avatarInitial(
  fullName?: string | null,
  username?: string | null,
): string {
  const source = (fullName || username || "U").trim();
  return (source.charAt(0) || "U").toUpperCase();
}
