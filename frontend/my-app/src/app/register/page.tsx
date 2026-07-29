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

export default function RegisterPage() {
  const router = useRouter();
  const [show, setShow] = useState(false);

  // State for each field
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
  const tones = ['bg-destructive', 'bg-red-500', 'bg-white', 'bg-green-500', 'bg-green-600'];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setFieldErrors({});

    // Validate on the frontend first (quick UX, no need to wait for network)
    const errors: typeof fieldErrors = {};
    if (!name) errors.name = "Full name is required";
    if (!username) errors.username = "Username is required";
    if (!email) errors.email = "Email is required";
    if (!pw) errors.pw = "Password is required";
    else if (pw.length < 8) errors.pw = "Password must be at least 8 characters long";
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
      setError(err instanceof Error ? err.message : "Unable to connect to the server");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="grid min-h-screen md:grid-cols-2">
        <div className="relative hidden md:flex flex-col justify-between border-r border-border bg-sidebar px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="grid h-9 w-9 place-items-center rounded-lg bg-primary text-primary-foreground">
              <span className="font-display text-xl leading-none">E</span>
            </div>
            <span className="text-sm font-semibold tracking-tight">EnglishFlow</span>
          </div>
          <div className="max-w-md space-y-4">
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              Begin in 3 minutes
            </p>
            <h2 className="font-display text-4xl leading-tight">
              A placement test, a goal, and your first conversation — all before your coffee
              gets cold.
            </h2>
            <ul className="space-y-2 text-sm text-muted-foreground">
              {[
                "Personalized roadmap from A1 to C1",
                "Inline grammar & vocab feedback in every chat",
                "Spaced-repetition vocab review that actually works",
              ].map((t) => (
                <li key={t} className="flex items-start gap-2">
                  <Check className="mt-0.5 h-4 w-4 text-emerald-500" /> {t}
                </li>
              ))}
            </ul>
          </div>
          <div className="text-xs text-muted-foreground">
          </div>
        </div>

        <div className="flex items-center justify-center p-6 md:p-12">
          <div className="w-full max-w-md">
            <div className="mb-8">
              <div className="mb-4 text-center text-muted-foreground">
                Already have an account?{" "}
                <Link href="/login" className="text-primary hover:underline">Sign in</Link>
              </div>
              <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                Create your account
              </p>
              <h1 className="mt-2 font-display text-3xl">Start your flow</h1>
            </div>

            <form className="space-y-4" onSubmit={handleSubmit}>
              {error && (
                <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {error}
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="name">Full name</Label>
                  <Input
                    id="name"
                    placeholder="Your Name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className={fieldErrors.name ? "border-destructive" : ""}
                  />
                  {fieldErrors.name && (
                    <p className="text-xs text-destructive">{fieldErrors.name}</p>
                  )}
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="username">Username</Label>
                  <Input
                    id="username"
                    placeholder="Username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className={fieldErrors.username ? "border-destructive" : ""}
                  />
                  {fieldErrors.username && (
                    <p className="text-xs text-destructive">{fieldErrors.username}</p>
                  )}
                </div>
              </div>

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
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={show ? "text" : "password"}
                    placeholder="At least 8 characters"
                    value={pw}
                    onChange={(e) => setPw(e.target.value)}
                    className={fieldErrors.pw ? "border-destructive" : ""}
                  />
                  <button
                    type="button"
                    onClick={() => setShow((v) => !v)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:text-foreground"
                  >
                    {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {fieldErrors.pw && (
                  <p className="text-xs text-destructive">{fieldErrors.pw}</p>
                )}
                <div className="mt-2 flex items-center gap-2">
                  <div className="flex flex-1 gap-1">
                    {[0, 1, 2, 3].map((i) => (
                      <div
                        key={i}
                        className={cn(
                          "h-1 flex-1 rounded-full bg-muted",
                          i < s && tones[s]
                        )}
                      />
                    ))}
                  </div>
                  <span className="w-20 text-right text-[11px] text-muted-foreground">
                    {pw ? labels[s] : ""}
                  </span>
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="confirm">Confirm password</Label>
                <Input
                  id="confirm"
                  type={show ? "text" : "password"}
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  className={fieldErrors.confirm ? "border-destructive" : ""}
                />
                {fieldErrors.confirm && (
                  <p className="text-xs text-destructive">{fieldErrors.confirm}</p>
                )}
              </div>

              <label className="flex items-start gap-2 text-xs text-muted-foreground">
                <Checkbox
                  className="border-primary data-[state=checked]:border-primary data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground"
                  checked={agreed}
                  onCheckedChange={(v) => setAgreed(v === true)}
                />
                <span>
                  I agree to the{" "}
                  <a className="text-primary hover:underline" href="#">
                    Terms
                  </a>{" "}
                  and{" "}
                  <a className="text-primary hover:underline" href="#">
                    Privacy Policy
                  </a>
                  .
                </span>
              </label>
              {fieldErrors.agreed && (
                <p className="text-xs text-destructive">{fieldErrors.agreed}</p>
              )}

              <Button type="submit" className="w-full h-10 rounded-2xl" disabled={loading}>
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    Create account <ArrowRight className="ml-1.5 h-4 w-4" />
                  </>
                )}
              </Button>
            </form>

            <p className="mt-6 text-center text-sm text-muted-foreground md:hidden">
              Already have an account?{" "}
              <Link href="/login" className="text-primary hover:underline">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}