import { NextRequest, NextResponse } from "next/server";

const backendBase = process.env.NEXT_PUBLIC_API_URL;
if (!backendBase) {
  if (process.env.NODE_ENV !== "development") {
    throw new Error("NEXT_PUBLIC_API_URL environment variable must be set in non-development environments.");
  }
  console.warn("[Google OAuth] NEXT_PUBLIC_API_URL is not set; falling back to http://localhost:5000/api/v1");
}
const backendUrl = backendBase || "http://localhost:5000/api/v1";

/**
 * Compatibility bridge for Google OAuth clients that still register the
 * frontend callback URL. The browser, rather than the Next.js server, is
 * redirected to the backend callback so the backend receives its HttpOnly
 * OAuth state cookie and can validate the authorization response.
 */
export function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const error = searchParams.get("error");
  const code = searchParams.get("code");
  const state = searchParams.get("state");

  if (error) {
    return NextResponse.redirect(
      new URL(`/login?error=${encodeURIComponent(error)}`, request.url)
    );
  }

  if (!code || !state) {
    return NextResponse.redirect(new URL("/login?error=missing_oauth_response", request.url));
  }

  const callbackUrl = new URL(`${backendUrl}/auth/google/callback`);
  callbackUrl.searchParams.set("code", code);
  callbackUrl.searchParams.set("state", state);
  return NextResponse.redirect(callbackUrl);
}
