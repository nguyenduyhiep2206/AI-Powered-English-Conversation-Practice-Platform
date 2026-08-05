const SOUND_KEY = "ef.prefs.soundEffects";
const DYSLEXIA_KEY = "ef.prefs.dyslexiaMode";
const PREFS_EVENT = "ef-prefs-change";

function readBool(key: string, fallback: boolean): boolean {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    if (raw == null) return fallback;
    return raw === "1" || raw === "true";
  } catch {
    return fallback;
  }
}

function writeBool(key: string, value: boolean): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, value ? "1" : "0");
    window.dispatchEvent(new Event(PREFS_EVENT));
  } catch {
    // Ignore quota / private mode failures.
  }
}

export function subscribeLearnerPrefs(onStoreChange: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  const handler = () => onStoreChange();
  window.addEventListener("storage", handler);
  window.addEventListener(PREFS_EVENT, handler);
  return () => {
    window.removeEventListener("storage", handler);
    window.removeEventListener(PREFS_EVENT, handler);
  };
}

export function getSoundEffectsEnabled(): boolean {
  return readBool(SOUND_KEY, true);
}

export function setSoundEffectsEnabled(value: boolean): void {
  writeBool(SOUND_KEY, value);
}

export function getDyslexiaModeEnabled(): boolean {
  return readBool(DYSLEXIA_KEY, false);
}

export function setDyslexiaModeEnabled(value: boolean): void {
  writeBool(DYSLEXIA_KEY, value);
  if (typeof document !== "undefined") {
    document.documentElement.dataset.dyslexia = value ? "on" : "off";
  }
}

/** Apply stored dyslexia preference on client mount. */
export function applyStoredDyslexiaMode(): void {
  if (typeof document === "undefined") return;
  document.documentElement.dataset.dyslexia = getDyslexiaModeEnabled()
    ? "on"
    : "off";
}
