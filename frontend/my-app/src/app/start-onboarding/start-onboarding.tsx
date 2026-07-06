import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Start your plan — EnglishFlow",
  description: "Set up your personalized English learning plan in about 5–7 minutes.",
  robots: { index: false, follow: false },
};

export default function StartOnboardingLayout({ children }: { children: React.ReactNode }) {
  return children;
}