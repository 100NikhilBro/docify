"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";

const getApiBaseUrl = () => {
  const nodeEnv = (
    process.env.NEXT_PUBLIC_NODE_ENV ||
    process.env.NODE_ENV ||
    "development"
  ).toLowerCase();
  if (nodeEnv === "production") {
    return (
      process.env.NEXT_PUBLIC_BASE_API_URL ||
      process.env.NEXT_BASE_API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      "https://pdf-rag-wjgd.onrender.com"
    );
  }
  return "http://localhost:8000";
};

const API_BASE = getApiBaseUrl();

export interface Citation {
  source: string;
  page: number;
  text: string;
}

interface PdfViewerPanelProps {
  citation: Citation | null;
  onClose: () => void;
}

export default function PdfViewerPanel({ citation, onClose }: PdfViewerPanelProps) {
  const { getToken } = useAuth();
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [txtContent, setTxtContent] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [isExcerptExpanded, setIsExcerptExpanded] = useState<boolean>(true);
  const [retryKey, setRetryKey] = useState<number>(0);

  useEffect(() => {
    if (citation) {
      setCurrentPage(citation.page);
      setIsExcerptExpanded(true);
    }
  }, [citation?.source, citation?.page]);

  useEffect(() => {
    let active = true;
    let currentUrl: string | null = null;

    if (citation?.source) {
      setIsLoading(true);
      setLoadError(false);
      setPdfUrl(null);
      setTxtContent(null);

      const fetchFile = async () => {
        try {
          const token = await getToken();
          const headers: Record<string, string> = {};
          if (token) {
            headers["Authorization"] = `Bearer ${token}`;
          }

          const res = await fetch(
            `${API_BASE}/files/pdf?filename=${encodeURIComponent(citation.source)}`,
            { headers }
          );

          if (!res.ok) {
            if (active) setLoadError(true);
            return;
          }

          const isTxt = citation.source.toLowerCase().endsWith(".txt");
          if (isTxt) {
            const text = await res.text();
            if (active) {
              setTxtContent(text);
            }
          } else {
            const blob = await res.blob();
            if (active) {
              const objectUrl = URL.createObjectURL(blob);
              currentUrl = objectUrl;
              setPdfUrl(objectUrl);
            }
          }
        } catch {
          if (active) setLoadError(true);
        } finally {
          if (active) setIsLoading(false);
        }
      };

      fetchFile();
    }

    return () => {
      active = false;
      if (currentUrl) {
        URL.revokeObjectURL(currentUrl);
      }
    };
  }, [citation?.source, getToken, retryKey]);

  const isOpen = citation !== null;

  return (
    <div
      className={`
        flex-shrink-0 flex flex-col h-full relative
        bg-surface border-l border-border-subtle
        transition-all duration-300 ease-in-out overflow-hidden
        ${
          isOpen
            ? "w-[min(100vw,700px)] sm:w-[500px] md:w-[600px] lg:w-[680px] xl:w-[760px] 2xl:w-[860px] opacity-100"
            : "w-0 opacity-0 border-none"
        }
      `}
      aria-hidden={!isOpen}
    >
      {isOpen && citation && (
        <div className="flex flex-col h-full overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2.5 bg-surface-2/80 border-b border-border-subtle text-foreground flex-shrink-0 select-none shadow-[var(--shadow-soft)] z-10">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-7 h-7 rounded-lg bg-surface flex items-center justify-center flex-shrink-0 border border-border-subtle">
                {citation.source.toLowerCase().endsWith(".txt") ? (
                  <svg className="w-4 h-4 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4 text-red-500 fill-current" viewBox="0 0 24 24">
                    <path d="M11.362 2C7.656 2 6 3.656 6 7.362v9.276C6 20.344 7.656 22 11.362 22h1.276C16.344 22 18 20.344 18 16.638V7.362C18 3.656 16.344 2 12.638 2h-1.276zm0 2h1.276c2.518 0 3.362.844 3.362 3.362v9.276c0 2.518-.844 3.362-3.362 3.362h-1.276c-2.518 0-3.362-.844-3.362-3.362V7.362C8 4.844 8.844 4 11.362 4z" />
                  </svg>
                )}
              </div>
              <p className="text-xs font-semibold text-foreground truncate max-w-[280px] md:max-w-[400px]" title={citation.source}>
                {citation.source}
              </p>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-red-500/10 text-muted hover:text-red-500 transition-all cursor-pointer border border-transparent hover:border-red-500/20"
              title="Close PDF viewer"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="flex-1 w-full h-full bg-surface-2 relative overflow-hidden select-text">
            {isLoading ? (
              <div className="absolute inset-0 flex items-center justify-center p-8 bg-surface-2">
                <div className="space-y-4 animate-pulse w-full max-w-[550px] shadow-[var(--shadow-card)] rounded-xl overflow-hidden bg-surface p-8 border border-border-subtle aspect-[3/4.15]" />
              </div>
            ) : loadError ? (
              <div className="flex flex-col items-center justify-center h-full gap-4 text-center py-20 px-8 bg-surface-2">
                <div className="w-16 h-16 rounded-2xl bg-surface border border-border-subtle flex items-center justify-center text-muted shadow-[var(--shadow-soft)]">
                  <svg className="w-8 h-8 text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-foreground">Couldn&apos;t load document</h4>
                  <p className="text-xs text-muted mt-1 max-w-[280px] leading-relaxed">
                    The file could not be loaded from the server. Check that it is still indexed.
                  </p>
                </div>
                <button
                  onClick={() => setRetryKey((k) => k + 1)}
                  className="text-xs px-4 py-2 rounded-xl bg-accent hover:bg-accent-strong text-accent-foreground font-semibold shadow-md transition-all cursor-pointer"
                >
                  Try Again
                </button>
              </div>
            ) : pdfUrl && !citation.source.toLowerCase().endsWith(".txt") ? (
              <iframe
                key={`${citation.source}-${currentPage}-${retryKey}`}
                src={`${pdfUrl}#page=${currentPage}`}
                className="w-full h-full border-none bg-surface-2"
                title={`PDF Viewer - ${citation.source}`}
              />
            ) : citation.source.startsWith("YouTube -") ? (
              <iframe
                key={`${citation.source}-${currentPage}-${retryKey}`}
                src={`https://www.youtube.com/embed/${citation.source.match(/\((.{11})\)\.txt/)?.[1] || ""}?start=${currentPage}&autoplay=1`}
                className="w-full h-full border-none bg-foreground"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
                title={`YouTube Viewer - ${citation.source}`}
              />
            ) : txtContent ? (
              <div className="w-full h-full overflow-y-auto p-8 bg-paper text-foreground font-mono text-sm leading-relaxed whitespace-pre-wrap select-text">
                {txtContent}
              </div>
            ) : null}

            {citation.text && (
              <div
                className={`
                  absolute bottom-6 left-6 right-6 z-20 flex flex-col
                  bg-surface/95 backdrop-blur-md border border-border-subtle rounded-xl shadow-[var(--shadow-card)]
                  transition-all duration-300 max-w-xl mx-auto
                `}
              >
                <button
                  onClick={() => setIsExcerptExpanded((ex) => !ex)}
                  className="flex items-center justify-between px-4 py-3 text-left text-foreground hover:bg-surface-2/60 cursor-pointer select-none rounded-xl"
                >
                  <span className="text-xs font-bold flex items-center gap-2 text-accent">
                    <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                    </svg>
                    Retrieved passage
                  </span>
                  <span className="text-[10px] text-muted flex items-center gap-1 font-semibold uppercase tracking-wider">
                    {isExcerptExpanded ? "Hide" : "Show"}
                    <svg
                      className={`w-3.5 h-3.5 transform transition-transform duration-200 ${
                        isExcerptExpanded ? "rotate-180" : ""
                      }`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 9l-7 7-7-7" />
                    </svg>
                  </span>
                </button>

                {isExcerptExpanded && (
                  <div className="px-4 pb-4 border-t border-border-subtle pt-3 select-text">
                    <div className="bg-accent-soft border-l-2 border-accent pl-3 pr-2 py-2 rounded-r-lg max-h-36 overflow-y-auto">
                      <p className="text-[11px] text-foreground leading-relaxed italic pr-1">
                        &ldquo;{citation.text}&rdquo;
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
