export type Source = { source: string; chunk: number; reference: string; snippet: string };
export type SearchSystem = "vector" | "graph";
export type VectorMode = "standard" | "multi-step";
export type ChatEvent =
  | { type: "sources"; sources: Source[]; top_k: number }
  | { type: "token"; text: string }
  | { type: "done" }
  | { type: "error"; message: string };

export function requestChat(question: string, system: SearchSystem, mode: VectorMode, signal: AbortSignal) {
  return fetch("/api/chat/stream", {
    method: "POST", headers: { "Content-Type": "application/json" }, signal,
    body: JSON.stringify({ question, top_k: 4, mode: system === "graph" ? "graph" : mode }),
  });
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
          const event: ChatEvent = JSON.parse(data);
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
