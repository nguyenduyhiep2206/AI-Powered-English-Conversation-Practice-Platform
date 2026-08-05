"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import SkillWorkspace from "@/components/admin/SkillWorkspace";

export default function AdminSkillWorkspacePage() {
  const params = useParams();
  const skillId = Number(params.skillId);

  if (!Number.isFinite(skillId) || skillId <= 0) {
    return (
      <p className="p-6 text-sm text-[#9F2F2D]">
        Invalid skill.{" "}
        <Link href="/admin/skills" className="underline">
          Back to skills
        </Link>
      </p>
    );
  }

  return (
    <>
      <div className="border-b border-border px-6 py-3">
        <Link
          href="/admin/skills"
          className="text-sm text-[#1F6C9F] underline-offset-2 hover:underline"
        >
          ← All skills
        </Link>
      </div>
      <SkillWorkspace skillId={skillId} />
    </>
  );
}
