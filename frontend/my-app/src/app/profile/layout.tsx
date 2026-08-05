import ProfileShell from "@/components/profile/ProfileShell";

export default function ProfileLayout({ children }: { children: React.ReactNode }) {
  return <ProfileShell>{children}</ProfileShell>;
}
