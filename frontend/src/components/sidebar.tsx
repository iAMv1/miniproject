"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/tracking", label: "Live Tracking", icon: "⚡" },
  { href: "/history", label: "History", icon: "📊" },
  { href: "/insights", label: "Insights", icon: "🔍" },
  { href: "/interventions", label: "Interventions", icon: "🧭" },
  { href: "/calibration", label: "Calibration", icon: "🎯" },
  { href: "/privacy", label: "Privacy", icon: "🔒" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 border-r border-border bg-surface flex flex-col">
      <div className="p-4 border-b border-border">
        <h1 className="text-xl font-bold text-accent">MindPulse</h1>
        <p className="text-xs text-muted mt-1">Stress Detection</p>
      </div>
      <nav className="flex-1 p-2 space-y-1">
        {NAV.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${
                active
                  ? "bg-accent/20 text-accent font-medium"
                  : "text-muted hover:bg-surface-hover hover:text-white"
              }`}
            >
              <span>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-3 border-t border-border text-xs text-muted">
        v1.0.0 · Privacy-first
      </div>
    </aside>
  );
}
