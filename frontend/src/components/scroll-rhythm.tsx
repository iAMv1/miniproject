"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useMotionValue, useReducedMotion, useScroll, useSpring, useTransform } from "framer-motion";

const POINTS = 24;

export function ScrollRhythm() {
  const shouldReduceMotion = useReducedMotion();
  const { scrollY } = useScroll();
  const lastY = useRef(0);
  const lastTime = useRef(Date.now());
  const rawVelocity = useMotionValue(0);
  const smoothedVelocity = useSpring(rawVelocity, { stiffness: 130, damping: 28, mass: 0.35 });
  const glow = useTransform(smoothedVelocity, [0, 2], [0.45, 1]);
  const [points, setPoints] = useState<number[]>(() => Array(POINTS).fill(0));

  useEffect(() => {
    const unsubscribe = scrollY.on("change", (currentY) => {
      const now = Date.now();
      const elapsed = Math.max(now - lastTime.current, 16);
      const nextVelocity = Math.min(Math.abs(currentY - lastY.current) / elapsed, 2.4);
      rawVelocity.set(nextVelocity);
      setPoints((previous) => [...previous.slice(-(POINTS - 1)), nextVelocity]);
      lastY.current = currentY;
      lastTime.current = now;
    });
    return unsubscribe;
  }, [rawVelocity, scrollY]);

  const path = points
    .map((velocity, index) => {
      const x = (index / (POINTS - 1)) * 96;
      const y = 14 - Math.min(velocity * 8, 10);
      return `${index === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <motion.aside
      aria-label="MindPulse scroll rhythm visual response; it is not a product reading"
      className="pointer-events-none fixed right-7 top-[4.7rem] z-40 hidden w-32 lg:block"
      style={{ opacity: shouldReduceMotion ? 0.68 : glow }}
    >
      <div className="rounded-2xl border border-white/[0.09] bg-[#0B0E19]/72 px-3 py-2.5 shadow-[0_14px_36px_rgba(0,0,0,0.24)] backdrop-blur-md">
        <div className="flex items-center gap-2">
          <span className="grid h-5 w-5 place-items-center rounded-md bg-white/[0.05]">
            <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" aria-hidden="true">
              <path d="M2 12h4l1.8-4.5L11 17l2.7-10 2 6H22" stroke="#B9B3FF" strokeWidth="1.55" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
          <span className="text-[10px] font-semibold tracking-[-0.02em] text-[#E8EAF4]">MindPulse</span>
        </div>
        <svg viewBox="0 0 96 28" className="mt-2 h-7 w-full" fill="none" aria-hidden="true">
          <path d="M0 14H96" stroke="rgba(255,255,255,0.10)" strokeWidth="1" />
          <motion.path d={path} stroke="#B9B3FF" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          {!shouldReduceMotion && <motion.circle cx="96" cy={points.length ? 14 - Math.min(points[points.length - 1] * 8, 10) : 14} r="2" fill="#72DDB6" animate={{ opacity: [0.6, 1, 0.6] }} transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }} />}
        </svg>
        <p className="mt-1 text-[8px] font-medium uppercase tracking-[0.15em] text-[#77829E]">Your scroll rhythm</p>
      </div>
    </motion.aside>
  );
}
