import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sign in — EnglishFlow",
  description: "Sign in to continue your English conversation practice.",
};

export default function LoginLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}