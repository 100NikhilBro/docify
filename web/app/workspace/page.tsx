"use client";

import React from "react";
import ChatInterface from "@/components/ChatInterface";
import Logo from "@/components/landing/Logo";
import Link from "next/link";
import { UserButton } from "@clerk/nextjs";
import { brand } from "@/lib/landing-content";

export default function WorkspacePage() {
  return (
    <div className="flex h-screen w-full flex-col bg-background font-sans text-foreground">
      <header className="z-50 flex h-14 flex-none items-center justify-between border-b border-border-subtle bg-surface/90 px-4 backdrop-blur-xl sm:px-6">
        <Link
          href="/"
          className="group flex items-center gap-2.5 transition-opacity hover:opacity-90"
        >
          <Logo size={28} className="transition-transform group-hover:scale-105" />
          <div className="flex flex-col leading-tight">
            <span className="font-display text-[17px] font-semibold tracking-tight text-foreground">
              {brand.name}
            </span>
            <span className="hidden text-[10px] font-medium text-muted sm:block">
              {brand.tagline}
            </span>
          </div>
        </Link>
        <div className="flex items-center gap-3 sm:gap-4">
          <UserButton
            appearance={{
              elements: { avatarBox: "h-8 w-8 ring-2 ring-border-subtle" },
            }}
          />
        </div>
      </header>
      <main className="relative flex-1 overflow-hidden">
        <ChatInterface />
      </main>
    </div>
  );
}
