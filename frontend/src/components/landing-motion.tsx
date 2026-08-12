"use client";

import type { ReactNode } from "react";
import { motion, useReducedMotion, useScroll, useSpring } from "framer-motion";

const EASE_OUT = [0.23, 1, 0.32, 1] as const;
const EASE_IN_OUT = [0.77, 0, 0.175, 1] as const;

type ChildrenProps = { children: ReactNode; className?: string };

export function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 180, damping: 32, mass: 0.25 });
  return <motion.div className="pointer-events-none fixed inset-x-0 top-0 z-[70] h-px origin-left bg-gradient-to-r from-[#B9B3FF] via-[#72DDB6] to-[#B9B3FF]" style={{ scaleX }} />;
}

export function LandingReveal({ children, className = "" }: ChildrenProps) {
  const reduceMotion = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduceMotion ? { opacity: 0 } : { opacity: 0, transform: "translate3d(0,20px,0) scale(0.985)" }}
      whileInView={reduceMotion ? { opacity: 1 } : { opacity: 1, transform: "translate3d(0,0,0) scale(1)" }}
      viewport={{ once: true, amount: 0.22, margin: "0px 0px -72px 0px" }}
      transition={{ duration: 0.62, ease: EASE_OUT }}
    >
      {children}
    </motion.div>
  );
}

export function LandingStagger({ children, className = "" }: ChildrenProps) {
  const reduceMotion = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.18, margin: "0px 0px -64px 0px" }}
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: reduceMotion ? 0 : 0.07, delayChildren: reduceMotion ? 0 : 0.03 } },
      }}
    >
      {children}
    </motion.div>
  );
}

export function LandingStaggerItem({ children, className = "" }: ChildrenProps) {
  const reduceMotion = useReducedMotion();
  return (
    <motion.div
      className={className}
      variants={{
        hidden: reduceMotion ? { opacity: 0 } : { opacity: 0, transform: "translate3d(0,14px,0) scale(0.99)" },
        visible: reduceMotion ? { opacity: 1 } : { opacity: 1, transform: "translate3d(0,0,0) scale(1)" },
      }}
      transition={{ duration: 0.46, ease: EASE_OUT }}
    >
      {children}
    </motion.div>
  );
}

export function SectionWave() {
  const reduceMotion = useReducedMotion();
  return (
    <motion.div
      aria-hidden="true"
      className="relative h-px overflow-hidden bg-white/[0.08]"
      initial={reduceMotion ? { opacity: 0 } : { opacity: 0, transform: "translate3d(-8%,0,0)" }}
      whileInView={reduceMotion ? { opacity: 1 } : { opacity: 1, transform: "translate3d(0,0,0)" }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.9, ease: EASE_IN_OUT }}
    >
      <motion.div
        className="absolute inset-y-0 left-0 w-1/3 bg-gradient-to-r from-transparent via-[#B9B3FF] to-transparent"
        animate={reduceMotion ? undefined : { transform: ["translate3d(-100%,0,0)", "translate3d(340%,0,0)"] }}
        transition={{ duration: 4.8, repeat: Infinity, ease: "linear" }}
      />
    </motion.div>
  );
}

export function NarrativeOrbit() {
  const reduceMotion = useReducedMotion();
  return (
    <div className="relative aspect-square w-full max-w-[18rem]" aria-hidden="true">
      <motion.div className="absolute inset-[4%] rounded-full border border-[#B9B3FF]/12" animate={reduceMotion ? undefined : { rotate: 360 }} transition={{ duration: 32, repeat: Infinity, ease: "linear" }} />
      <motion.div className="absolute inset-[20%] rounded-full border border-[#72DDB6]/16" animate={reduceMotion ? undefined : { rotate: -360 }} transition={{ duration: 22, repeat: Infinity, ease: "linear" }} />
      <motion.div className="absolute inset-[37%] rounded-full border border-white/10 bg-white/[0.035]" animate={reduceMotion ? undefined : { transform: ["scale(1)", "scale(1.06)", "scale(1)"] }} transition={{ duration: 4.8, repeat: Infinity, ease: "easeInOut" }} />
      <motion.span className="absolute left-[15%] top-[29%] h-2 w-2 rounded-full bg-[#B9B3FF] shadow-[0_0_18px_rgba(185,179,255,0.9)]" animate={reduceMotion ? undefined : { transform: ["translate3d(0,0,0)", "translate3d(16px,-9px,0)", "translate3d(0,0,0)"] }} transition={{ duration: 5.4, repeat: Infinity, ease: "easeInOut" }} />
      <motion.span className="absolute bottom-[21%] right-[20%] h-2 w-2 rounded-full bg-[#72DDB6] shadow-[0_0_18px_rgba(114,221,182,0.8)]" animate={reduceMotion ? undefined : { transform: ["translate3d(0,0,0)", "translate3d(-12px,10px,0)", "translate3d(0,0,0)"] }} transition={{ duration: 6.2, repeat: Infinity, ease: "easeInOut" }} />
    </div>
  );
}
