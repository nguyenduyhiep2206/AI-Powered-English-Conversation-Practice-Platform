import Link from "next/link";
import AppHeader from "@/components/AppHeader";

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-[#F7F6F3] text-[#111111]">
      <AppHeader />
      <main className="mx-auto w-full max-w-3xl px-6 py-10 md:px-10">
        <Link
          href="/profile/settings"
          className="text-sm text-[#787774] underline-offset-4 hover:underline"
        >
          Back to settings
        </Link>
        <h1 className="mt-4 font-display text-3xl tracking-[-0.03em]">
          Terms and policies
        </h1>
        <p className="mt-4 text-sm leading-relaxed text-[#787774]">
          These pages are placeholders. Full terms of service and privacy policy
          will be published here before launch.
        </p>
      </main>
    </div>
  );
}
