"use client";

import { useRouter } from "next/navigation";
import {
  ArrowUpRight,
  Check,
  ChevronRight,
  EyeOff,
  MousePointer2,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { ScrollRhythm } from "@/components/scroll-rhythm";
import {
  LandingReveal,
  LandingStagger,
  LandingStaggerItem,
  NarrativeOrbit,
  ScrollProgress,
  SectionWave,
} from "@/components/landing-motion";

function Brand() {
  return (
    <div className="flex items-center gap-2.5" aria-label="MindPulse">
      <span className="grid h-9 w-9 place-items-center rounded-xl border border-white/10 bg-white/[0.04] shadow-[0_12px_28px_rgba(98,85,213,0.16)]">
        <svg viewBox="0 0 32 32" className="h-5 w-5" fill="none" aria-hidden="true">
          <path d="M3 16h5l2.5-6 4.2 13 3.4-16 3.1 12 2.4-5H29" stroke="#B9B3FF" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
      <span className="text-sm font-semibold tracking-[-0.035em] text-white">MindPulse</span>
    </div>
  );
}

const principles = [
  {
    icon: <MousePointer2 className="h-5 w-5" />,
    title: "Observe rhythm, not content",
    body: "The product works from behavioral timing and interaction patterns. It is not a screen recorder or a text reader.",
  },
  {
    icon: <EyeOff className="h-5 w-5" />,
    title: "Refuse weak conclusions",
    body: "If the current input is limited or the baseline is still learning, the dashboard says so instead of filling the space with a score.",
  },
  {
    icon: <ShieldCheck className="h-5 w-5" />,
    title: "Keep control in the product",
    body: "Tracking can be paused, and stored behavioral data can be exported or deleted from the privacy controls.",
  },
];

const states = [
  { label: "Waiting", body: "Nothing useful has been measured in the current window.", color: "text-[#A9B3CB]", edge: "border-white/10" },
  { label: "Insufficient activity", body: "Quiet activity is not interpreted as calm, focused, or low strain.", color: "text-[#EFC277]", edge: "border-[#EFC277]/20" },
  { label: "Calibrating", body: "An early pattern is visible while the personal baseline learns.", color: "text-[#B9B3FF]", edge: "border-[#B9B3FF]/20" },
  { label: "Ready", body: "A personalized trend is shown only when its context is established.", color: "text-[#72DDB6]", edge: "border-[#72DDB6]/20" },
];

export default function LandingPage() {
  const router = useRouter();
  const start = () => router.push("/signup");

  return (
    <main className="min-h-screen overflow-hidden bg-[#080A12] text-white">
      <ScrollProgress />
      <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(circle_at_14%_0%,rgba(109,96,232,0.18),transparent_27rem),radial-gradient(circle_at_88%_12%,rgba(72,194,150,0.12),transparent_23rem),linear-gradient(180deg,#080A12_0%,#0C1020_54%,#080A12_100%)]" />
      <div className="pointer-events-none fixed inset-0 -z-10 opacity-[0.035] [background-image:linear-gradient(rgba(255,255,255,.9)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.9)_1px,transparent_1px)] [background-size:48px_48px]" />
      <ScrollRhythm />

      <nav className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 lg:px-8">
        <Brand />
        <div className="hidden items-center gap-7 text-xs text-[#A9B3CB] md:flex">
          <a href="#principles" className="transition-colors duration-150 hover:text-white">Principles</a>
          <a href="#states" className="transition-colors duration-150 hover:text-white">Signal states</a>
          <a href="#privacy" className="transition-colors duration-150 hover:text-white">Privacy</a>
        </div>
        <button onClick={start} className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.05] px-4 py-2 text-xs font-medium text-white transition-[transform,background-color,border-color] duration-150 ease-out hover:border-white/25 hover:bg-white/[0.09] active:scale-[0.97]">
          Get started <ArrowUpRight className="h-3.5 w-3.5" />
        </button>
      </nav>

      <section className="mx-auto grid min-h-[calc(100vh-76px)] max-w-7xl items-center gap-12 px-5 pb-24 pt-16 lg:grid-cols-[1.08fr_.92fr] lg:px-8 lg:pb-28 lg:pt-20">
        <LandingReveal>
          <div>
            <p className="inline-flex items-center gap-2 rounded-full border border-[#B9B3FF]/22 bg-[#B9B3FF]/[0.07] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#D1CDFF]">
              <Sparkles className="h-3 w-3" /> Behavioral awareness, with context
            </p>
            <h1 className="mt-7 max-w-3xl text-5xl font-medium leading-[0.98] tracking-[-0.075em] text-[#F6F7FB] sm:text-6xl lg:text-7xl">
              A clearer relationship with your <span className="bg-gradient-to-r from-[#C9C4FF] to-[#72DDB6] bg-clip-text text-transparent">workday.</span>
            </h1>
            <p className="mt-7 max-w-xl text-base leading-7 text-[#A9B3CB] sm:text-lg">
              MindPulse notices changes in interaction rhythm, then makes its limits visible. It does not label an empty window, turn a quiet moment into a conclusion, or pretend a new pattern is a personal truth.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <button onClick={start} className="inline-flex items-center gap-3 rounded-full bg-[#F6F7FB] px-5 py-3.5 text-sm font-semibold text-[#0A0C14] transition-[transform,background-color] duration-150 ease-out hover:bg-white active:scale-[0.97]">
                Create a private baseline <ArrowUpRight className="h-4 w-4" />
              </button>
              <a href="#principles" className="inline-flex items-center gap-2 rounded-full border border-white/12 px-5 py-3.5 text-sm font-medium text-[#D8DDED] transition-[transform,background-color,border-color] duration-150 ease-out hover:border-white/25 hover:bg-white/[0.04] active:scale-[0.97]">
                How it works <ChevronRight className="h-4 w-4" />
              </a>
            </div>
            <div className="mt-12 flex flex-wrap gap-x-6 gap-y-3 border-t border-white/10 pt-6 text-xs text-[#8B96B1]">
              <span className="inline-flex items-center gap-2"><Check className="h-3.5 w-3.5 text-[#72DDB6]" /> Typed content is not persisted</span>
              <span className="inline-flex items-center gap-2"><Check className="h-3.5 w-3.5 text-[#72DDB6]" /> Pause, export, and delete controls</span>
            </div>
          </div>
        </LandingReveal>
        <LandingReveal className="relative">
          <div className="absolute -inset-10 rounded-full bg-[#7668EC]/10 blur-3xl" />
          <div className="relative grid min-h-[28rem] place-items-center overflow-hidden rounded-[2rem] border border-white/10 bg-[#101526]/72 p-6 shadow-[0_28px_80px_rgba(0,0,0,0.35)] backdrop-blur-xl sm:p-8">
            <NarrativeOrbit />
            <div className="absolute inset-x-7 bottom-7 border-t border-white/10 pt-5 text-center">
              <p className="text-sm font-medium text-[#EEF0F7]">Context before conclusion.</p>
              <p className="mx-auto mt-2 max-w-sm text-xs leading-5 text-[#8F9AB5]">MindPulse makes the quality of the current input visible before it offers guidance.</p>
            </div>
          </div>
        </LandingReveal>
      </section>

      <SectionWave />
      <section id="principles" className="bg-white/[0.018]">
        <div className="mx-auto max-w-7xl px-5 py-24 lg:px-8 lg:py-32">
          <LandingReveal className="max-w-2xl">
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#B9B3FF]">Designed around context</p>
            <h2 className="mt-4 text-3xl font-medium tracking-[-0.055em] text-white sm:text-5xl">The product should feel calm because it is honest.</h2>
            <p className="mt-5 text-base leading-7 text-[#A9B3CB]">Every part of MindPulse is designed to reduce the gap between what the interface suggests and what the system can actually know.</p>
          </LandingReveal>
          <LandingStagger className="mt-12 grid gap-4 md:grid-cols-3">
            {principles.map((item) => (
              <LandingStaggerItem key={item.title} className="landing-motion-card rounded-3xl border border-white/10 bg-[#101526]/70 p-6">
                <span className="grid h-10 w-10 place-items-center rounded-xl bg-white/[0.05] text-[#C9C4FF]">{item.icon}</span>
                <h3 className="mt-8 text-lg font-semibold tracking-[-0.03em] text-white">{item.title}</h3>
                <p className="mt-3 text-sm leading-6 text-[#9CA8C3]">{item.body}</p>
              </LandingStaggerItem>
            ))}
          </LandingStagger>
        </div>
      </section>

      <SectionWave />
      <section id="states" className="relative overflow-hidden">
        <div className="pointer-events-none absolute left-1/2 top-0 h-[36rem] w-[36rem] -translate-x-1/2 rounded-full bg-[#62D8AC]/[0.045] blur-3xl" />
        <div className="relative mx-auto grid max-w-7xl gap-12 px-5 py-24 lg:grid-cols-[.82fr_1.18fr] lg:px-8 lg:py-32">
          <LandingReveal>
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#72DDB6]">Signal integrity</p>
            <h2 className="mt-4 text-3xl font-medium tracking-[-0.055em] text-white sm:text-5xl">A dashboard that knows when to wait.</h2>
            <p className="mt-5 max-w-xl text-base leading-7 text-[#A9B3CB]">The dashboard uses explicit signal states. This makes a quiet window, an early pattern, and a ready personal trend visibly different experiences.</p>
            <button onClick={start} className="mt-8 inline-flex items-center gap-2 text-sm font-semibold text-[#D1CDFF] transition-[transform,color] duration-150 ease-out hover:text-white active:scale-[0.97]">See your own state <ArrowUpRight className="h-4 w-4" /></button>
          </LandingReveal>
          <LandingStagger className="grid gap-3 sm:grid-cols-2">
            {states.map((state) => (
              <LandingStaggerItem key={state.label} className={`landing-motion-card rounded-2xl border ${state.edge} bg-[#101526]/65 p-5`}>
                <span className={`text-[10px] font-semibold uppercase tracking-[0.16em] ${state.color}`}>{state.label}</span>
                <p className="mt-4 text-sm leading-6 text-[#A9B3CB]">{state.body}</p>
                <span className="motion-line mt-7 block h-px w-8 bg-white/10" />
              </LandingStaggerItem>
            ))}
          </LandingStagger>
        </div>
      </section>

      <SectionWave />
      <section id="privacy" className="bg-[#0B0F1B]">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-24 lg:grid-cols-[1.05fr_.95fr] lg:px-8 lg:py-32">
          <LandingReveal>
            <div className="landing-motion-card relative overflow-hidden rounded-[2rem] border border-white/10 bg-[linear-gradient(145deg,rgba(112,99,237,.16),rgba(16,21,38,.9)_48%,rgba(16,21,38,.72))] p-7 sm:p-9">
              <div className="pointer-events-none absolute -right-14 -top-14 h-44 w-44 rounded-full border border-[#B9B3FF]/15" />
              <span className="relative grid h-11 w-11 place-items-center rounded-xl bg-white/[0.07] text-[#C9C4FF]"><ShieldCheck className="h-5 w-5" /></span>
              <h2 className="relative mt-14 text-3xl font-medium tracking-[-0.055em] text-white sm:text-4xl">Private by design. Clear by default.</h2>
              <p className="relative mt-5 max-w-md text-sm leading-7 text-[#A9B3CB]">MindPulse explains the behavioral data it stores and puts the controls where you can use them. Nothing needs to be taken on faith.</p>
              <LandingStagger className="relative mt-10 space-y-3">
                {["Typed content is not persisted", "Collection can be paused on this device", "Export and deletion are available in-product"].map((item) => (
                  <LandingStaggerItem key={item} className="flex items-center gap-3 text-sm text-[#DBE0EE]"><span className="grid h-5 w-5 place-items-center rounded-full bg-[#72DDB6]/10 text-[#72DDB6]"><Check className="h-3 w-3" /></span>{item}</LandingStaggerItem>
                ))}
              </LandingStagger>
            </div>
          </LandingReveal>
          <LandingReveal className="flex flex-col justify-center">
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#B9B3FF]">For the everyday workday</p>
            <h2 className="mt-4 text-3xl font-medium tracking-[-0.055em] text-white sm:text-5xl">Make room to notice your own pace.</h2>
            <p className="mt-5 max-w-xl text-base leading-7 text-[#A9B3CB]">A quieter tool for people who want reflection without surveillance, diagnosis, or a productivity contest.</p>
            <div className="mt-9 flex flex-wrap gap-3">
              <button onClick={start} className="inline-flex items-center gap-2 rounded-full bg-[#7668EC] px-5 py-3.5 text-sm font-semibold text-white transition-[transform,background-color] duration-150 ease-out hover:bg-[#8A7FF1] active:scale-[0.97]">Start with your baseline <ArrowUpRight className="h-4 w-4" /></button>
              <a href="#principles" className="inline-flex items-center gap-2 rounded-full border border-white/12 px-5 py-3.5 text-sm text-[#DBE0EE] transition-[transform,background-color,border-color] duration-150 ease-out hover:border-white/25 hover:bg-white/[0.04] active:scale-[0.97]">Read the principles</a>
            </div>
          </LandingReveal>
        </div>
      </section>

      <SectionWave />
      <LandingReveal>
        <footer className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-10 text-xs text-[#7C88A4] sm:flex-row sm:items-center sm:justify-between lg:px-8">
          <Brand />
          <div className="flex flex-wrap gap-x-5 gap-y-2"><span>MindPulse</span><span>Behavioral signals, not diagnoses</span><span>Privacy controls included</span></div>
        </footer>
      </LandingReveal>
    </main>
  );
}
