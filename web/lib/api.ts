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
