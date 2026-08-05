"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Eye, EyeOff, ArrowRight, Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { register } from "@/lib/api";

function strength(pw: string) {
  let s = 0;
  if (pw.length >= 8) s++;
  if (/[A-Z]/.test(pw)) s++;
  if (/[0-9]/.test(pw)) s++;
  if (/[^A-Za-z0-9]/.test(pw)) s++;
  return s; // 0..4
}

const fieldClass =
  "h-11 rounded-2xl border-[#EDE6E0] bg-[#FFFCF9] px-3.5 text-[0.9375rem] text-[#2A2438] placeholder:text-[#B0A9B8] focus-visible:border-[#FF8A6B] focus-visible:ring-[#FF8A6B]/25";

const fieldErrorClass =
  "border-[#E07060] focus-visible:border-[#E07060] focus-visible:ring-[#E07060]/20";

/** Soft coral → sky, not Duolingo green */
const strengthTones = [
  "bg-[#EDE6E0]",
  "bg-[#E07060]",
  "bg-[#FFB38A]",
  "bg-[#8CC6E8]",
  "bg-[#7B6EF6]",
];

export default function RegisterPage() {
  const router = useRouter();
  const [show, setShow] = useState(false);

  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [agreed, setAgreed] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{
    name?: string;
    username?: string;
    email?: string;
    pw?: string;
    confirm?: string;
    agreed?: string;
  }>({});

  const s = useMemo(() => strength(pw), [pw]);
  const labels = ["Too weak", "Weak", "Okay", "Strong", "Excellent"];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setFieldErrors({});

    const errors: typeof fieldErrors = {};
    if (!name) errors.name = "Full name is required";
    if (!username) errors.username = "Username is required";
    if (!email) errors.email = "Email is required";
    if (!pw) errors.pw = "Password is required";
    else if (pw.length < 8)
      errors.pw = "Password must be at least 8 characters long";
    if (!confirm) errors.confirm = "Password confirmation is required";
    else if (pw !== confirm) errors.confirm = "Passwords do not match";
    if (!agreed) errors.agreed = "You must agree to the Terms and Privacy Policy";

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setError("Please fill in all required fields correctly");
      return;
    }

    setLoading(true);
    try {
      await register({ full_name: name, username, email, password: pw });
      router.replace("/start-onboarding");
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
            "radial-gradient(ellipse 70% 55% at 88% 18%, rgba(255, 164, 140, 0.35), transparent 60%), radial-gradient(ellipse 55% 50% at 12% 82%, rgba(140, 198, 232, 0.32), transparent 55%), radial-gradient(ellipse 40% 35% at 30% 12%, rgba(196, 176, 232, 0.18), transparent 50%)",
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
                "bg-[#FFD3A8]",
                "bg-[#8CC6E8]",
                "bg-[#C4B0E8]",
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
              A goal, a path, and your first conversation — ready when you are.
            </h2>
            <ul
              className="ef-fade-up mt-6 space-y-3"
              style={{ ["--ef-index" as string]: 2 }}
            >
              {[
                "Personalized roadmap from A1 to C1",
                "Gentle feedback in every practice chat",
                "Vocab review that fits your pace",
              ].map((t) => (
                <li
                  key={t}
                  className="flex items-start gap-2.5 text-[0.9375rem] leading-snug text-[#6B6478]"
                >
                  <span className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full bg-[#FF8A6B]/15 text-[#FF8A6B]">
                    <Check className="h-3 w-3" strokeWidth={2.5} aria-hidden />
                  </span>
                  {t}
                </li>
              ))}
            </ul>
          </div>

          <p
            className="ef-fade-up text-[0.875rem] text-[#8A8396]"
            style={{ ["--ef-index" as string]: 3 }}
          >
            Free to start — build a habit that sticks.
          </p>
        </aside>

        <div className="relative flex items-center justify-center px-5 py-8 sm:px-8 md:p-10 lg:py-12">
          <div
            className="ef-fade-up w-full max-w-[440px] rounded-[1.75rem] bg-white p-6 shadow-[0_18px_50px_rgba(42,36,56,0.08)] ring-1 ring-[#2A2438]/06 sm:p-8"
            style={{ ["--ef-index" as string]: 1 }}
          >
            <div className="mb-6 flex items-center gap-2.5 md:hidden">
              <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#FF8A6B] text-white">
                <span className="text-[0.875rem] font-bold leading-none">E</span>
              </div>
              <span className="text-[0.875rem] font-semibold tracking-tight">
                EnglishFlow
              </span>
            </div>

            <div className="mb-6">
              <h1 className="text-[1.75rem] font-semibold tracking-tight text-[#2A2438]">
                Start your path
              </h1>
              <p className="mt-2 text-[0.875rem] leading-relaxed text-[#8A8396]">
                Already have an account?{" "}
                <Link
                  href="/login"
                  className="inline-flex min-h-11 items-center font-semibold text-[#7B6EF6] transition-colors hover:text-[#6758E8] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#FF8A6B]"
                >
                  Sign in
                </Link>
              </p>
            </div>

            <form className="space-y-3.5" onSubmit={handleSubmit} noValidate>
              {error ? (
                <div
                  className="rounded-2xl bg-[#FFF0EE] px-3.5 py-2.5 text-[0.875rem] text-[#C24B3A] ring-1 ring-[#FF8A6B]/25"
                  role="alert"
                >
                  {error}
                </div>
              ) : null}

              <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="name" className="text-[#6B6478]">
                    Full name
                  </Label>
                  <Input
                    id="name"
                    autoComplete="name"
                    placeholder="Your name"
                    value={name}
                    aria-invalid={Boolean(fieldErrors.name)}
                    onChange={(e) => setName(e.target.value)}
                    className={cn(
                      fieldClass,
                      fieldErrors.name && fieldErrorClass,
                    )}
                  />
                  {fieldErrors.name ? (
                    <p className="text-[0.75rem] text-[#C24B3A]">
                      {fieldErrors.name}
                    </p>
                  ) : null}
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="username" className="text-[#6B6478]">
                    Username
                  </Label>
                  <Input
                    id="username"
                    autoComplete="username"
                    placeholder="Username"
                    value={username}
                    aria-invalid={Boolean(fieldErrors.username)}
                    onChange={(e) => setUsername(e.target.value)}
                    className={cn(
                      fieldClass,
                      fieldErrors.username && fieldErrorClass,
                    )}
                  />
                  {fieldErrors.username ? (
                    <p className="text-[0.75rem] text-[#C24B3A]">
                      {fieldErrors.username}
                    </p>
                  ) : null}
                </div>
              </div>

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
                    autoComplete="new-password"
                    placeholder="At least 8 characters"
                    value={pw}
                    aria-invalid={Boolean(fieldErrors.pw)}
                    onChange={(e) => setPw(e.target.value)}
                    className={cn(
                      fieldClass,
                      "pr-12",
                      fieldErrors.pw && fieldErrorClass,
                    )}
                  />
                  <button
                    type="button"
                    onClick={() => setShow((v) => !v)}
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
                {fieldErrors.pw ? (
                  <p className="text-[0.75rem] text-[#C24B3A]">{fieldErrors.pw}</p>
                ) : null}
                <div className="mt-2 flex items-center gap-2">
                  <div className="flex flex-1 gap-1" aria-hidden>
                    {[0, 1, 2, 3].map((i) => (
                      <div
                        key={i}
                        className={cn(
                          "h-1.5 flex-1 rounded-full bg-[#EDE6E0]",
                          i < s && strengthTones[s],
                        )}
                      />
                    ))}
                  </div>
                  <span className="w-[4.5rem] text-right text-[0.75rem] font-medium text-[#8A8396]">
                    {pw ? labels[s] : ""}
                  </span>
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="confirm" className="text-[#6B6478]">
                  Confirm password
                </Label>
                <Input
                  id="confirm"
                  type={show ? "text" : "password"}
                  autoComplete="new-password"
                  placeholder="Repeat password"
                  value={confirm}
                  aria-invalid={Boolean(fieldErrors.confirm)}
                  onChange={(e) => setConfirm(e.target.value)}
                  className={cn(
                    fieldClass,
                    fieldErrors.confirm && fieldErrorClass,
                  )}
                />
                {fieldErrors.confirm ? (
                  <p className="text-[0.75rem] text-[#C24B3A]">
                    {fieldErrors.confirm}
                  </p>
                ) : null}
              </div>

              <div className="pt-0.5">
                <label className="inline-flex min-h-11 cursor-pointer items-start gap-2.5 text-[0.8125rem] leading-relaxed text-[#6B6478]">
                  <Checkbox
                    checked={agreed}
                    onCheckedChange={(v) => setAgreed(v === true)}
                    className="mt-0.5 size-5 rounded-md border-[#D9D0C8] data-[state=checked]:border-[#FF8A6B] data-[state=checked]:bg-[#FF8A6B] data-[state=checked]:text-white"
                  />
                  <span>
                    I agree to the{" "}
                    <Link
                      href="/terms"
                      className="inline-flex min-h-11 min-w-11 items-center justify-center font-medium text-[#7B6EF6] transition-colors hover:text-[#6758E8] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#FF8A6B]"
                    >
                      Terms
                    </Link>{" "}
                    and Privacy Policy.
                  </span>
                </label>
                {fieldErrors.agreed ? (
                  <p className="mt-1.5 text-[0.75rem] text-[#C24B3A]">
                    {fieldErrors.agreed}
                  </p>
                ) : null}
              </div>

              <Button
                type="submit"
                disabled={loading}
                className="mt-1 h-11 w-full rounded-2xl bg-[#FF8A6B] text-[0.9375rem] font-semibold text-white shadow-[0_10px_24px_rgba(255,138,107,0.28)] transition-[transform,background-color,box-shadow] duration-200 hover:bg-[#F47A5A] hover:shadow-[0_12px_28px_rgba(255,138,107,0.34)] active:scale-[0.98] disabled:opacity-60"
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                ) : (
                  <>
                    Create account
                    <ArrowRight className="ml-1.5 h-4 w-4" aria-hidden />
                  </>
                )}
              </Button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
