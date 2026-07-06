import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Create account — EnglishFlow",
  description: "Join EnglishFlow and start practicing English in real-world scenarios.",
};

export default function RegisterLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}