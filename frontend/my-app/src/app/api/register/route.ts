import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_URL;

function extractErrorMessage(error: unknown): string {
  if (!error || typeof error !== "object") return "Registration failed";

  const detail = (error as { detail?: unknown }).detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    return (
      detail
        .map((item) => (typeof item === "string" ? item : item?.msg))
        .filter(Boolean)
        .join(", ") || "Data validation error"
    );
  }

  return "Registration failed";
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json(); // { name, username, email, password }

    const res = await fetch(`${API_URL}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      return NextResponse.json(
        { message: extractErrorMessage(error) },
        { status: res.status }
      );
    }

    const data = await res.json();

    return NextResponse.json({ success: true, ...data });
  } catch (err) {
    return NextResponse.json(
      { message: "An error occurred, please try again" },
      { status: 500 }
    );
  }
}