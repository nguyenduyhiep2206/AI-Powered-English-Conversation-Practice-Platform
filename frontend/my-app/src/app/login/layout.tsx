import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-login",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Sign in — EnglishFlow",
  description: "Sign in to continue your English conversation practice.",
};

export default function LoginLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <div className={`${jakarta.variable} font-[family-name:var(--font-login)]`}>{children}</div>;
}
