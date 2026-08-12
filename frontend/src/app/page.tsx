"use client";

import { useRouter } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";
import { ScrollRhythm } from "@/components/scroll-rhythm";
import {
  ArrowUpRight,
  Check,
  ChevronRight,
  CircleDot,
  EyeOff,
  MousePointer2,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

const EASE_OUT = [0.23, 1, 0.32, 1] as const;

const reveal = (delay = 0) => ({
  initial: { opacity: 0, transform: "translateY(14px)" },
  animate: { opacity: 1, transform: "translateY(0px)" },
  transition: { duration: 0.56, delay, ease: EASE_OUT },
});

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

function QuietOrbit() {
  const shouldReduceMotion = useReducedMotion();
  const orbitTransition = { duration: 26, repeat: Infinity, ease: "linear" as const };
  return (
    <div className="relative mx-auto grid aspect-square w-full max-w-[30rem] place-items-center" aria-hidden="true">
      <motion.div className="absolute inset-[10%] rounded-full border border-[#b9b3ff]/10" animate={shouldReduceMotion ? undefined : { rotate: 360 }} transition={orbitTransition} />
      <motion.div className="absolute inset-[20%] rounded-full border border-[#b9b3ff]/15" animate={shouldReduceMotion ? undefined : { rotate: -360 }} transition={{ ...orbitTransition, duration: 19 }} />
      <motion.div className="absolute inset-[31%] rounded-full border border-[#62d8ac]/20" animate={shouldReduceMotion ? undefined : { scale: [1, 1.04, 1], opacity: [0.55, 1, 0.55] }} transition={{ duration: 5.5, repeat: Infinity, ease: "easeInOut" }} />
      <motion.div className="absolute inset-[42%] rounded-full border border-white/10 bg-[#111628]/80 shadow-[0_0_80px_rgba(115,101,237,0.20)]" animate={shouldReduceMotion ? undefined : { scale: [1, 1.025, 1] }} transition={{ duration: 4.2, repeat: Infinity, ease: "easeInOut" }} />
      <div className="absolute h-[58%] w-px bg-gradient-to-b from-transparent via-[#b9b3ff]/55 to-transparent" />
      <div className="absolute h-px w-[58%] bg-gradient-to-r from-transparent via-[#62d8ac]/45 to-transparent" />
      <div className="relative flex max-w-[12rem] flex-col items-center text-center">
        <span className="mb-4 grid h-11 w-11 place-items-center rounded-2xl border border-white/10 bg-white/[0.04] text-[#C9C4FF]"><CircleDot className="h-5 w-5" /></span>
        <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#B9B3FF]">A quieter signal</span>
        <span className="mt-3 text-sm leading-6 text-[#A9B3CB]">Designed to wait for context before it says anything.</span>
      </div>
      <motion.span className="absolute left-[13%] top-[27%] h-2 w-2 rounded-full bg-[#B9B3FF] shadow-[0_0_16px_rgba(185,179,255,0.9)]" animate={shouldReduceMotion ? undefined : { transform: ["translate3d(0,0,0)", "translate3d(10px,-8px,0)", "translate3d(0,0,0)"] }} transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut" }} />
      <motion.span className="absolute bottom-[22%] right-[18%] h-2 w-2 rounded-full bg-[#62D8AC] shadow-[0_0_16px_rgba(98,216,172,0.8)]" animate={shouldReduceMotion ? undefined : { transform: ["translate3d(0,0,0)", "translate3d(-8px,9px,0)", "translate3d(0,0,0)"] }} transition={{ duration: 5.4, repeat: Infinity, ease: "easeInOut" }} />
    </div>
  );
}

const states = [
  {
    label: "Waiting",
    body: "Nothing useful has been measured in the current window.",
    color: "text-[#A9B3CB]",
  },
  {
    label: "Insufficient activity",
    body: "Quiet activity is not interpreted as calm, focused, or low strain.",
    color: "text-[#EFC277]",
  },
  {
    label: "Calibrating",
    body: "An early pattern is visible while the personal baseline learns.",
    color: "text-[#B9B3FF]",
  },
  {
    label: "Ready",
    body: "A personalized trend is shown only when its context is established.",
    color: "text-[#62D8AC]",
  },
];

export default function LandingPage() {
  const router = useRouter();
  const start = () => router.push("/signup");

  return (
    <main className="min-h-screen overflow-hidden bg-[#080A12] text-white">
      <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(circle_at_14%_0%,rgba(109,96,232,0.16),transparent_27rem),radial-gradient(circle_at_88%_12%,rgba(72,194,150,0.10),transparent_23rem),linear-gradient(180deg,#080A12_0%,#0C1020_54%,#080A12_100%)]" />
      <div className="pointer-events-none fixed inset-0 -z-10 opacity-[0.035] [background-image:linear-gradient(rgba(255,255,255,.9)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.9)_1px,transparent_1px)] [background-size:48px_48px]" />
      <ScrollRhythm />

      <nav className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 lg:px-8">
        <Brand />
        <div className="hidden items-center gap-7 text-xs text-[#A9B3CB] md:flex">
          <a href="#principles" className="transition-colors hover:text-white">Principles</a>
          <a href="#states" className="transition-colors hover:text-white">Signal states</a>
          <a href="#privacy" className="transition-colors hover:text-white">Privacy</a>
        </div>
        <button onClick={start} className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.05] px-4 py-2 text-xs font-medium text-white transition-[transform,background-color,border-color] duration-150 ease-out hover:border-white/25 hover:bg-white/[0.09] active:scale-[0.97]">
          Get started <ArrowUpRight className="h-3.5 w-3.5" />
        </button>
      </nav>

      <section className="mx-auto grid max-w-7xl items-center gap-12 px-5 pb-24 pt-16 lg:grid-cols-[1.08fr_.92fr] lg:px-8 lg:pb-32 lg:pt-24">
        <div>
          <motion.p {...reveal(0)} className="inline-flex items-center gap-2 rounded-full border border-[#B9B3FF]/22 bg-[#B9B3FF]/[0.07] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#D1CDFF]">
            <Sparkles className="h-3 w-3" /> Behavioral awareness, with context
          </motion.p>
          <motion.h1 {...reveal(0.07)} className="mt-7 max-w-3xl text-5xl font-medium leading-[0.98] tracking-[-0.075em] text-[#F6F7FB] sm:text-6xl lg:text-7xl">
            A clearer relationship with your <span className="bg-gradient-to-r from-[#C9C4FF] to-[#72DDB6] bg-clip-text text-transparent">workday.</span>
          </motion.h1>
          <motion.p {...reveal(0.14)} className="mt-7 max-w-xl text-base leading-7 text-[#A9B3CB] sm:text-lg">
            MindPulse notices changes in interaction rhythm, then makes its limits visible. It does not label an empty window, turn a quiet moment into a conclusion, or pretend a new pattern is a personal truth.
          </motion.p>
          <motion.div {...reveal(0.21)} className="mt-9 flex flex-wrap gap-3">
            <button onClick={start} className="inline-flex items-center gap-3 rounded-full bg-[#F6F7FB] px-5 py-3.5 text-sm font-semibold text-[#0A0C14] transition-[transform,background-color] duration-150 ease-out hover:bg-white active:scale-[0.97]">
              Create a private baseline <ArrowUpRight className="h-4 w-4" />
            </button>
            <a href="#principles" className="inline-flex items-center gap-2 rounded-full border border-white/12 px-5 py-3.5 text-sm font-medium text-[#D8DDED] transition-[transform,background-color,border-color] duration-150 ease-out hover:border-white/25 hover:bg-white/[0.04] active:scale-[0.97]">
              How it works <ChevronRight className="h-4 w-4" />
            </a>
          </motion.div>
          <motion.div {...reveal(0.29)} className="mt-12 flex flex-wrap gap-x-6 gap-y-3 border-t border-white/10 pt-6 text-xs text-[#8B96B1]">
            <span className="inline-flex items-center gap-2"><Check className="h-3.5 w-3.5 text-[#62D8AC]" /> Typed content is not persisted</span>
            <span className="inline-flex items-center gap-2"><Check className="h-3.5 w-3.5 text-[#62D8AC]" /> Pause, export, and delete controls</span>
          </motion.div>
        </div>
        <motion.div {...reveal(0.12)} className="relative">
          <div className="absolute -inset-10 rounded-full bg-[#7668EC]/10 blur-3xl" />
          <div className="relative rounded-[2rem] border border-white/10 bg-[#101526]/72 p-6 shadow-[0_28px_80px_rgba(0,0,0,0.35)] backdrop-blur-xl sm:p-8">
            <QuietOrbit />
            <div className="mt-3 border-t border-white/10 pt-5 text-center">
              <p className="text-sm font-medium text-[#EEF0F7]">Context before conclusion.</p>
              <p className="mx-auto mt-2 max-w-sm text-xs leading-5 text-[#8F9AB5]">MindPulse makes the quality of the current input visible before it offers guidance.</p>
            </div>
          </div>
        </motion.div>
      </section>

      <section id="principles" className="border-y border-white/[0.08] bg-white/[0.02]">
        <div className="mx-auto max-w-7xl px-5 py-20 lg:px-8 lg:py-28">
          <motion.div {...reveal()} className="max-w-2xl">
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#B9B3FF]">Designed around context</p>
            <h2 className="mt-4 text-3xl font-medium tracking-[-0.055em] text-white sm:text-5xl">The product should feel calm because it is honest.</h2>
            <p className="mt-5 text-base leading-7 text-[#A9B3CB]">Every part of MindPulse is designed to reduce the gap between what the interface suggests and what the system can actually know.</p>
          </motion.div>
          <div className="mt-12 grid gap-4 md:grid-cols-3">
            {[
              { icon: <MousePointer2 className="h-5 w-5" />, title: "Observe rhythm, not content", body: "The product works from behavioral timing and interaction patterns. It is not a screen recorder or a text reader." },
              { icon: <EyeOff className="h-5 w-5" />, title: "Refuse weak conclusions", body: "If the current input is limited or the baseline is still learning, the dashboard says so instead of filling the space with a score." },
              { icon: <ShieldCheck className="h-5 w-5" />, title: "Keep control in the product", body: "Tracking can be paused, and stored behavioral data can be exported or deleted from the privacy controls." },
            ].map((item, index) => (
              <motion.article key={item.title} {...reveal(index * 0.07)} className="rounded-3xl border border-white/10 bg-[#101526]/70 p-6 transition-[transform,border-color,background-color] duration-200 ease-out hover:-translate-y-1 hover:border-[#B9B3FF]/28 hover:bg-[#141A2E]">
                <span className="grid h-10 w-10 place-items-center rounded-xl bg-white/[0.05] text-[#C9C4FF]">{item.icon}</span>
                <h3 className="mt-8 text-lg font-semibold tracking-[-0.03em] text-white">{item.title}</h3>
                <p className="mt-3 text-sm leading-6 text-[#9CA8C3]">{item.body}</p>
              </motion.article>
            ))}
          </div>
        </div>
      </section>

      <section id="states" className="mx-auto max-w-7xl px-5 py-20 lg:px-8 lg:py-28">
        <div className="grid gap-12 lg:grid-cols-[.82fr_1.18fr] lg:items-start">
          <motion.div {...reveal()}>
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#62D8AC]">Signal integrity</p>
            <h2 className="mt-4 text-3xl font-medium tracking-[-0.055em] text-white sm:text-5xl">A dashboard that knows when to wait.</h2>
            <p className="mt-5 max-w-xl text-base leading-7 text-[#A9B3CB]">The dashboard uses explicit signal states. This makes a quiet window, an early pattern, and a ready personal trend visibly different experiences.</p>
            <button onClick={start} className="mt-8 inline-flex items-center gap-2 text-sm font-semibold text-[#D1CDFF] transition-colors hover:text-white">See your own state <ArrowUpRight className="h-4 w-4" /></button>
          </motion.div>
          <motion.div {...reveal(0.08)} className="grid gap-3 sm:grid-cols-2">
            {states.map((state) => (
              <article key={state.label} className="rounded-2xl border border-white/10 bg-[#101526]/65 p-5">
                <span className={`text-[10px] font-semibold uppercase tracking-[0.16em] ${state.color}`}>{state.label}</span>
                <p className="mt-4 text-sm leading-6 text-[#A9B3CB]">{state.body}</p>
              </article>
            ))}
          </motion.div>
        </div>
      </section>

      <section id="privacy" className="border-t border-white/[0.08] bg-[#0B0F1B]">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-20 lg:grid-cols-[1.05fr_.95fr] lg:px-8 lg:py-28">
          <motion.div {...reveal()} className="rounded-[2rem] border border-white/10 bg-[linear-gradient(145deg,rgba(112,99,237,.16),rgba(16,21,38,.9)_48%,rgba(16,21,38,.72))] p-7 sm:p-9">
            <span className="grid h-11 w-11 place-items-center rounded-xl bg-white/[0.07] text-[#C9C4FF]"><ShieldCheck className="h-5 w-5" /></span>
            <h2 className="mt-14 text-3xl font-medium tracking-[-0.055em] text-white sm:text-4xl">Private by design. Clear by default.</h2>
            <p className="mt-5 max-w-md text-sm leading-7 text-[#A9B3CB]">MindPulse explains the behavioral data it stores and puts the controls where you can use them. Nothing needs to be taken on faith.</p>
            <div className="mt-10 space-y-3">
              {["Typed content is not persisted", "Collection can be paused on this device", "Export and deletion are available in-product"].map((item) => (
                <p key={item} className="flex items-center gap-3 text-sm text-[#DBE0EE]"><span className="grid h-5 w-5 place-items-center rounded-full bg-[#62D8AC]/10 text-[#62D8AC]"><Check className="h-3 w-3" /></span>{item}</p>
              ))}
            </div>
          </motion.div>
          <motion.div {...reveal(0.08)} className="flex flex-col justify-center">
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#B9B3FF]">For the everyday workday</p>
            <h2 className="mt-4 text-3xl font-medium tracking-[-0.055em] text-white sm:text-5xl">Make room to notice your own pace.</h2>
            <p className="mt-5 max-w-xl text-base leading-7 text-[#A9B3CB]">A quieter tool for people who want reflection without surveillance, diagnosis, or a productivity contest.</p>
            <div className="mt-9 flex flex-wrap gap-3">
              <button onClick={start} className="inline-flex items-center gap-2 rounded-full bg-[#7668EC] px-5 py-3.5 text-sm font-semibold text-white transition-[transform,background-color] duration-150 ease-out hover:bg-[#8A7FF1] active:scale-[0.97]">Start with your baseline <ArrowUpRight className="h-4 w-4" /></button>
              <a href="#principles" className="inline-flex items-center gap-2 rounded-full border border-white/12 px-5 py-3.5 text-sm text-[#DBE0EE] transition-[transform,background-color,border-color] duration-150 ease-out hover:border-white/25 hover:bg-white/[0.04] active:scale-[0.97]">Read the principles</a>
            </div>
          </motion.div>
        </div>
      </section>

      <footer className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-8 text-xs text-[#7C88A4] sm:flex-row sm:items-center sm:justify-between lg:px-8">
        <Brand />
        <div className="flex flex-wrap gap-x-5 gap-y-2"><span>MindPulse</span><span>Behavioral signals, not diagnoses</span><span>Privacy controls included</span></div>
      </footer>
    </main>
  );
}
