export type Source = { source: string; chunk: number; reference: string; snippet: string };
export type SearchSystem = "vector" | "graph";
export type VectorMode = "standard" | "multi-step";
export type ChatEvent =
  | { type: "sources"; sources: Source[]; top_k: number }
  | { type: "token"; text: string }
  | { type: "done" }
  | { type: "error"; message: string };

export function requestChat(question: string, system: SearchSystem, mode: VectorMode, signal: AbortSignal, filename?: string) {
  return fetch("/api/chat/stream", {
    method: "POST", headers: { "Content-Type": "application/json" }, signal,
    body: JSON.stringify({ question, top_k: 4, mode: system === "graph" ? "graph" : mode, filename: system === "graph" ? filename : undefined }),
  });
}

function decodeEvent(data: string): ChatEvent {
  const event: unknown = JSON.parse(data);
  if (!event || typeof event !== "object" || !("type" in event)) throw new Error("Invalid chat event.");
  if (event.type === "done") return { type: "done" };
  if (event.type === "token" && "text" in event && typeof event.text === "string") return { type: "token", text: event.text };
  if (event.type === "error" && "message" in event && typeof event.message === "string") return { type: "error", message: event.message };
  if (event.type === "sources" && "sources" in event && Array.isArray(event.sources) &&
      "top_k" in event && typeof event.top_k === "number" && Number.isInteger(event.top_k)) {
    const sources: Source[] = [];
    for (const item of event.sources as unknown[]) {
      if (!item || typeof item !== "object" || !("source" in item) || typeof item.source !== "string" ||
          !("chunk" in item) || typeof item.chunk !== "number" || !Number.isInteger(item.chunk) ||
          !("reference" in item) || typeof item.reference !== "string" || !("snippet" in item) || typeof item.snippet !== "string") {
        throw new Error("Invalid chat source.");
      }
      sources.push({ source: item.source, chunk: item.chunk, reference: item.reference, snippet: item.snippet });
    }
    return { type: "sources", sources, top_k: event.top_k };
  }
  throw new Error("Invalid chat event.");
}

export async function readChatStream(response: Response, onEvent: (event: ChatEvent) => void, signal: AbortSignal) {
  signal.throwIfAborted();
  if (!response.ok || !response.body) throw new Error("The answer could not be started.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const cancel = () => { void reader.cancel().catch(() => {}); };
  signal.addEventListener("abort", cancel, { once: true });
  try {
    while (true) {
      const { value, done } = await reader.read();
      signal.throwIfAborted();
      if (done) throw new Error("The answer was interrupted.");
      buffer += decoder.decode(value, { stream: true });
      buffer = buffer.replace(/\r\n/g, "\n");
      let boundary = buffer.indexOf("\n\n");
      while (boundary >= 0) {
        signal.throwIfAborted();
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        let data = "";
        for (const line of frame.split("\n")) {
          if (line.startsWith("data:")) data += line.slice(5).trimStart() + "\n";
        }
        if (data) {
          const event = decodeEvent(data);
          onEvent(event);
          if (event.type === "error") throw new Error(event.message);
          if (event.type === "done") return;
        }
        boundary = buffer.indexOf("\n\n");
      }
    }
  } finally {
    signal.removeEventListener("abort", cancel);
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
