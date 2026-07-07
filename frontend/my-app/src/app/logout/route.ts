import { NextRequest } from "next/server";
import { performLogout } from "@/lib/logout-server";

export async function GET(request: NextRequest) {
  return performLogout(request);
}
