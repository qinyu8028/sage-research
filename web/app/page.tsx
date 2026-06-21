"use client";

import { useState } from "react";
import QueryInput from "@/components/QueryInput";
import ClarifyPanel from "@/components/ClarifyPanel";

export default function Home() {
  const [stage, setStage] = useState<"input" | "clarify" | "researching" | "report">("input");
  const [query, setQuery] = useState("");
  const [brief, setBrief] = useState("");

  function handleQuerySubmit(q: string) {
    setQuery(q);
    setStage("clarify");
  }

  function handleBriefReady(b: string) {
    setBrief(b);
    setStage("researching");
  }

  return (
    <div className="flex flex-1 flex-col items-center px-4">
      {stage === "input" && (
        <>
          <div className="flex flex-1 items-center justify-center">
            <h1 className="text-3xl font-medium">SAGE Research</h1>
          </div>
          <div className="w-full flex justify-center pb-8">
            <QueryInput onSubmit={handleQuerySubmit} />
          </div>
        </>
      )}

      {stage === "clarify" && (
        <div className="flex flex-1 items-center justify-center">
          <ClarifyPanel query={query} onBriefReady={handleBriefReady} />
        </div>
      )}

      {stage === "researching" && (
        <div className="flex flex-1 flex-col items-center pt-16 w-full max-w-2xl">
          <div className="border-l-2 border-approved pl-4 mb-8">
            <p className="text-lg italic">{brief}</p>
          </div>
          <p className="text-muted-foreground">研究阶段（待实现）</p>
        </div>
      )}
    </div>
  );
}
