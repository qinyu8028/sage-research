"use client";

import { useEffect, useState } from "react";
import { clarify, refine, type ClarifyResult } from "@/lib/api";

export default function ClarifyPanel({
  query,
  onBriefReady,
}: {
  query: string;
  onBriefReady: (brief: string) => void;
}) {
  const [result, setResult] = useState<ClarifyResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [customInput, setCustomInput] = useState("");
  const [refining, setRefining] = useState(false);

  useEffect(() => {
    clarify(query).then((data) => {
      if (data.is_clear && data.brief) {
        onBriefReady(data.brief);
      } else {
        setResult(data);
        setLoading(false);
      }
    });
  }, [query]);

  async function handleSelect(direction: string) {
    setRefining(true);
    const data = await refine(query, direction);
    onBriefReady(data.brief);
  }

  async function handleCustomSubmit() {
    const trimmed = customInput.trim();
    if (!trimmed) return;
    setRefining(true);
    const data = await refine(query, trimmed);
    onBriefReady(data.brief);
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <span className="inline-block w-4 h-4 border-2 border-muted-foreground/30 border-t-accent rounded-full animate-spin" />
        正在分析问题...
      </div>
    );
  }

  if (refining) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <span className="inline-block w-4 h-4 border-2 border-muted-foreground/30 border-t-accent rounded-full animate-spin" />
        正在生成研究方案...
      </div>
    );
  }

  return (
    <div className="w-full max-w-2xl space-y-6">
      {result?.message && (
        <p className="text-lg">{result.message}</p>
      )}

      {result?.directions && result.directions.length > 0 && (
        <div className="space-y-2">
          {result.directions.map((direction, i) => (
            <button
              key={i}
              onClick={() => handleSelect(direction)}
              className="w-full text-left rounded-xl bg-surface border border-foreground/10 hover:border-foreground/25 px-4 py-3 transition-colors"
            >
              {direction}
            </button>
          ))}
        </div>
      )}

      <div className="relative">
        <input
          value={customInput}
          onChange={(e) => setCustomInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleCustomSubmit();
            }
          }}
          placeholder="或者输入你的具体方向..."
          className="w-full rounded-xl bg-surface border border-foreground/10 hover:border-foreground/25 focus:border-foreground/25 focus:outline-none px-4 py-3 pr-14 font-mono placeholder:text-muted-foreground/60 placeholder:font-mono transition-colors"
        />
        <button
          onClick={handleCustomSubmit}
          disabled={!customInput.trim()}
          className="absolute right-3 bottom-3 rounded-lg bg-accent p-2 text-surface hover:bg-accent-hover disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="w-4 h-4"
          >
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </div>
  );
}
