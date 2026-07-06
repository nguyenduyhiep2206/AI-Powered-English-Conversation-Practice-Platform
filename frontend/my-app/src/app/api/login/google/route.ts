import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_URL;

function extractErrorMessage(error: unknown): string {
  if (!error || typeof error !== "object") return "Sign in with Google failed";
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
  return "Sign in with Google failed";
}

export async function POST(request: NextRequest) {
  try {
    const { credential } = await request.json();

    const res = await fetch(`${API_URL}/api/v1/auth/google`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ credential }),
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      return NextResponse.json(
        { message: extractErrorMessage(error) },
        { status: res.status }
      );
    }

    const data = await res.json(); // { access_token, refresh_token, token_type }

    const response = NextResponse.json({ success: true });

    response.cookies.set("token", data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24 * 7,
    });

    if (data.refresh_token) {
      response.cookies.set("refresh_token", data.refresh_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        path: "/",
        maxAge: 60 * 60 * 24 * 30,
      });
    }

    return response;
  } catch (err) {
    return NextResponse.json(
      { message: "An error occurred, please try again" },
      { status: 500 }
    );
  }
}