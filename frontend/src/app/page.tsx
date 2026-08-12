"use client";

import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Activity,
  ArrowUpRight,
  Check,
  ChevronRight,
  CircleDot,
  EyeOff,
  Keyboard,
  MousePointer2,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

const EASE = [0.16, 1, 0.3, 1] as const;

const reveal = {
  initial: { opacity: 0, y: 18 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, amount: 0.2 },
  transition: { duration: 0.7, ease: EASE },
};

function Mark() {
  return (
    <div className="flex items-center gap-2.5" aria-label="MindPulse home">
      <div className="grid h-9 w-9 place-items-center rounded-xl border border-white/10 bg-white/[0.04] shadow-[0_0_30px_rgba(139,124,246,0.16)]">
        <svg viewBox="0 0 32 32" className="h-5 w-5" fill="none" aria-hidden="true">
          <path d="M3 16h5l2.5-6 4.2 13 3.4-16 3.1 12 2.4-5H29" stroke="#B8B1FF" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <span className="text-sm font-semibold tracking-[-0.03em] text-[#F4F6FB]">MindPulse</span>
    </div>
  );
}

function Dot({ tone = "violet" }: { tone?: "violet" | "mint" | "amber" }) {
  const colors = {
    violet: "bg-[#8b7cf6] shadow-[0_0_12px_rgba(139,124,246,0.9)]",
    mint: "bg-[#54d6a0] shadow-[0_0_12px_rgba(84,214,160,0.8)]",
    amber: "bg-[#f0b35b] shadow-[0_0_12px_rgba(240,179,91,0.7)]",
  };
  return <span className={`inline-block h-1.5 w-1.5 rounded-full ${colors[tone]}`} />;
}

function SignalPreview() {
  return (
    <div className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-[#101527]/80 p-5 shadow-[0_35px_100px_rgba(0,0,0,0.42)] backdrop-blur-xl">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_75%_0%,rgba(139,124,246,0.23),transparent_36%),radial-gradient(circle_at_15%_100%,rgba(84,214,160,0.12),transparent_28%)]" />
      <div className="relative">
        <div className="mb-7 flex items-center justify-between">
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#AAB4CF]">
            <Dot tone="amber" /> Live signal
          </div>
          <span className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[10px] text-[#AAB4CF]">Window 00:18</span>
        </div>

        <div className="rounded-2xl border border-[#f0b35b]/25 bg-[#f0b35b]/[0.06] p-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold text-[#F4F6FB]">Waiting for a useful signal</p>
              <p className="mt-1 max-w-[18rem] text-xs leading-5 text-[#AAB4CF]">More measured activity is needed before MindPulse can describe a trend.</p>
            </div>
            <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#f0b35b]/15 text-[#f0b35b]"><Activity className="h-4 w-4" /></div>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-[1.25fr_.75fr] gap-3">
          <div className="rounded-2xl border border-white/8 bg-[#080b15]/70 p-4">
            <div className="flex items-center justify-between"><span className="text-[10px] uppercase tracking-[0.16em] text-[#7E89A6]">Activity trace</span><span className="text-[10px] text-[#54d6a0]">measured</span></div>
            <svg viewBox="0 0 260 68" className="mt-5 h-16 w-full" fill="none" preserveAspectRatio="none" aria-hidden="true">
              <path d="M0 51C17 50 20 46 33 46c17 0 17-27 34-27 18 0 15 35 35 35 20 0 15-15 34-15 14 0 20-24 35-24 19 0 10 39 31 39 17 0 19-12 29-12 12 0 14 7 29 7" stroke="url(#trace)" strokeWidth="3" strokeLinecap="round" />
              <defs><linearGradient id="trace" x1="0" y1="0" x2="260" y2="0"><stop stopColor="#8b7cf6" /><stop offset="1" stopColor="#54d6a0" /></linearGradient></defs>
            </svg>
            <div className="mt-3 flex justify-between text-[10px] text-[#7E89A6]"><span>quiet</span><span>current window</span></div>
          </div>
          <div className="rounded-2xl border border-white/8 bg-[#080b15]/70 p-4">
            <p className="text-[10px] uppercase tracking-[0.16em] text-[#7E89A6]">Context</p>
            <p className="mt-4 text-2xl font-medium tracking-[-0.06em] text-[#F4F6FB]">—</p>
            <p className="mt-1 text-[10px] leading-4 text-[#7E89A6]">No label until the input is meaningful.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LandingPage() {
  const router = useRouter();
  const start = () => router.push("/signup");

  return (
    <main className="min-h-screen overflow-hidden bg-[#080a12] text-[#F4F6FB]">
      <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(circle_at_15%_0%,rgba(139,124,246,0.20),transparent_31rem),radial-gradient(circle_at_93%_20%,rgba(84,214,160,0.10),transparent_26rem),linear-gradient(180deg,#080a12_0%,#0a0e1a_46%,#080a12_100%)]" />
      <div className="pointer-events-none fixed inset-0 -z-10 opacity-[0.045] [background-image:linear-gradient(rgba(255,255,255,.7)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.7)_1px,transparent_1px)] [background-size:48px_48px]" />

      <nav className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 lg:px-8">
        <Mark />
        <div className="hidden items-center gap-7 text-xs text-[#AAB4CF] md:flex">
          <a href="#how-it-works" className="transition hover:text-white">How it works</a>
          <a href="#privacy" className="transition hover:text-white">Privacy</a>
          <a href="#states" className="transition hover:text-white">Signal states</a>
        </div>
        <button onClick={start} className="group inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.06] px-4 py-2 text-xs font-medium text-white transition hover:border-white/25 hover:bg-white/[0.1] active:scale-[0.98]">
          Start privately <ArrowUpRight className="h-3.5 w-3.5 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
        </button>
      </nav>

      <section className="mx-auto grid max-w-7xl items-center gap-12 px-5 pb-24 pt-16 lg:grid-cols-[1.02fr_.98fr] lg:px-8 lg:pb-32 lg:pt-24">
        <motion.div {...reveal}>
          <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-[#8b7cf6]/25 bg-[#8b7cf6]/[0.08] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-[#C8C3FF]"><Sparkles className="h-3 w-3" /> Behavioral intelligence, deliberately quiet</div>
          <h1 className="max-w-3xl text-5xl font-medium leading-[0.98] tracking-[-0.075em] text-[#F7F8FC] sm:text-6xl lg:text-7xl">
            Understand the workday you&apos;re <span className="bg-gradient-to-r from-[#b8b1ff] to-[#61d9a8] bg-clip-text text-transparent">actually having.</span>
          </h1>
          <p className="mt-7 max-w-xl text-base leading-7 text-[#AAB4CF] sm:text-lg">
            MindPulse turns interaction timing into a private, personal rhythm signal—then makes it clear when it has enough context to be useful and when it does not.
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <button onClick={start} className="group inline-flex items-center gap-3 rounded-full bg-[#F4F6FB] px-5 py-3.5 text-sm font-semibold text-[#090B12] shadow-[0_16px_40px_rgba(244,246,251,0.12)] transition hover:bg-white active:scale-[0.98]">
              Begin your baseline <ArrowUpRight className="h-4 w-4 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
            </button>
            <a href="#states" className="inline-flex items-center gap-2 rounded-full border border-white/12 px-5 py-3.5 text-sm font-medium text-[#D5DAE8] transition hover:border-white/25 hover:bg-white/[0.04]">See the product logic <ChevronRight className="h-4 w-4" /></a>
          </div>
          <div className="mt-12 grid max-w-xl grid-cols-3 gap-3 border-t border-white/10 pt-6">
            {[['No content', 'Typed text is not persisted'], ['Four states', 'No fake certainty'], ['Your control', 'Pause, export, delete']].map(([number, label]) => (
              <div key={number}><p className="text-sm font-semibold text-[#F4F6FB]">{number}</p><p className="mt-1 text-[11px] leading-4 text-[#7E89A6]">{label}</p></div>
            ))}
          </div>
        </motion.div>
        <motion.div {...reveal} transition={{ duration: 0.8, delay: 0.12, ease: EASE }} className="relative">
          <div className="absolute -inset-12 rounded-full bg-[#8b7cf6]/10 blur-3xl" />
          <SignalPreview />
          <div className="relative mx-auto -mt-5 w-[86%] rounded-2xl border border-white/10 bg-[#0d1220]/95 p-3 shadow-2xl backdrop-blur-xl">
            <div className="flex items-center gap-3"><div className="grid h-8 w-8 place-items-center rounded-lg bg-[#54d6a0]/10 text-[#54d6a0]"><ShieldCheck className="h-4 w-4" /></div><p className="text-xs leading-5 text-[#BAC3DA]"><span className="font-semibold text-[#F4F6FB]">The design principle:</span> a signal is only useful when its limits are visible.</p></div>
          </div>
        </motion.div>
      </section>

      <section id="how-it-works" className="border-y border-white/[0.08] bg-white/[0.02]">
        <div className="mx-auto max-w-7xl px-5 py-20 lg:px-8 lg:py-28">
          <motion.div {...reveal} className="max-w-2xl"><p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#8b7cf6]">A different kind of dashboard</p><h2 className="mt-4 text-3xl font-medium tracking-[-0.055em] text-white sm:text-5xl">Less theatre. More context.</h2><p className="mt-5 text-base leading-7 text-[#AAB4CF]">Most wellbeing products make a bold claim from a thin slice of activity. MindPulse is designed to qualify the input first, then present a useful trend only when the data supports it.</p></motion.div>
          <div className="mt-12 grid gap-4 md:grid-cols-3">
            {[
              { icon: <MousePointer2 className="h-5 w-5" />, title: "Observe timing", body: "Interaction timing and movement patterns are summarized in short windows. Typed content is not persisted." },
              { icon: <CircleDot className="h-5 w-5" />, title: "Qualify the signal", body: "Sparse activity, early calibration, and a ready personal baseline are distinct states—not the same score with different colors." },
              { icon: <Sparkles className="h-5 w-5" />, title: "Guide, never diagnose", body: "The product offers an optional check-in or gentle intervention. You remain the authority on your context." },
            ].map((item, index) => <motion.article {...reveal} transition={{ duration: 0.55, delay: index * 0.08, ease: EASE }} key={item.title} className="group rounded-3xl border border-white/10 bg-[#101527]/70 p-6 transition hover:-translate-y-1 hover:border-[#8b7cf6]/35 hover:bg-[#12192c]">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-white/[0.05] text-[#B8B1FF]">{item.icon}</div><p className="mt-8 text-lg font-semibold tracking-[-0.03em] text-white">{item.title}</p><p className="mt-3 text-sm leading-6 text-[#9BA7C2]">{item.body}</p><span className="mt-7 inline-flex items-center gap-1 text-xs font-medium text-[#B8B1FF]">0{index + 1} <ChevronRight className="h-3.5 w-3.5" /></span>
            </motion.article>)}
          </div>
        </div>
      </section>

      <section id="states" className="mx-auto max-w-7xl px-5 py-20 lg:px-8 lg:py-28">
        <div className="grid gap-12 lg:grid-cols-[.86fr_1.14fr] lg:items-start"><motion.div {...reveal}><p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#54d6a0]">Signal integrity</p><h2 className="mt-4 text-3xl font-medium tracking-[-0.055em] text-white sm:text-5xl">A dashboard that knows when not to speak.</h2><p className="mt-5 text-base leading-7 text-[#AAB4CF]">The live surface does not invent a score for an empty window. It identifies the quality of the input, the maturity of the baseline, and the right next step.</p><button onClick={start} className="mt-8 inline-flex items-center gap-2 text-sm font-semibold text-[#C8C3FF] transition hover:text-white">Experience the four states <ArrowUpRight className="h-4 w-4" /></button></motion.div>
          <motion.div {...reveal} transition={{ duration: 0.8, delay: 0.1, ease: EASE }} className="grid gap-3 sm:grid-cols-2">
            {[
              { tone: "border-white/10", status: "No live window", detail: "Nothing has been measured in the current interval.", chip: "Waiting", icon: <Activity className="h-4 w-4" /> },
              { tone: "border-[#f0b35b]/30", status: "Insufficient activity", detail: "A quiet window is not interpreted as calm or low strain.", chip: "Abstain", icon: <EyeOff className="h-4 w-4" /> },
              { tone: "border-[#8b7cf6]/35", status: "Calibrating", detail: "Early activity is visible, while the personal baseline is still learning.", chip: "Early trend", icon: <Keyboard className="h-4 w-4" /> },
              { tone: "border-[#54d6a0]/35", status: "Ready", detail: "Measured activity can be read against a sufficiently established personal baseline.", chip: "Contextual", icon: <Check className="h-4 w-4" /> },
            ].map((state) => <div key={state.status} className={`rounded-2xl border ${state.tone} bg-[#101527]/70 p-5`}><div className="flex items-center justify-between"><span className="grid h-8 w-8 place-items-center rounded-lg bg-white/[0.05] text-[#D7D3FF]">{state.icon}</span><span className="rounded-full bg-white/[0.05] px-2.5 py-1 text-[10px] text-[#B8C1D8]">{state.chip}</span></div><p className="mt-7 text-sm font-semibold text-white">{state.status}</p><p className="mt-2 text-xs leading-5 text-[#9BA7C2]">{state.detail}</p></div>)}
          </motion.div>
        </div>
      </section>

      <section id="privacy" className="border-t border-white/[0.08] bg-[#0B0F1B]">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-20 lg:grid-cols-2 lg:px-8 lg:py-28"><motion.div {...reveal} className="rounded-[2rem] border border-white/10 bg-[linear-gradient(145deg,rgba(139,124,246,.15),rgba(16,21,39,.88)_42%,rgba(16,21,39,.7))] p-7 sm:p-9"><div className="grid h-11 w-11 place-items-center rounded-xl bg-white/[0.07] text-[#B8B1FF]"><ShieldCheck className="h-5 w-5" /></div><h2 className="mt-14 text-3xl font-medium tracking-[-0.055em] text-white sm:text-4xl">Private by design. Clear by default.</h2><p className="mt-5 max-w-md text-sm leading-7 text-[#AAB4CF]">You can pause collection on a device, export the behavioral data stored by the service, or delete it while keeping your account. The product explains what it stores instead of hiding it in a promise.</p><div className="mt-10 space-y-3">{['Typed content is not persisted', 'Tracking can be paused instantly', 'Export and deletion are in-product controls'].map((item) => <div className="flex items-center gap-3 text-sm text-[#D9DDEA]" key={item}><span className="grid h-5 w-5 place-items-center rounded-full bg-[#54d6a0]/10 text-[#54d6a0]"><Check className="h-3 w-3" /></span>{item}</div>)}</div></motion.div>
          <motion.div {...reveal} transition={{ duration: 0.8, delay: 0.1, ease: EASE }} className="flex flex-col justify-center"><p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#8b7cf6]">Built for everyday work</p><h3 className="mt-4 text-3xl font-medium tracking-[-0.055em] text-white sm:text-5xl">A softer relationship with your attention.</h3><p className="mt-5 max-w-xl text-base leading-7 text-[#AAB4CF]">For people who want a clearer view of their workday without being watched, diagnosed, or pushed into a productivity contest.</p><div className="mt-9 flex flex-wrap gap-3"><button onClick={start} className="inline-flex items-center gap-2 rounded-full bg-[#8b7cf6] px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-[#9b90f8] active:scale-[0.98]">Create your private baseline <ArrowUpRight className="h-4 w-4" /></button><a href="#how-it-works" className="inline-flex items-center gap-2 rounded-full border border-white/10 px-5 py-3.5 text-sm text-[#D9DDEA] transition hover:bg-white/[0.04]">How it works</a></div></motion.div>
        </div>
      </section>

      <footer className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-8 text-xs text-[#7E89A6] sm:flex-row sm:items-center sm:justify-between lg:px-8"><Mark /><div className="flex flex-wrap gap-x-5 gap-y-2"><span>MindPulse v1.0</span><span>Behavioral signals, not diagnoses</span><span>Privacy controls included</span></div></footer>
    </main>
  );
}
