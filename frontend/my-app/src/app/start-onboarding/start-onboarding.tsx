import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Start your plan — EnglishFlow",
  description:
    "Set up your personalized English plan with a short survey. Placement is optional if you need help finding your level.",
  robots: { index: false, follow: false },
};

export default function StartOnboardingLayout({ children }: { children: React.ReactNode }) {
  return children;
}