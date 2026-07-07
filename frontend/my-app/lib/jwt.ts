/** Decode JWT exp without verification (middleware / client guard only). */
export function isJwtExpired(token: string): boolean {
  try {
    const segment = token.split(".")[1];
    if (!segment) return true;
    const base64 = segment.replace(/-/g, "+").replace(/_/g, "/");
    const payload = JSON.parse(atob(base64)) as { exp?: number };
    if (typeof payload.exp !== "number") return false;
    return payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
}
