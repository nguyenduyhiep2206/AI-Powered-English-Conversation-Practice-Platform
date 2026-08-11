"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Eye, EyeOff, ArrowRight, Loader2 } from "lucide-react";
import { login, getMe } from "@/lib/api";
import { resolvePostLoginPath, type MeResponse } from "@/lib/auth";
import { cn } from "@/lib/utils";

const fieldClass =
  "h-11 rounded-2xl border-[#E9D7C9] bg-[#FFFAF5] px-3.5 text-[0.9375rem] text-[#1F1B15] placeholder:text-[#A89F94] focus-visible:border-[#E85D04] focus-visible:ring-[#E85D04]/25";

const fieldErrorClass =
  "border-[#E07060] focus-visible:border-[#E07060] focus-visible:ring-[#E07060]/20";

export default function LoginPage() {
  const router = useRouter();
  const [show, setShow] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{
    email?: string;
    password?: string;
  }>({});

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setFieldErrors({});

    const trimmedEmail = email.trim();
    const errors: { email?: string; password?: string } = {};
    if (!trimmedEmail) errors.email = "Email is required";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      errors.email = "Enter a valid email address";
    }
    if (!password) errors.password = "Password is required";

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setError("Please fill in all required fields");
      return;
    }

    setLoading(true);
    try {
      await login(trimmedEmail, password, rememberMe);
      const me = (await getMe()) as MeResponse;
      router.replace(resolvePostLoginPath(me.data));
      router.refresh();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to connect to the server",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#FFF5EB] text-[#1F1B15]">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 70% 55% at 12% 20%, rgba(232, 93, 4, 0.16), transparent 60%), radial-gradient(ellipse 55% 50% at 88% 78%, rgba(13, 148, 136, 0.14), transparent 55%), radial-gradient(ellipse 40% 35% at 70% 12%, rgba(47, 158, 68, 0.1), transparent 50%)",
        }}
      />

      <div className="relative grid min-h-screen md:grid-cols-2">
        <aside className="relative hidden flex-col justify-between overflow-hidden px-10 py-10 md:flex lg:px-14 lg:py-12">
          <div
            className="ef-fade-up flex items-center gap-3"
            style={{ ["--ef-index" as string]: 0 }}
          >
            <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#E85D04] text-white shadow-[0_8px_24px_rgba(232,93,4,0.28)]">
              <span className="text-[1.25rem] font-bold leading-none tracking-tight">
                E
              </span>
            </div>
            <span className="text-[1.25rem] font-semibold tracking-tight text-[#1F1B15]">
              EnglishFlow
            </span>
          </div>

          <div className="relative max-w-md">
            <div aria-hidden className="mb-8 flex items-center gap-3">
              {[
                "bg-[#E85D04]",
                "bg-[#0D9488]",
                "bg-[#2F9E44]",
                "bg-[#9A3412]",
              ].map((tone, i) => (
                <div key={tone} className="flex items-center gap-3">
                  <span
                    className={cn(
                      "login-bob block size-3.5 rounded-full shadow-[0_2px_8px_rgba(31,27,21,0.08)] ring-1 ring-[#1F1B15]/10",
                      tone,
                    )}
                    style={{ ["--login-bob-delay" as string]: i * 180 }}
                  />
                  {i < 3 ? (
                    <span className="h-0.5 w-6 rounded-full bg-[#1F1B15]/10" />
                  ) : null}
                </div>
              ))}
            </div>

            <h2
              className="ef-fade-up text-[2rem] font-semibold leading-[1.15] tracking-tight text-[#1F1B15] lg:text-[2.75rem]"
              style={{ ["--ef-index" as string]: 1 }}
            >
              Practice real conversations that fit your level.
            </h2>
            <p
              className="ef-fade-up mt-4 text-[0.9375rem] leading-relaxed text-[#6B6258]"
              style={{ ["--ef-index" as string]: 2 }}
            >
              Role-play everyday situations, get gentle corrections, and keep
              moving along a path built for you.
            </p>

            <div
              className="ef-fade-up mt-8 flex flex-wrap gap-2"
              style={{ ["--ef-index" as string]: 3 }}
            >
              {["A1–C1 paths", "AI role-play", "Lesson Q&A"].map((chip) => (
                <span
                  key={chip}
                  className="rounded-2xl bg-white/70 px-3.5 py-1.5 text-[0.75rem] font-medium text-[#6B6258] shadow-[0_1px_0_rgba(31,27,21,0.04)] ring-1 ring-[#1F1B15]/06 backdrop-blur-sm"
                >
                  {chip}
                </span>
              ))}
            </div>
          </div>

          <p
            className="ef-fade-up text-[0.875rem] text-[#8A8178]"
            style={{ ["--ef-index" as string]: 4 }}
          >
            Pick up where you left off. Your path remembers you.
          </p>
        </aside>

        <div className="relative flex items-center justify-center px-5 py-10 sm:px-8 md:p-12">
          <div
            className="ef-fade-up w-full max-w-[400px] rounded-[1.75rem] bg-white p-7 shadow-[0_18px_50px_rgba(31,27,21,0.08)] ring-1 ring-[#1F1B15]/06 sm:p-9"
            style={{ ["--ef-index" as string]: 1 }}
          >
            <div className="mb-7 flex items-center gap-2.5 md:hidden">
              <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#E85D04] text-white">
                <span className="text-[0.875rem] font-bold leading-none">E</span>
              </div>
              <span className="text-[0.875rem] font-semibold tracking-tight">
                EnglishFlow
              </span>
            </div>

            <div className="mb-7">
              <h1 className="text-[1.75rem] font-semibold tracking-tight text-[#1F1B15]">
                Sign in to continue
              </h1>
              <p className="mt-2 text-[0.875rem] leading-relaxed text-[#8A8178]">
                Your roadmap and practice chats are waiting.
              </p>
            </div>

            <form className="space-y-4" onSubmit={handleSubmit} noValidate>
              {error ? (
                <div
                  className="rounded-2xl bg-[#FFE4E6] px-3.5 py-2.5 text-[0.875rem] text-[#BE123C] ring-1 ring-[#BE123C]/25"
                  role="alert"
                >
                  {error}
                </div>
              ) : null}

              <div className="space-y-1.5">
                <Label htmlFor="email" className="text-[#6B6258]">
                  Email
                </Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@example.com"
                  value={email}
                  aria-invalid={Boolean(fieldErrors.email)}
                  aria-describedby={
                    fieldErrors.email ? "email-error" : undefined
                  }
                  onChange={(e) => setEmail(e.target.value)}
                  className={cn(
                    fieldClass,
                    fieldErrors.email && fieldErrorClass,
                  )}
                />
                {fieldErrors.email ? (
                  <p id="email-error" className="text-[0.75rem] text-[#BE123C]">
                    {fieldErrors.email}
                  </p>
                ) : null}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="password" className="text-[#6B6258]">
                  Password
                </Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={show ? "text" : "password"}
                    autoComplete="current-password"
                    placeholder="••••••••"
                    value={password}
                    aria-invalid={Boolean(fieldErrors.password)}
                    aria-describedby={
                      fieldErrors.password ? "password-error" : undefined
                    }
                    onChange={(e) => setPassword(e.target.value)}
                    className={cn(
                      fieldClass,
                      "pr-12",
                      fieldErrors.password && fieldErrorClass,
                    )}
                  />
                  <button
                    type="button"
                    onClick={() => setShow((s) => !s)}
                    className="absolute right-1 top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-xl text-[#8A8178] transition-colors hover:bg-[#FFF5EB] hover:text-[#1F1B15] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]"
                    aria-label={show ? "Hide password" : "Show password"}
                  >
                    {show ? (
                      <EyeOff className="h-4 w-4" aria-hidden />
                    ) : (
                      <Eye className="h-4 w-4" aria-hidden />
                    )}
                  </button>
                </div>
                {fieldErrors.password ? (
                  <p
                    id="password-error"
                    className="text-[0.75rem] text-[#BE123C]"
                  >
                    {fieldErrors.password}
                  </p>
                ) : null}
              </div>

              <div className="flex items-center justify-between gap-3 pt-0.5">
                <label className="inline-flex min-h-11 shrink-0 cursor-pointer items-center gap-2.5 whitespace-nowrap text-[0.875rem] text-[#6B6258]">
                  <Checkbox
                    checked={rememberMe}
                    onCheckedChange={(checked) =>
                      setRememberMe(checked === true)
                    }
                    className="size-5 rounded-md border-[#D4C0AE] data-[state=checked]:border-[#E85D04] data-[state=checked]:bg-[#E85D04] data-[state=checked]:text-white"
                  />
                  Remember me
                </label>
                <Link
                  href="/forgot-password"
                  className="inline-flex min-h-11 shrink-0 items-center whitespace-nowrap text-[0.8125rem] font-medium text-[#9A3412] transition-colors hover:text-[#E85D04] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]"
                >
                  Forgot password?
                </Link>
              </div>

              <Button
                type="submit"
                disabled={loading}
                aria-busy={loading}
                className="h-11 w-full rounded-2xl bg-[#E85D04] text-[0.9375rem] font-semibold text-white shadow-[0_10px_24px_rgba(232,93,4,0.28)] transition-[transform,background-color,box-shadow] duration-200 hover:bg-[#D04F00] hover:shadow-[0_12px_28px_rgba(232,93,4,0.34)] active:scale-[0.98] disabled:opacity-60"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-1.5 h-4 w-4 animate-spin" aria-hidden />
                    Signing in…
                  </>
                ) : (
                  <>
                    Sign in
                    <ArrowRight className="ml-1.5 h-4 w-4" aria-hidden />
                  </>
                )}
              </Button>
            </form>

            <p className="mt-7 text-center text-[0.875rem] text-[#8A8178]">
              Don&apos;t have an account?{" "}
              <Link
                href="/register"
                className="inline-flex min-h-11 items-center font-semibold text-[#9A3412] transition-colors hover:text-[#E85D04] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]"
              >
                Create one
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
