import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_URL;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json(); // { email, password }
    const payload = {
      identifier: body.identifier ?? body.email,
      password: body.password,
    };

    const res = await fetch(`${API_URL}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      return NextResponse.json(
        { message: error.detail || "Login failed" },
        { status: res.status }
      );
    }

    const data = await res.json(); // { access_token: "..." }

    const response = NextResponse.json({ success: true });

    response.cookies.set("token", data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24 * 7,
    });

    return response;
  } catch (err) {
    return NextResponse.json(
      { message: "An error occurred, please try again" },
      { status: 500 }
    );
  }
}