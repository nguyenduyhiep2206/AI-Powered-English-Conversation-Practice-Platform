"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Eye, EyeOff, ArrowRight, Loader2 } from "lucide-react";
import GoogleSignInButton from "@/components/ui/GoogleSignInButton";

export default function LoginPage() {
  const router = useRouter();
  const [show, setShow] = useState(false);

  // 1. State save email, password, error, loading
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});

  // 2. Function to handle form submission
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setFieldErrors({});

    // Validate required fields
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
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.message || "Email or password is incorrect");
        return;
      }

      // Login successful -> redirect
      router.push("/register");
      router.refresh();
    } catch (err) {
      setError("Unable to connect to the server");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="dark min-h-screen bg-background text-foreground">
      <div className="grid min-h-screen md:grid-cols-2">
        {/* Brand panel */}
        <div className="relative hidden md:flex flex-col justify-between border-r border-border bg-sidebar p-10">
          <div className="flex items-center gap-2">
            <div className="grid h-9 w-9 place-items-center rounded-lg bg-primary text-primary-foreground">
              <span className="font-display text-xl leading-none">E</span>
            </div>
            <span className="text-sm font-semibold tracking-tight">EnglishFlow</span>
          </div>
          <div className="max-w-md space-y-4">
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              Practice that actually sticks
            </p>
            <h2 className="font-display text-4xl leading-tight">
              Conversations that meet you where you are - and nudge you one step further.
            </h2>
            <p className="text-sm text-muted-foreground">
              Roleplay real scenarios with an AI partner. Get inline grammar repair, vocab
              suggestions, and a clarity score after every session.
            </p>
          </div>
          <div className="flex items-center gap-6 text-xs text-muted-foreground">
            <div><span className="text-foreground font-semibold">12k+</span> learners</div>
            <div><span className="text-foreground font-semibold">340</span> scenarios</div>
            <div><span className="text-foreground font-semibold">A1–C1</span> CEFR coverage</div>
          </div>
        </div>

        {/* Form */}
        <div className="flex items-center justify-center p-6 md:p-12">
          <div className="w-full max-w-sm">
            <div className="mb-8">
              <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                Welcome back
              </p>
              <h1 className="mt-2 font-display text-3xl">Sign in to your flow</h1>
            </div>

            <form className="space-y-4" onSubmit={handleSubmit}>
              {error && (
                <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {error}
                </div>
              )}

              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={fieldErrors.email ? "border-destructive" : ""}
                />
                {fieldErrors.email && (
                  <p className="text-xs text-destructive">{fieldErrors.email}</p>
                )}
              </div>
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Password</Label>
                  <Link href="/forgot-password" className="text-xs text-primary hover:underline">
                    Forgot password?
                  </Link>
                </div>
                <div className="relative">
                  <Input
                    id="password"
                    type={show ? "text" : "password"}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className={fieldErrors.password ? "border-destructive" : ""}
                  />
                  <button
                    type="button"
                    onClick={() => setShow((s) => !s)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:text-foreground"
                    aria-label={show ? "Hide password" : "Show password"}
                  >
                    {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {fieldErrors.password && (
                  <p className="text-xs text-destructive">{fieldErrors.password}</p>
                )}
              </div>

              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <Checkbox /> Remember me
              </label>

              <Button type="submit" className="w-full h-10 rounded-2xl" disabled={loading}>
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    Sign in <ArrowRight className="ml-1.5 h-4 w-4" />
                  </>
                )}
              </Button>
            </form>

            <div className="my-6 flex items-center gap-3 text-xs text-muted-foreground">
              <div className="h-px flex-1 bg-border" />
              or
              <div className="h-px flex-1 bg-border" />
            </div>

            <div className="my-2">
              <GoogleSignInButton />
            </div>
            <p className="text-center text-sm text-muted-foreground">
              Don't have an account?{" "}
              <Link href={`/register`} className="text-primary hover:underline">
                Create one
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}