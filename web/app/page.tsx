"use client";

import { useState } from "react";
import QueryInput from "@/components/QueryInput";
import ClarifyPanel, { resetClarifyCache } from "@/components/ClarifyPanel";
import ResearchProgress from "@/components/ResearchProgress";
import ReportView from "@/components/ReportView";
import StreamingText from "@/components/StreamingText";

export default function Home() {
  const [stage, setStage] = useState<"input" | "sending" | "clarify" | "researching" | "report">("input");
  const [query, setQuery] = useState("");
  const [brief, setBrief] = useState("");
  const [report, setReport] = useState("");
  const [stats, setStats] = useState<{ total_calls: number; total_tokens: number } | null>(null);
  const [exiting, setExiting] = useState(false);

  function handleQuerySubmit(q: string) {
    setQuery(q);
    setStage("sending");
    setTimeout(() => setStage("clarify"), 400);
  }

  function handleBriefReady(b: string) {
    setBrief(b);
    setStage("researching");
  }

  function handleBack() {
    setExiting(true);
    setTimeout(() => {
      resetClarifyCache();
      setStage("input");
      setBrief("");
      setReport("");
      setStats(null);
      setExiting(false);
    }, 350);
  }

  const isReport = stage === "report";

  return (
    <>
      {(stage === "input" || stage === "sending") && (
        <div className="flex flex-1 flex-col items-center px-4">
          <HeroSection onSubmit={handleQuerySubmit} sending={stage === "sending"} />
        </div>
      )}

      {stage !== "input" && stage !== "sending" && (
        <div className={`relative flex flex-1 w-full overflow-hidden min-h-0 ${exiting ? "back-exit" : ""}`}>
          {/* Left spacer — provides centering, collapses on report */}
          <div
            className="transition-[flex] duration-700 ease-[cubic-bezier(0.2,0.8,0.2,1)]"
            style={{ flex: isReport ? "0 0 0px" : "1 1 0px" }}
          />

          {/* Chat panel */}
          <div className="w-full max-w-3xl shrink-0 overflow-y-auto min-h-0 px-4 thin-scroll" data-scroll-container>
            {/* Sticky back button — stays within chat panel bounds */}
            <div
              className="sticky top-0 z-10 pointer-events-none -mx-4 px-4"
              style={{ background: "linear-gradient(to bottom, var(--background) 55%, transparent)", height: 50 }}
            >
              <button
                onClick={handleBack}
                className="pointer-events-auto mt-4 inline-flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground active:scale-95 transition-all duration-200"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                  strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
                  <path d="M19 12H5M12 19l-7-7 7-7" />
                </svg>
                返回
              </button>
            </div>
            <div className="pb-16 gap-4 flex flex-col">
              <ClarifyPanel query={query} onBriefReady={handleBriefReady} />

              {(stage === "researching" || isReport) && (
                <ResearchProgress
                  brief={brief}
                  onReport={(r, s) => {
                    setReport(r);
                    if (s) setStats({ total_calls: s.total_calls, total_tokens: s.total_tokens });
                    setStage("report");
                  }}
                />
              )}
            </div>
          </div>

          {/* Report panel */}
          <div
            data-report-panel
            className={`flex-1 min-w-0 overflow-y-auto min-h-0 thin-scroll transition-opacity duration-500 ease-out ${
              isReport
                ? "opacity-100 border-l border-foreground/8 bg-surface/40"
                : "opacity-0 pointer-events-none"
            }`}
          >
            {report && <ReportView report={report} stats={stats} />}
          </div>
        </div>
      )}
    </>
  );
}

function HeroSection({
  onSubmit,
  sending,
}: {
  onSubmit: (q: string) => void;
  sending?: boolean;
}) {
  const [showSubtitle, setShowSubtitle] = useState(false);

  return (
    <div className={`flex flex-1 flex-col items-center w-full ${sending ? "hero-exit" : ""}`}>
      <div className="flex flex-1 flex-col items-center justify-center">
        <h1 className="text-4xl font-medium w-full text-center">
          <StreamingText text="SAGE Research" mode="typewriter" speed="slow" pause={350} onComplete={() => setShowSubtitle(true)} />
        </h1>
        <div
          className={`w-full overflow-hidden transition-all duration-1000 ease-[cubic-bezier(0.2,0.8,0.2,1)] ${
            showSubtitle ? "max-h-16 opacity-100 mt-3" : "max-h-0 opacity-0 mt-0"
          }`}
        >
          <p className="text-lg text-foreground/65 tracking-wide text-center pl-[1.1em]">
            输入一个研究问题，开始探索。
          </p>
        </div>
      </div>
      <div className="w-full flex justify-center pb-8">
        <QueryInput onSubmit={onSubmit} disabled={sending} />
      </div>
    </div>
  );
}
