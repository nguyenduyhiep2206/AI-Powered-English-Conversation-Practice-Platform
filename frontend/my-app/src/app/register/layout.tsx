import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-register",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Create account — EnglishFlow",
  description:
    "Join EnglishFlow and start practicing English in real-world scenarios.",
};

export default function RegisterLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div
      className={`${jakarta.variable} font-[family-name:var(--font-register)]`}
    >
      {children}
    </div>
  );
}
