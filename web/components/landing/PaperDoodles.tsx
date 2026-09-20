import React from "react";

/** Decorative paper / doodle shapes for the Craft-inspired landing. */
export default function PaperDoodles() {
  return (
    <>
      <svg
        className="absolute left-[6%] top-28 hidden h-16 w-16 text-[var(--doodle)] opacity-70 sm:block"
        viewBox="0 0 64 64"
        fill="none"
        aria-hidden
      >
        <path
          d="M12 40c8-18 28-22 40-8"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        <circle cx="18" cy="18" r="4" fill="currentColor" opacity="0.55" />
      </svg>
      <svg
        className="absolute right-[8%] top-40 hidden h-20 w-20 rotate-12 text-accent opacity-40 lg:block"
        viewBox="0 0 80 80"
        fill="none"
        aria-hidden
      >
        <rect
          x="16"
          y="12"
          width="40"
          height="52"
          rx="6"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeDasharray="4 5"
        />
        <path
          d="M26 28h20M26 38h14M26 48h18"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute bottom-24 left-[12%] hidden h-10 w-10 rounded-full border-2 border-dashed border-[var(--doodle)] opacity-60 sm:block" />
      <div className="absolute right-[18%] top-[58%] hidden h-3 w-16 -rotate-6 rounded-full bg-accent/20 sm:block" />
    </>
  );
}
