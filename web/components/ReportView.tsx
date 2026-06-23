"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeRaw from "rehype-raw";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { saveReport } from "@/lib/api";

interface ReportViewProps {
  report: string;
  stats: { total_calls: number; total_tokens: number } | null;
}

interface SourceItem {
  id: string;
  text: string;
}

interface ProcessedReport {
  body: string;
  sourcesHeading: string;
  sources: SourceItem[];
}

function processReport(raw: string): ProcessedReport {
  const headingMatch = raw.match(
    /^(#{1,3})\s*(Sources|References|参考文献)\s*$/m,
  );
  if (!headingMatch) {
    return { body: raw, sourcesHeading: "", sources: [] };
  }

  const heading = headingMatch[0];
  const splitIdx = headingMatch.index!;
  const body = raw.slice(0, splitIdx);
  const sourcesText = raw.slice(splitIdx + heading.length).trim();

  const processedBody = body.replace(
    /\[(\d+)\](?!\()/g,
    '<a href="#source-$1" class="citation-link">[$1]</a>',
  );

  const sources: SourceItem[] = [];
  for (const line of sourcesText.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const m = trimmed.match(/^\[(\d+)\]/);
    if (m) {
      sources.push({ id: m[1], text: trimmed });
    }
  }

  return { body: processedBody, sourcesHeading: heading, sources };
}

function handleCitationClick(e: React.MouseEvent<HTMLElement>) {
  const link = (e.target as HTMLElement).closest("a.citation-link");
  if (!link) return;
  e.preventDefault();
  const id = link.getAttribute("href")?.slice(1);
  if (!id) return;
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

const sourceComponents = {
  p: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
};

function extractTitle(md: string): string {
  const m = md.match(/^#\s+(.+)$/m);
  return m ? m[1].trim() : "research-report";
}

export default function ReportView({ report, stats }: ReportViewProps) {
  const { body, sourcesHeading, sources } = processReport(report);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");

  function handlePrint() {
    const prev = document.title;
    document.title = extractTitle(report);
    window.print();
    setTimeout(() => { document.title = prev; }, 100);
  }

  async function handleSave() {
    if (saveState !== "idle") return;
    setSaveState("saving");
    try {
      await saveReport(extractTitle(report), report);
      setSaveState("saved");
    } catch {
      setSaveState("idle");
    }
  }

  return (
    <div className="px-10 pt-5 pb-20">
      <div className="print-hide flex justify-end gap-2 mb-1.5">
        <button
          onClick={handleSave}
          disabled={saveState !== "idle"}
          className={`inline-flex items-center gap-1.5 text-[13px] rounded-lg px-3 py-1.5 active:scale-95 transition-all duration-200 ${
            saveState === "saved"
              ? "text-approved bg-approved/10 border border-approved/20"
              : "text-foreground/70 bg-surface border border-foreground/10 hover:text-muted-foreground hover:bg-transparent hover:border-border"
          } ${saveState === "saving" ? "opacity-60 cursor-wait" : ""}`}
        >
          {saveState === "saved" ? (
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
              <path d="M20 6L9 17l-5-5" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
              <polyline points="17 21 17 13 7 13 7 21" />
              <polyline points="7 3 7 8 15 8" />
            </svg>
          )}
          {saveState === "saved" ? "已保存" : saveState === "saving" ? "保存中..." : "保存到文献库"}
        </button>
        <button
          onClick={handlePrint}
          className="inline-flex items-center gap-1.5 text-[13px] text-foreground/70 bg-surface border border-foreground/10 rounded-lg px-3 py-1.5 hover:text-muted-foreground hover:bg-transparent hover:border-border active:scale-95 transition-all duration-200"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10V4a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v6M5 10h14a2 2 0 0 1 2 2v3H3v-3a2 2 0 0 1 2-2z" />
            <circle cx="12" cy="15" r="1" />
          </svg>
          打印 PDF
        </button>
      </div>
      <article className="report-prose" onClick={handleCitationClick}>
        <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeRaw, rehypeKatex]}>
          {body}
        </ReactMarkdown>
        {sources.length > 0 && (
          <>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {sourcesHeading}
            </ReactMarkdown>
            {sources.map((s) => (
              <div key={s.id} id={`source-${s.id}`} className="source-item">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={sourceComponents}
                >
                  {s.text}
                </ReactMarkdown>
              </div>
            ))}
          </>
        )}
      </article>
      {stats && (
        <div className="mt-16 pt-4 border-t border-foreground/10 text-[13px] text-foreground/35 flex gap-6 font-mono">
          <span>{stats.total_calls} API calls</span>
          <span>{stats.total_tokens.toLocaleString()} tokens</span>
        </div>
      )}
    </div>
  );
}
