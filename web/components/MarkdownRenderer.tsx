"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { marked } from "marked";

interface MarkdownRendererProps {
  content: string;
  isStreaming?: boolean;
  /** Called when the user clicks a [File.pdf, Page N] citation badge */
  onCitationClick?: (source: string, page: number, chunkText: string) => void;
}

/** Escape text for safe use inside HTML attribute values and text nodes. */
function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

const DANGEROUS_TAGS = new Set([
  "script",
  "iframe",
  "object",
  "embed",
  "form",
  "link",
  "meta",
  "base",
  "svg",
  "math",
  "template",
]);

/**
 * Browser-side HTML sanitizer for model-rendered markdown.
 * Strips dangerous tags/attrs and blocks javascript: URLs.
 */
function sanitizeHtml(dirty: string): string {
  if (typeof window === "undefined" || typeof DOMParser === "undefined") {
    return dirty
      .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, "")
      .replace(/\son\w+\s*=\s*(["']).*?\1/gi, "")
      .replace(/\son\w+\s*=\s*[^\s>]+/gi, "");
  }

  const doc = new DOMParser().parseFromString(
    `<div id="__sanitize_root__">${dirty}</div>`,
    "text/html"
  );
  const root = doc.getElementById("__sanitize_root__");
  if (!root) return "";

  const walker = doc.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
  const toRemove: Element[] = [];

  let node = walker.nextNode() as Element | null;
  while (node) {
    const tag = node.tagName.toLowerCase();
    if (DANGEROUS_TAGS.has(tag)) {
      toRemove.push(node);
    } else {
      for (const attr of Array.from(node.attributes)) {
        const name = attr.name.toLowerCase();
        const value = attr.value.trim();
        if (name.startsWith("on") || name === "srcdoc") {
          node.removeAttribute(attr.name);
          continue;
        }
        if (
          (name === "href" || name === "src" || name === "xlink:href") &&
          /^\s*javascript:/i.test(value)
        ) {
          node.removeAttribute(attr.name);
          continue;
        }
        // Harden external navigations from model markdown
        if (tag === "a" && name === "href") {
          const href = value.trim();
          if (/^https?:\/\//i.test(href)) {
            node.setAttribute("rel", "noopener noreferrer");
            node.setAttribute("target", "_blank");
          }
        }
      }
    }
    node = walker.nextNode() as Element | null;
  }

  for (const el of toRemove) {
    el.remove();
  }

  return root.innerHTML;
}

/**
 * Extract the "answer body" — everything before "**Sources:**" — so we can
 * pass it as the cited text excerpt to the viewer.
 */
function extractAnswerBody(content: string): string {
  const sourceIdx = content.search(/\*\*Sources:\*\*/i);
  if (sourceIdx === -1) return content;
  return content.slice(0, sourceIdx).trim();
}

/**
 * Replace raw [File.pdf, Page N] tokens in an HTML string with styled
 * <button> elements carrying data-attributes the container can delegate to.
 * Attribute values are HTML-escaped to prevent XSS via citation strings.
 */
function injectCitationButtons(html: string): string {
  let result = html.replace(
    /\[([^\]]+?\.pdf),\s*[Pp]age\s*(\d+)\]/g,
    (_match, source, page) => {
      const safeSource = escapeHtml(String(source).trim());
      const safePage = escapeHtml(String(page));
      const shortName = escapeHtml(String(source).split(".")[0].slice(0, 14));
      return `<button
        type="button"
        class="citation-badge"
        data-source="${safeSource}"
        data-page="${safePage}"
        title="Open ${safeSource}, page ${safePage}"
      >${shortName}… p.${safePage}</button>`;
    }
  );

  result = result.replace(
    /\[([^\]]+?(?:\.txt)?),\s*(?:[Pp]age\s*)?\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\]/g,
    (_match, source, timestamp) => {
      let src = String(source).trim();
      if (!src.endsWith(".txt")) {
        src = src + ".txt";
      }
      const safeSource = escapeHtml(src);
      const safeTs = escapeHtml(String(timestamp));
      const shortName = escapeHtml(src.split(".")[0].slice(0, 14));
      return `<button
        type="button"
        class="citation-badge"
        data-source="${safeSource}"
        data-timestamp="${safeTs}"
        title="Open ${safeSource}, time ${safeTs}"
      >${shortName}… @ ${safeTs}</button>`;
    }
  );

  return result;
}

export default function MarkdownRenderer({
  content,
  isStreaming = false,
  onCitationClick,
}: MarkdownRendererProps) {
  const [html, setHtml] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  // Convert markdown → sanitized HTML with citation buttons injected
  useEffect(() => {
    marked.setOptions({ breaks: true, gfm: true });

    const parsed = marked.parse(content);

    const applyInjection = (rawHtml: string) => {
      const withCitations = injectCitationButtons(rawHtml);
      setHtml(sanitizeHtml(withCitations));
    };

    if (parsed instanceof Promise) {
      parsed.then((h) => applyInjection(h as string));
    } else {
      applyInjection(parsed as string);
    }
  }, [content]);

  // Delegate click events from citation badge buttons inside raw HTML
  const handleContainerClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const target = (e.target as HTMLElement).closest(".citation-badge") as HTMLButtonElement | null;
      if (!target || !onCitationClick) return;

      const source = target.dataset.source || "";
      const pageStr = target.dataset.page;
      const tsStr = target.dataset.timestamp;

      let page = 1;
      if (tsStr) {
        const parts = tsStr.split(":").map(Number);
        if (parts.length === 2) {
          page = parts[0] * 60 + parts[1];
        } else if (parts.length === 3) {
          page = parts[0] * 3600 + parts[1] * 60 + parts[2];
        }
      } else if (pageStr) {
        page = parseInt(pageStr, 10);
      }

      // Extract the answer body as context for the viewer's text excerpt
      const chunkText = extractAnswerBody(content).slice(-600).trim();

      onCitationClick(source, page, chunkText);
    },
    [content, onCitationClick]
  );

  return (
    <>
      <style>{`
        .markdown-content .citation-badge {
          display: inline-flex;
          align-items: center;
          gap: 2px;
          font-size: 10px;
          font-weight: 600;
          line-height: 1;
          padding: 2px 7px;
          margin: 0 2px;
          border-radius: 999px;
          background: var(--accent-soft);
          color: var(--accent);
          border: 1px solid color-mix(in oklab, var(--accent) 35%, transparent);
          cursor: pointer;
          vertical-align: middle;
          transition: background 0.15s, border-color 0.15s, color 0.15s, transform 0.1s;
          white-space: nowrap;
        }
        .markdown-content .citation-badge:hover {
          background: color-mix(in oklab, var(--accent) 22%, transparent);
          border-color: color-mix(in oklab, var(--accent) 60%, transparent);
          color: var(--accent-strong);
          transform: translateY(-1px);
        }
        .markdown-content .citation-badge:active {
          transform: translateY(0);
        }
        .markdown-content .citation-badge::before {
          content: "↗";
          font-size: 9px;
          opacity: 0.7;
        }
        .markdown-content p { margin-bottom: 0.6em; }
        .markdown-content ul, .markdown-content ol { padding-left: 1.2em; margin-bottom: 0.6em; }
        .markdown-content li { margin-bottom: 0.25em; }
        .markdown-content strong { color: var(--foreground); font-weight: 700; }
        .markdown-content code { background: var(--accent-soft); color: var(--accent-strong); padding: 1px 5px; border-radius: 4px; font-size: 0.85em; }
        .markdown-content pre { background: var(--surface-2); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 0.75em 1em; margin: 0.5em 0; overflow-x: auto; }
        .markdown-content pre code { background: transparent; color: var(--foreground); padding: 0; }
        .markdown-content h1, .markdown-content h2, .markdown-content h3 { color: var(--foreground); font-weight: 700; margin: 0.8em 0 0.4em; }
        .markdown-content blockquote { border-left: 2px solid var(--accent); padding-left: 0.75em; color: var(--muted); margin: 0.5em 0; }
        .markdown-content a { color: var(--accent); text-decoration: underline; }
        .is-streaming .markdown-content::after {
          content: "▋";
          display: inline-block;
          animation: blink 0.8s step-end infinite;
          color: var(--accent);
          font-size: 0.75em;
          vertical-align: text-bottom;
          margin-left: 2px;
        }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
      `}</style>

      <div
        ref={containerRef}
        className={`markdown-content text-[12px] sm:text-xs text-foreground leading-relaxed ${
          isStreaming ? "is-streaming" : ""
        }`}
        dangerouslySetInnerHTML={{ __html: html }}
        onClick={onCitationClick ? handleContainerClick : undefined}
      />
    </>
  );
}
