"use client";

import { useEffect, useRef, useState } from "react";

type Mode = "typewriter" | "word-fade" | "skeleton" | "dots-then-text" | "dots";

export default function StreamingText({
  text,
  mode,
  speed,
  pause,
  onComplete,
}: {
  text: string;
  mode: Mode;
  speed?: "normal" | "slow";
  pause?: number;
  onComplete?: () => void;
}) {
  switch (mode) {
    case "typewriter":
      return <Typewriter text={text} speed={speed} pause={pause} onComplete={onComplete} />;
    case "word-fade":
      return <WordFade text={text} onComplete={onComplete} />;
    case "skeleton":
      return <Skeleton text={text} onComplete={onComplete} />;
    case "dots-then-text":
      return <DotsTheText text={text} onComplete={onComplete} />;
    case "dots":
      return <Dots text={text} />;
  }
}

function Typewriter({
  text,
  speed,
  pause,
  onComplete,
}: {
  text: string;
  speed?: "normal" | "slow";
  pause?: number;
  onComplete?: () => void;
}) {
  const [index, setIndex] = useState(0);
  const [done, setDone] = useState(false);
  const called = useRef(false);
  const slow = speed === "slow";

  useEffect(() => {
    if (index >= text.length) {
      const wait = pause ?? 0;
      const timer = setTimeout(() => {
        setDone(true);
        if (onComplete && !called.current) {
          called.current = true;
          onComplete();
        }
      }, wait);
      return () => clearTimeout(timer);
    }
    const delay = text[index] === " " ? (slow ? 68 : 34) : (slow ? 45 : 20);
    const timer = setTimeout(() => setIndex(index + 1), delay);
    return () => clearTimeout(timer);
  }, [index, text, onComplete, pause]);

  return (
    <span>
      {text.slice(0, index)}
      {!done && <span className="caret" />}
    </span>
  );
}

function WordFade({
  text,
  onComplete,
}: {
  text: string;
  onComplete?: () => void;
}) {
  const tokens = splitTokens(text);
  const [revealed, setRevealed] = useState(0);
  const called = useRef(false);
  const wordCount = tokens.filter((t) => !t.space).length;

  useEffect(() => {
    if (revealed >= wordCount) {
      if (onComplete && !called.current) {
        called.current = true;
        onComplete();
      }
      return;
    }
    const timer = setTimeout(() => setRevealed(revealed + 1), 72);
    return () => clearTimeout(timer);
  }, [revealed, wordCount, onComplete]);

  let wordIdx = 0;
  return (
    <span>
      {tokens.map((t, i) => {
        if (t.space) return <span key={i}>{t.text}</span>;
        const current = wordIdx++;
        return (
          <span
            key={i}
            className={`tok-fade${current < revealed ? " in" : ""}`}
          >
            {t.text}
          </span>
        );
      })}
    </span>
  );
}

function Skeleton({
  text,
  onComplete,
}: {
  text: string;
  onComplete?: () => void;
}) {
  const [phase, setPhase] = useState<"skeleton" | "text">("skeleton");

  useEffect(() => {
    const timer = setTimeout(() => setPhase("text"), 1500);
    return () => clearTimeout(timer);
  }, []);

  if (phase === "skeleton") {
    return (
      <div>
        <div className="sk-bar" style={{ width: "100%" }} />
        <div className="sk-bar" style={{ width: "92%" }} />
        <div className="sk-bar" style={{ width: "58%" }} />
      </div>
    );
  }

  return <WordFade text={text} onComplete={onComplete} />;
}

function DotsTheText({
  text,
  onComplete,
}: {
  text: string;
  onComplete?: () => void;
}) {
  const [phase, setPhase] = useState<"dots" | "text">("dots");

  useEffect(() => {
    const timer = setTimeout(() => setPhase("text"), 1150);
    return () => clearTimeout(timer);
  }, []);

  if (phase === "dots") {
    return (
      <div className="dots-pulse">
        <i />
        <i />
        <i />
      </div>
    );
  }

  return <WordFade text={text} onComplete={onComplete} />;
}

function Dots({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-2 text-muted-foreground">
      <div className="dots-pulse">
        <i />
        <i />
        <i />
      </div>
      <span className="text-sm">{text}</span>
    </div>
  );
}

function splitTokens(text: string) {
  return text
    .split(/(\s+)/)
    .filter((s) => s.length > 0)
    .map((s) => ({ space: /^\s+$/.test(s), text: s }));
}
