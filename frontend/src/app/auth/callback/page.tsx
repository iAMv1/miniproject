"use client";

import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { setToken } from "@/lib/api";

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    // The backend returns credentials in the URL fragment, which is not sent
    // to servers, browser history referrers, or application logs. Support a
    // query token as a compatibility fallback for already-issued callbacks.
    const hashParams = new URLSearchParams(window.location.hash.slice(1));
    const oauthError = hashParams.get("error") || searchParams.get("error");
    const token = hashParams.get("token") || searchParams.get("token");
    const user = hashParams.get("user");
    const email = hashParams.get("email") || searchParams.get("email");

    if (oauthError) {
      router.replace(`/login?error=${encodeURIComponent(oauthError)}`);
      return;
    }

    if (!token) {
      router.replace("/login?error=missing_token");
      return;
    }

    setToken(token);
    if (user) {
      try {
        localStorage.setItem("mp_user", JSON.stringify(JSON.parse(user)));
      } catch {
        // A valid token is sufficient for the guarded app; user hydration will
        // refresh from /auth/me when a malformed compatibility payload occurs.
      }
    } else if (email) {
      localStorage.setItem("mp_user_email", email);
    }

    window.history.replaceState(null, "", window.location.pathname);
    router.replace("/tracking");
  }, [router, searchParams]);

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center">
      <div className="text-sm text-muted animate-pulse">Completing sign in...</div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-bg flex items-center justify-center">
          <div className="text-sm text-muted animate-pulse">Loading...</div>
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  );
}
