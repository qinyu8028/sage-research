"use client";

import { useEffect, useRef, useState } from "react";
import { clarify, refine, type ClarifyResult } from "@/lib/api";
import StreamingText from "@/components/StreamingText";

type ChatMsg =
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; animate?: "word-fade" | "typewriter" }
  | { role: "assistant-loading"; content: string }
  | { role: "assistant-directions"; message: string; directions: string[] }
  | { role: "assistant-brief"; content: string };

let msgId = 0;
function nextId() {
  return ++msgId;
}

let _clarifyCache: {
  query: string;
  messages: (ChatMsg & { id: number })[];
  settled: boolean;
} | null = null;

export function resetClarifyCache() {
  _clarifyCache = null;
}

export default function ClarifyPanel({
  query,
  onBriefReady,
}: {
  query: string;
  onBriefReady: (brief: string) => void;
}) {
  const hit = _clarifyCache?.query === query ? _clarifyCache : null;

  const [messages, setMessages] = useState<(ChatMsg & { id: number })[]>(
    () =>
      hit?.messages ?? [
        { id: nextId(), role: "user", content: query.trim() },
        { id: nextId(), role: "assistant-loading", content: "正在分析问题" },
      ],
  );
  const [customInput, setCustomInput] = useState("");
  const [settled, setSettled] = useState(() => hit?.settled ?? false);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const [inputFlash, setInputFlash] = useState(false);
  const [revealDirections, setRevealDirections] = useState(!!hit);
  const [revealBrief, setRevealBrief] = useState(!!hit);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pendingBriefRef = useRef<string | null>(null);

  useEffect(() => {
    _clarifyCache = { query, messages, settled };
  });

  useEffect(() => {
    if (hit) return;

    let cancelled = false;
    clarify(query).then((data) => {
      if (cancelled) return;
      if (data.is_clear && data.brief) {
        const brief = data.brief;
        pendingBriefRef.current = brief;
        setMessages((prev) => [
          prev[0],
          { id: nextId(), role: "assistant-brief", content: brief },
        ]);
      } else {
        setMessages((prev) => [
          prev[0],
          {
            id: nextId(),
            role: "assistant-directions",
            message: data.message || "",
            directions: data.directions,
          },
        ]);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [query]);

  function handleCardClick(direction: string) {
    const el = textareaRef.current;
    if (el) {
      el.style.transition = "none";
      el.style.color = "transparent";
      void el.offsetHeight;
      el.style.transition = "color 0.5s ease-out, background-color 0.4s, border-color 0.4s";
      el.style.color = "";
    }

    setCustomInput(direction);
    setInputFlash(true);
    setTimeout(() => setInputFlash(false), 600);

    setTimeout(() => {
      if (el) {
        el.focus();
        el.setSelectionRange(direction.length, direction.length);
        el.style.height = "auto";
        el.style.height = el.scrollHeight + "px";
      }
    }, 0);
  }

  function handleSubmit() {
    const trimmed = customInput.trim();
    if (!trimmed) return;
    setCustomInput("");
    setSettled(true);
    setRevealBrief(false);
    const userMsgId = nextId();
    const loadingMsgId = nextId();
    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: "user", content: trimmed },
      { id: loadingMsgId, role: "assistant-loading", content: "收到，正在整理研究方案..." },
    ]);
    refine(query, trimmed).then((data) => {
      pendingBriefRef.current = data.brief;
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { id: nextId(), role: "assistant-brief", content: data.brief },
      ]);
    });
  }

  function autoResize() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.transition = "none";
    el.style.height = "auto";
    const target = el.scrollHeight + "px";
    if (el.style.height !== target) {
      el.style.height = el.dataset.prevHeight || target;
      void el.offsetHeight;
      el.style.transition = "height 0.2s ease";
      el.style.height = target;
    }
    el.dataset.prevHeight = target;
  }

  return (
    <div className="w-full max-w-2xl flex flex-col gap-4">
      {messages.map((msg) => {
        if (msg.role === "user") {
          return <UserBubble key={msg.id} text={msg.content} />;
        }
        if (msg.role === "assistant-loading") {
          return (
            <AssistantMsg key={msg.id}>
              <StreamingText text={msg.content} mode="dots" />
            </AssistantMsg>
          );
        }
        if (msg.role === "assistant-directions") {
          return (
            <AssistantMsg key={msg.id}>
              <p className={`text-[15px] leading-relaxed ${!settled ? "mb-4" : ""}`}>
                <StreamingText text={msg.message} mode="typewriter" onComplete={() => setRevealDirections(true)} />
              </p>
              {!settled && revealDirections && (
                <>
                  <div className="flex flex-col gap-2.5">
                    {msg.directions.map((dir, j) => {
                      const isHovered = hoveredIdx === j;
                      const isActive = customInput === dir;
                      return (
                        <button
                          key={j}
                          onClick={() => handleCardClick(dir)}
                          onMouseEnter={() => setHoveredIdx(j)}
                          onMouseLeave={() => setHoveredIdx(null)}
                          className={`bubble-enter relative w-full text-left rounded-xl border pl-5 py-3 pr-4 text-[14px] leading-snug active:scale-[0.98] ease-[cubic-bezier(0.2,0.8,0.2,1)] ${
                            isActive
                              ? "bg-accent text-surface border-accent"
                              : "bg-surface border-foreground/10 hover:-translate-y-0.5 hover:scale-[1.01] hover:shadow-[0_4px_12px_rgba(0,0,0,0.06)]"
                          }`}
                          style={{
                            animationDelay: `${j * 60 + 100}ms`,
                            transition: "background-color 0.35s, border-color 0.35s, color 0.35s, box-shadow 0.2s, scale 0.12s, translate 0.12s",
                          }}
                        >
                          <span
                            className={`absolute left-2.5 top-2.5 w-[2.5px] rounded-full transition-all duration-300 ease-[cubic-bezier(0.2,0.8,0.2,1)] ${
                              isHovered
                                ? `h-[calc(100%-21px)] ${isActive ? "bg-surface" : "bg-accent"}`
                                : "h-0 bg-accent"
                            }`}
                          />
                          {dir}
                        </button>
                      );
                    })}
                    <div
                      className="relative bubble-enter"
                      style={{ animationDelay: `${msg.directions.length * 60 + 160}ms` }}
                    >
                      <textarea
                        ref={textareaRef}
                        value={customInput}
                        onChange={(e) => {
                          setCustomInput(e.target.value);
                          autoResize();
                        }}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault();
                            handleSubmit();
                          }
                        }}
                        placeholder="或者输入你的具体方向..."
                        rows={1}
                        className={`w-full rounded-xl border pl-5 py-3 pr-14 font-mono text-sm placeholder:text-muted-foreground/60 placeholder:font-mono resize-none overflow-hidden focus:outline-none ${
                          inputFlash
                            ? "bg-accent/15 border-accent/40"
                            : "bg-surface border-foreground/10 hover:border-foreground/25 focus:border-foreground/25"
                        }`}
                      />
                      <button
                        onClick={handleSubmit}
                        disabled={!customInput.trim()}
                        className="absolute right-2 bottom-3.5 rounded-lg bg-accent p-1.5 text-surface hover:bg-accent-hover active:scale-90 disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-150"
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
                </>
              )}
            </AssistantMsg>
          );
        }
        if (msg.role === "assistant-brief") {
          return (
            <AssistantMsg key={msg.id}>
              <p className="text-[15px] leading-relaxed">
                <StreamingText text="好的，研究方向已确认，即将开始研究：" mode="typewriter" onComplete={() => setRevealBrief(true)} />
              </p>
              {revealBrief && (
                <p className="text-[15px] leading-relaxed mt-1.5 text-foreground/70">
                  <StreamingText
                    text={msg.content}
                    mode="typewriter"
                    onComplete={() => {
                      if (pendingBriefRef.current) {
                        onBriefReady(pendingBriefRef.current);
                        pendingBriefRef.current = null;
                      }
                    }}
                  />
                </p>
              )}
            </AssistantMsg>
          );
        }
        if (msg.role === "assistant") {
          return (
            <AssistantMsg key={msg.id}>
              <p className="text-[15px] leading-relaxed">
                <StreamingText
                  text={msg.content}
                  mode={msg.animate || "word-fade"}
                />
              </p>
            </AssistantMsg>
          );
        }
      })}
    </div>
  );
}

function UserBubble({ text }: { text: string }) {
  return (
    <div className="flex justify-end bubble-enter">
      <div className="bg-foreground/85 text-surface px-4 py-2.5 rounded-2xl rounded-br-sm max-w-[84%] text-[14px] leading-snug whitespace-pre-wrap">
        {text.trim()}
      </div>
    </div>
  );
}

function AssistantMsg({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5 bubble-enter">
      <div className="flex items-center gap-1.5 font-mono text-[10px] tracking-widest uppercase text-muted-foreground">
        <span className="w-1.5 h-1.5 rounded-full bg-foreground/70" />
        Assistant
      </div>
      <div>{children}</div>
    </div>
  );
}
