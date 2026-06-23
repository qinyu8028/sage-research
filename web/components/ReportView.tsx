"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

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

export default function ReportView({ report, stats }: ReportViewProps) {
  const { body, sourcesHeading, sources } = processReport(report);

  return (
    <div className="px-10 pt-12 pb-20">
      <article className="report-prose" onClick={handleCitationClick}>
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
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
