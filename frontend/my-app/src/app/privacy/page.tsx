import Link from "next/link";

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[#FFF5EB] text-[#1F1B15]">
      <main className="mx-auto w-full max-w-3xl px-6 py-10 md:px-10">
        <Link
          href="/register"
          className="text-[0.875rem] font-medium text-[#9A3412] underline-offset-4 hover:text-[#E85D04] hover:underline"
        >
          Back to create account
        </Link>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight">
          Privacy Policy
        </h1>
        <p className="mt-4 text-[0.9375rem] leading-relaxed text-[#6B6258]">
          This page is a placeholder. The full Privacy Policy will be published
          here before launch. Until then, contact{" "}
          <a
            href="mailto:support@englishflow.app"
            className="font-medium text-[#9A3412] underline-offset-2 hover:underline"
          >
            support@englishflow.app
          </a>{" "}
          with any privacy questions.
        </p>
        <p className="mt-6 text-[0.875rem] text-[#8A8178]">
          See also{" "}
          <Link
            href="/terms"
            className="font-medium text-[#9A3412] underline-offset-2 hover:underline"
          >
            Terms and policies
          </Link>
          .
        </p>
      </main>
    </div>
  );
}
