const API_BASE = "http://localhost:8000";

export interface ClarifyResult {
  is_clear: boolean;
  brief: string | null;
  directions: string[];
  message: string | null;
}

export interface RefineResult {
  brief: string;
}

export async function clarify(query: string): Promise<ClarifyResult> {
  const res = await fetch(`${API_BASE}/api/clarify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  return res.json();
}

export async function refine(query: string, response: string): Promise<RefineResult> {
  const res = await fetch(`${API_BASE}/api/clarify/refine`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, response }),
  });
  return res.json();
}

// --- SSE Research Events ---

export type ResearchEvent =
  | { type: "plan"; sub_questions: { label: string; question: string }[] }
  | { type: "research"; question: string; preview: string; tool_call_counts: Record<string, number> }
  | { type: "review"; round: number; review_summary: { question: string; verdict: string; failed: Record<string, boolean>; evidence?: Record<string, string> }[]; missing_dimensions?: string }
  | { type: "write"; report: string }
  | { type: "stats"; total_calls: number; prompt_tokens: number; completion_tokens: number; total_tokens: number }
  | { type: "error"; message: string };

export function startResearch(
  brief: string,
  onEvent: (event: ResearchEvent) => void,
): () => void {
  const controller = new AbortController();

  fetch(`${API_BASE}/api/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ brief }),
    signal: controller.signal,
  })
    .then((res) => {
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      function pump(): Promise<void> {
        return reader.read().then(({ done, value }) => {
          if (done) return;
          buffer += decoder.decode(value, { stream: true });

          const blocks = buffer.split("\n\n");
          buffer = blocks.pop()!;

          for (const block of blocks) {
            let eventType = "";
            let data = "";
            for (const line of block.split("\n")) {
              if (line.startsWith("event: ")) eventType = line.slice(7);
              else if (line.startsWith("data: ")) data = line.slice(6);
            }
            if (eventType && data) {
              onEvent({ type: eventType, ...JSON.parse(data) } as ResearchEvent);
            }
          }

          return pump();
        });
      }

      return pump();
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onEvent({ type: "error", message: err.message });
      }
    });

  return () => controller.abort();
}
