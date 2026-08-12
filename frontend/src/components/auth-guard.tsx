"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { supabase } from "@/lib/supabase";

const PUBLIC_PATHS = ["/login", "/signup"];

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (PUBLIC_PATHS.includes(pathname)) {
      setChecked(true);
      return;
    }

    supabase.auth.getSession().then(({ data }) => {
      if (!data.session) {
        router.replace("/login");
        return;
      }
      setChecked(true);
    });
  }, [pathname, router]);

  if (!checked) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <div className="text-sm text-muted animate-pulse">Loading...</div>
      </div>
    );
  }

  return <>{children}</>;
}
