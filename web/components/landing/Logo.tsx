import React from "react";

export default function Logo({
  className = "",
  size = 32,
}: {
  className?: string;
  size?: number;
}) {
  return (
    <span
      className={`relative inline-flex items-center justify-center rounded-2xl bg-accent shadow-[0_6px_16px_rgba(124,108,240,0.28)] ${className}`}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <svg
        width={size * 0.58}
        height={size * 0.58}
        viewBox="0 0 24 24"
        fill="none"
        className="text-white"
      >
        <rect
          x="6.5"
          y="4"
          width="11"
          height="14"
          rx="2.4"
          stroke="currentColor"
          strokeWidth="1.7"
          opacity="0.45"
        />
        <rect
          x="4"
          y="6.5"
          width="11"
          height="14"
          rx="2.4"
          fill="currentColor"
        />
        <path
          d="M6.7 11.5h5.6M6.7 14.3h3.4"
          stroke="#F6F1EA"
          strokeWidth="1.7"
          strokeLinecap="round"
        />
      </svg>
    </span>
  );
}
