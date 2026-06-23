"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ReportViewProps {
  report: string;
  stats: { total_calls: number; total_tokens: number } | null;
}

export default function ReportView({ report, stats }: ReportViewProps) {
  return (
    <div className="max-w-3xl mx-auto px-10 pt-12 pb-20">
      <article className="report-prose">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{report}</ReactMarkdown>
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
