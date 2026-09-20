"use client";

import React from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import Reveal from "./Reveal";
import { finalCta } from "@/lib/landing-content";

export default function Cta() {
  return (
    <section className="px-4 py-20 sm:px-6 sm:py-28">
      <Reveal className="mx-auto max-w-5xl">
        <div className="relative overflow-hidden rounded-[2rem] border border-border-subtle bg-accent px-6 py-16 text-center shadow-[0_20px_50px_rgba(124,108,240,0.28)] sm:px-12 sm:py-24">
          <div className="pointer-events-none absolute inset-0">
            <div className="absolute -left-10 top-8 h-40 w-40 rounded-full bg-white/10 blur-2xl" />
            <div className="absolute -right-8 bottom-6 h-48 w-48 rounded-full bg-[#c4b5fd]/30 blur-3xl" />
          </div>

          <div className="relative">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/25 bg-white/10 px-3.5 py-1.5 text-xs font-medium text-white/90">
              <span className="h-1.5 w-1.5 rounded-full bg-white" />
              {finalCta.badge}
            </span>
            <h2 className="mx-auto mt-6 max-w-2xl text-balance font-display text-3xl font-semibold tracking-tight text-white sm:text-5xl">
              {finalCta.title}
            </h2>
            <p className="mx-auto mt-5 max-w-xl text-pretty text-base leading-relaxed text-white/80 sm:text-lg">
              {finalCta.subtitle}
            </p>
            <div className="mt-9 flex justify-center">
              <Link
                href="/workspace"
                className="group inline-flex items-center justify-center gap-2 rounded-full bg-white px-8 py-4 text-sm font-semibold text-accent-strong transition-transform hover:scale-[1.03]"
              >
                {finalCta.primary}
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
            </div>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
