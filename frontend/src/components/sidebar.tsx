"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { clearToken } from "@/lib/api";
import { Activity, Clock, Lightbulb, Heart, Shield, Eye, MessageSquare, Sparkles, Target } from "lucide-react";

const NAV = [
  { href: "/tracking", label: "Rhythm", icon: Activity },
  { href: "/history", label: "History", icon: Clock },
  { href: "/insights", label: "Insights", icon: Lightbulb },
  { href: "/interventions", label: "Guidance", icon: Heart },
  { href: "/calibration", label: "Calibration", icon: Shield },
  { href: "/privacy", label: "Privacy", icon: Eye },
];

const NEW_FEATURES = [
  { href: "/chat", label: "Ask MindPulse", icon: MessageSquare },
  { href: "/wellness", label: "Wellness", icon: Sparkles },
  { href: "/focus", label: "Focus & Flow", icon: Target },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [user, setUser] = useState<{ display_name: string; email: string } | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("mp_user");
    if (stored) {
      try { setUser(JSON.parse(stored)); } catch { setUser(null); }
    }
  }, []);

  const handleLogout = () => {
    clearToken();
    localStorage.removeItem("mp_user");
    window.location.href = "/login";
  };

  return (
    <aside className="app-sidebar sticky top-0 z-30 flex h-dvh w-56 flex-shrink-0 flex-col border-r border-[rgba(142,153,178,0.16)] bg-[rgba(8,10,18,0.82)] backdrop-blur-xl max-md:w-[4.5rem]" aria-label="Primary navigation">
      <div className="border-b border-[rgba(142,153,178,0.16)] px-4 py-5 max-md:px-2">
        <div className="flex items-center gap-3">
          <svg viewBox="0 0 40 40" className="w-8 h-8" fill="none">
            <defs>
              <linearGradient id="sideLogoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#5b4fc4" />
                <stop offset="100%" stopColor="#8b7fd4" />
              </linearGradient>
            </defs>
            <circle cx="20" cy="20" r="17" stroke="url(#sideLogoGrad)" strokeWidth="1" opacity="0.4" />
            <path d="M 6 20 L 13 20 L 15 20 L 17 14 L 19 26 L 21 10 L 23 24 L 25 17 L 27 20 L 34 20" stroke="url(#sideLogoGrad)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
            <circle cx="20" cy="20" r="2" fill="url(#sideLogoGrad)" />
          </svg>
          <div className="max-md:hidden">
            <div className="text-sm font-semibold tracking-tight text-[#F4F6FB]">MindPulse</div>
            <p className="text-[10px] text-[#8E99B2]">rhythm, understood</p>
          </div>
        </div>
      </div>
      <nav className="flex-1 space-y-0.5 px-2 py-4" aria-label="MindPulse sections">
        {NAV.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 ${
                active ? "bg-[#8b7cf6]/15 text-[#b8b1ff] font-medium shadow-[inset_3px_0_0_#8b7cf6]" : "text-[#8e99b2] hover:bg-[#192038] hover:text-[#f4f6fb]"
              }`}
            >
              <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="max-md:hidden">{item.label}</span>
            </Link>
          );
        })}
        <div className="pt-3 pb-1 px-3">
          <div className="text-[9px] uppercase tracking-[0.2em] text-[#8e99b2]/45 max-md:hidden">More</div>
        </div>
        {NEW_FEATURES.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 ${
                active ? "bg-[#8b7cf6]/15 text-[#b8b1ff] font-medium shadow-[inset_3px_0_0_#8b7cf6]" : "text-[#8e99b2] hover:bg-[#192038] hover:text-[#f4f6fb]"
              }`}
            >
              <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="max-md:hidden">{item.label}</span>
            </Link>
          );
        })}
      </nav>
      {user && (
        <div className="relative border-t border-[rgba(142,153,178,0.16)] px-3 py-3 max-md:px-2">
          <button onClick={() => setMenuOpen(!menuOpen)} className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-[#141420] transition text-left">
            <div className="w-7 h-7 rounded-full bg-[#5b4fc4]/20 flex items-center justify-center text-[#5b4fc4] text-xs font-semibold">{user.display_name.charAt(0).toUpperCase()}</div>
            <div className="min-w-0 flex-1 max-md:hidden">
              <div className="text-xs font-medium text-[#F2EFE9] truncate">{user.display_name}</div>
              <div className="text-[10px] text-[#857F75] truncate">{user.email}</div>
            </div>
          </button>
          {menuOpen && (
            <div className="absolute bottom-14 left-2 right-2 z-50 rounded-xl border border-[rgba(142,153,178,0.2)] bg-[#111626] p-1 shadow-2xl">
              <button onClick={handleLogout} className="w-full text-left px-3 py-2 text-xs text-[#dc2626] hover:bg-[#1c1c2e] rounded-md transition">Sign out</button>
            </div>
          )}
        </div>
      )}
      {!user && (
        <div className="border-t border-[rgba(142,153,178,0.16)] px-3 py-3 max-md:px-2">
          <Link href="/login" className="block px-3 py-2 rounded-md text-xs font-medium text-[#5b4fc4] hover:bg-[#5b4fc4]/10 transition text-center">Sign in</Link>
        </div>
      )}
    </aside>
  );
}
