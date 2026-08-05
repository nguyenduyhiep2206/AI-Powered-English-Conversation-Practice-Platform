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
  "h-11 rounded-2xl border-[#EDE6E0] bg-[#FFFCF9] px-3.5 text-[0.9375rem] text-[#2A2438] placeholder:text-[#B0A9B8] focus-visible:border-[#FF8A6B] focus-visible:ring-[#FF8A6B]/25";

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

    const errors: { email?: string; password?: string } = {};
    if (!email) errors.email = "Email is required";
    if (!password) errors.password = "Password is required";

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setError("Please fill in all required fields");
      return;
    }

    setLoading(true);
    try {
      await login(email, password, rememberMe);
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
    <div className="relative min-h-screen overflow-hidden bg-[#FFF8F4] text-[#2A2438]">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 70% 55% at 12% 20%, rgba(255, 164, 140, 0.35), transparent 60%), radial-gradient(ellipse 55% 50% at 88% 78%, rgba(140, 198, 232, 0.32), transparent 55%), radial-gradient(ellipse 40% 35% at 70% 12%, rgba(196, 176, 232, 0.18), transparent 50%)",
        }}
      />

      <div className="relative grid min-h-screen md:grid-cols-2">
        <aside className="relative hidden flex-col justify-between overflow-hidden px-10 py-10 md:flex lg:px-14 lg:py-12">
          <div
            className="ef-fade-up flex items-center gap-3"
            style={{ ["--ef-index" as string]: 0 }}
          >
            <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#FF8A6B] text-white shadow-[0_8px_24px_rgba(255,138,107,0.28)]">
              <span className="text-[1.25rem] font-bold leading-none tracking-tight">
                E
              </span>
            </div>
            <span className="text-[1.25rem] font-semibold tracking-tight text-[#2A2438]">
              EnglishFlow
            </span>
          </div>

          <div className="relative max-w-md">
            <div aria-hidden className="mb-8 flex items-center gap-3">
              {[
                "bg-[#FF8A6B]",
                "bg-[#8CC6E8]",
                "bg-[#C4B0E8]",
                "bg-[#FFD3A8]",
              ].map((tone, i) => (
                <div key={tone} className="flex items-center gap-3">
                  <span
                    className={cn(
                      "login-bob block size-3.5 rounded-full shadow-[0_2px_8px_rgba(42,36,56,0.08)]",
                      tone,
                    )}
                    style={{ ["--login-bob-delay" as string]: i * 180 }}
                  />
                  {i < 3 ? (
                    <span className="h-0.5 w-6 rounded-full bg-[#2A2438]/10" />
                  ) : null}
                </div>
              ))}
            </div>

            <h2
              className="ef-fade-up text-[2rem] font-semibold leading-[1.15] tracking-tight text-[#2A2438] lg:text-[2.75rem]"
              style={{ ["--ef-index" as string]: 1 }}
            >
              Practice real conversations that fit your level.
            </h2>
            <p
              className="ef-fade-up mt-4 text-[0.9375rem] leading-relaxed text-[#6B6478]"
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
                  className="rounded-2xl bg-white/70 px-3.5 py-1.5 text-[0.75rem] font-medium text-[#5C5468] shadow-[0_1px_0_rgba(42,36,56,0.04)] ring-1 ring-[#2A2438]/06 backdrop-blur-sm"
                >
                  {chip}
                </span>
              ))}
            </div>
          </div>

          <p
            className="ef-fade-up text-[0.875rem] text-[#8A8396]"
            style={{ ["--ef-index" as string]: 4 }}
          >
            Pick up where you left off — your path remembers you.
          </p>
        </aside>

        <div className="relative flex items-center justify-center px-5 py-10 sm:px-8 md:p-12">
          <div
            className="ef-fade-up w-full max-w-[400px] rounded-[1.75rem] bg-white p-7 shadow-[0_18px_50px_rgba(42,36,56,0.08)] ring-1 ring-[#2A2438]/06 sm:p-9"
            style={{ ["--ef-index" as string]: 1 }}
          >
            <div className="mb-7 flex items-center gap-2.5 md:hidden">
              <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#FF8A6B] text-white">
                <span className="text-[0.875rem] font-bold leading-none">E</span>
              </div>
              <span className="text-[0.875rem] font-semibold tracking-tight">
                EnglishFlow
              </span>
            </div>

            <div className="mb-7">
              <h1 className="text-[1.75rem] font-semibold tracking-tight text-[#2A2438]">
                Sign in to continue
              </h1>
              <p className="mt-2 text-[0.875rem] leading-relaxed text-[#8A8396]">
                Your roadmap and practice chats are waiting.
              </p>
            </div>

            <form className="space-y-4" onSubmit={handleSubmit} noValidate>
              {error ? (
                <div
                  className="rounded-2xl bg-[#FFF0EE] px-3.5 py-2.5 text-[0.875rem] text-[#C24B3A] ring-1 ring-[#FF8A6B]/25"
                  role="alert"
                >
                  {error}
                </div>
              ) : null}

              <div className="space-y-1.5">
                <Label htmlFor="email" className="text-[#6B6478]">
                  Email
                </Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@example.com"
                  value={email}
                  aria-invalid={Boolean(fieldErrors.email)}
                  onChange={(e) => setEmail(e.target.value)}
                  className={cn(
                    fieldClass,
                    fieldErrors.email && fieldErrorClass,
                  )}
                />
                {fieldErrors.email ? (
                  <p className="text-[0.75rem] text-[#C24B3A]">
                    {fieldErrors.email}
                  </p>
                ) : null}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="password" className="text-[#6B6478]">
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
                    className="absolute right-1 top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-xl text-[#8A8396] transition-colors hover:bg-[#FFF8F4] hover:text-[#2A2438] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#FF8A6B]"
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
                  <p className="text-[0.75rem] text-[#C24B3A]">
                    {fieldErrors.password}
                  </p>
                ) : null}
              </div>

              <div className="flex flex-wrap items-center justify-between gap-2 pt-0.5">
                <label className="inline-flex min-h-11 cursor-pointer items-center gap-2.5 text-[0.875rem] text-[#6B6478]">
                  <Checkbox
                    checked={rememberMe}
                    onCheckedChange={(checked) =>
                      setRememberMe(checked === true)
                    }
                    className="size-5 rounded-md border-[#D9D0C8] data-[state=checked]:border-[#FF8A6B] data-[state=checked]:bg-[#FF8A6B] data-[state=checked]:text-white"
                  />
                  Remember me
                </label>
                <Link
                  href="/forgot-password"
                  className="inline-flex min-h-11 items-center text-[0.8125rem] font-medium text-[#7B6EF6] transition-colors hover:text-[#6758E8] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#FF8A6B]"
                >
                  Forgot password?
                </Link>
              </div>

              <Button
                type="submit"
                disabled={loading}
                className="h-11 w-full rounded-2xl bg-[#FF8A6B] text-[0.9375rem] font-semibold text-white shadow-[0_10px_24px_rgba(255,138,107,0.28)] transition-[transform,background-color,box-shadow] duration-200 hover:bg-[#F47A5A] hover:shadow-[0_12px_28px_rgba(255,138,107,0.34)] active:scale-[0.98] disabled:opacity-60"
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                ) : (
                  <>
                    Sign in
                    <ArrowRight className="ml-1.5 h-4 w-4" aria-hidden />
                  </>
                )}
              </Button>
            </form>

            <p className="mt-7 text-center text-[0.875rem] text-[#8A8396]">
              Don&apos;t have an account?{" "}
              <Link
                href="/register"
                className="inline-flex min-h-11 items-center font-semibold text-[#7B6EF6] transition-colors hover:text-[#6758E8] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#FF8A6B]"
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
