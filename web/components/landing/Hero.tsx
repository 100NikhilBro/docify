"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  AnimatePresence,
  motion,
  useReducedMotion,
  useScroll,
  useTransform,
} from "framer-motion";
import { ArrowRight, Play } from "lucide-react";
import ProductVisual from "./ProductVisual";
import PaperDoodles from "./PaperDoodles";
import { brand, hero } from "@/lib/landing-content";

export default function Hero() {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"],
  });
  const y = useTransform(scrollYProgress, [0, 1], [0, reduce ? 0 : 100]);
  const opacity = useTransform(scrollYProgress, [0, 0.8], [1, reduce ? 1 : 0]);

  const [wordIndex, setWordIndex] = useState(0);
  useEffect(() => {
    if (reduce) return;
    const id = setInterval(
      () => setWordIndex((i) => (i + 1) % hero.titleRotators.length),
      2200
    );
    return () => clearInterval(id);
  }, [reduce]);

  const ease = [0.21, 0.47, 0.32, 0.98] as const;

  return (
    <section
      ref={ref}
      className="relative overflow-hidden px-4 pb-16 pt-28 sm:px-6 sm:pt-36 lg:pt-40"
    >
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-paper" />
        <div className="absolute inset-0 bg-dots opacity-40" />
        <div className="absolute left-1/2 top-10 h-[420px] w-[720px] -translate-x-1/2 rounded-full bg-[var(--accent-glow)] blur-[120px]" />
        <PaperDoodles />
      </div>

      <motion.div style={{ y, opacity }} className="mx-auto max-w-3xl text-center">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease }}
          className="mb-5"
        >
          <p className="font-display text-5xl font-semibold tracking-tight text-foreground sm:text-6xl lg:text-7xl">
            {brand.name}
          </p>
          <p className="mt-2 text-sm font-medium tracking-wide text-accent sm:text-base">
            {brand.tagline}
          </p>
        </motion.div>

        <motion.a
          href="#features"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.05, ease }}
          className="group inline-flex items-center gap-2 rounded-full border border-border-subtle bg-surface/80 px-3.5 py-1.5 text-xs font-medium text-muted shadow-[var(--shadow-soft)] backdrop-blur-sm transition-colors hover:text-foreground"
        >
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-accent" />
          {hero.eyebrow}
          <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
        </motion.a>

        <motion.h1
          initial={{ opacity: 0, y: 22 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.1, ease }}
          className="mt-6 text-balance font-display text-3xl font-semibold leading-[1.12] tracking-tight text-foreground sm:text-5xl"
        >
          {hero.titleLead}{" "}
          <span className="relative inline-flex min-w-[12ch] justify-center text-accent">
            <AnimatePresence mode="wait">
              <motion.span
                key={wordIndex}
                initial={{ opacity: 0, y: "0.4em" }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: "-0.4em" }}
                transition={{ duration: 0.4, ease }}
              >
                {hero.titleRotators[wordIndex]}
              </motion.span>
            </AnimatePresence>
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 22 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2, ease }}
          className="mx-auto mt-6 max-w-2xl text-pretty text-base leading-relaxed text-muted sm:text-lg"
        >
          {hero.subtitle}
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 22 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3, ease }}
          className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row"
        >
          <Link
            href="/workspace"
            className="group inline-flex w-full items-center justify-center gap-2 rounded-full bg-accent px-7 py-3.5 text-sm font-semibold text-accent-foreground shadow-[0_12px_28px_rgba(124,108,240,0.28)] transition-all hover:scale-[1.02] sm:w-auto"
          >
            {hero.primaryCta}
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
          <a
            href="#demo"
            className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-border-subtle bg-surface px-7 py-3.5 text-sm font-semibold text-foreground shadow-[var(--shadow-soft)] transition-colors hover:bg-surface-2 sm:w-auto"
          >
            <Play className="h-3.5 w-3.5 fill-current" />
            {hero.secondaryCta}
          </a>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.45 }}
          className="mt-5 text-xs text-muted"
        >
          {hero.footnote}
        </motion.p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.35, ease }}
        className="mx-auto mt-14 max-w-4xl"
      >
        <ProductVisual />
      </motion.div>
    </section>
  );
}
