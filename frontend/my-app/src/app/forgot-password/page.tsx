"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowLeft, Loader2, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

const CONTACT_EMAIL = "support@englishflow.app";

const fieldClass =
  "h-11 rounded-2xl border-[#E9D7C9] bg-[#FFFAF5] px-3.5 text-[0.9375rem] text-[#1F1B15] placeholder:text-[#A89F94] focus-visible:border-[#E85D04] focus-visible:ring-[#E85D04]/25";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFieldError(null);
    if (!email.trim()) {
      setFieldError("Email is required");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setFieldError("Enter a valid email address");
      return;
    }
    setLoading(true);
    // Placeholder until backend password-reset API ships.
    window.setTimeout(() => {
      setLoading(false);
      setSubmitted(true);
    }, 400);
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#FFF5EB] text-[#1F1B15]">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 70% 55% at 12% 20%, rgba(232, 93, 4, 0.16), transparent 60%), radial-gradient(ellipse 55% 50% at 88% 78%, rgba(13, 148, 136, 0.14), transparent 55%)",
        }}
      />

      <div className="relative flex min-h-screen items-center justify-center px-5 py-10">
        <div className="w-full max-w-[400px] rounded-[1.75rem] bg-white p-7 shadow-[0_18px_50px_rgba(31,27,21,0.08)] ring-1 ring-[#E9D7C9] sm:p-9">
          <Link
            href="/login"
            className="inline-flex min-h-11 items-center gap-1.5 text-[0.875rem] font-medium text-[#9A3412] transition-colors hover:text-[#E85D04] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden />
            Back to sign in
          </Link>

          <h1 className="mt-4 text-[1.75rem] font-semibold tracking-tight text-[#1F1B15]">
            Forgot password
          </h1>
          <p className="mt-2 text-[0.875rem] leading-relaxed text-[#6B6258]">
            Self-serve reset is not live yet. Leave your email and we will help
            you recover access manually.
          </p>

          {submitted ? (
            <div
              className="mt-6 rounded-2xl bg-[#D8F3DC] px-4 py-3 text-[0.875rem] leading-relaxed text-[#1F1B15] ring-1 ring-[#2F9E44]/30"
              role="status"
            >
              <p className="font-semibold text-[#2F9E44]">Request noted</p>
              <p className="mt-1 text-[#6B6258]">
                We have your address ({email.trim()}). Email{" "}
                <a
                  href={`mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent("Password reset request")}&body=${encodeURIComponent(`Please reset the password for ${email.trim()}.`)}`}
                  className="font-semibold text-[#9A3412] underline-offset-2 hover:underline"
                >
                  {CONTACT_EMAIL}
                </a>{" "}
                if you need a faster reply.
              </p>
              <Button
                asChild
                type="button"
                className="mt-4 h-11 w-full rounded-2xl bg-[#E85D04] text-[0.875rem] font-semibold text-white hover:bg-[#D04F00]"
              >
                <Link href="/login">Return to sign in</Link>
              </Button>
            </div>
          ) : (
            <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
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
                  aria-invalid={Boolean(fieldError)}
                  onChange={(e) => setEmail(e.target.value)}
                  className={cn(fieldClass, fieldError && "border-[#BE123C]")}
                />
                {fieldError ? (
                  <p className="text-[0.75rem] text-[#BE123C]">{fieldError}</p>
                ) : null}
              </div>

              <Button
                type="submit"
                disabled={loading}
                className="h-11 w-full rounded-2xl bg-[#E85D04] text-[0.9375rem] font-semibold text-white shadow-[0_10px_24px_rgba(232,93,4,0.28)] hover:bg-[#D04F00] disabled:opacity-60"
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                ) : (
                  <>
                    <Mail className="mr-2 h-4 w-4" aria-hidden />
                    Request help
                  </>
                )}
              </Button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
