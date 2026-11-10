import type { Source } from "./chat-stream";

export type EvaluationMode = "standard" | "multi-step" | "graph";
export const evaluationModes: EvaluationMode[] = ["standard", "multi-step", "graph"];
export const evaluationNames = { standard: "Vector Standard", "multi-step": "Vector Multi-step", graph: "Graph RAG" };
export type Question = { id: string; type: string; question: string; expected_answer: string; required_sources: string[] };
export type Calls = { llm: number; vector_searches: number; graph_queries: number };
export type Result = Question & {
  answer: string | null; sources: Source[]; source_coverage: number | null; response_time_seconds: number;
  error: string | null; status: string; note: string | null; calls: Calls | null;
};
export type Summary = {
  total: number; successful: number; incomplete: number;
  average_source_coverage: number | null; average_response_time_seconds: number | null; calls: Calls | null;
};
export type Evaluation = {
  system: EvaluationMode; results: Result[]; summary: Summary; categories: Record<string, Summary>; completed_at: string;
  corpus: { documents: number; chunks: number; top_k: number; fingerprint: string };
};
export type Evaluations = Partial<Record<EvaluationMode, Evaluation>>;

export function coverage(value: number | null) { return value === null ? "—" : `${(value * 100).toFixed(1)}%`; }
export function seconds(value: number | null) { return value === null ? "—" : `${value.toFixed(2)} s`; }

export function evidenceStatus(status: string) {
  const labels: Record<string, string> = {
    complete: "Expected sources found", partial: "Some expected sources missing", missing: "No usable evidence",
    insufficient: "Intermediate evidence unverified", unsupported: "Question unsupported", error: "Request failed",
  };
  return labels[status] ?? status;
}

export function work(calls: Calls | null) {
  if (!calls) return "Call counts unavailable";
  const parts = [`${calls.llm} model calls`];
  if (calls.vector_searches) parts.push(`${calls.vector_searches} vector searches`);
  if (calls.graph_queries) parts.push(`${calls.graph_queries} graph queries`);
  return parts.join(", ");
}

export function canDownloadReport(evaluations: Evaluations): boolean {
  const baseline = evaluations.standard;
  if (!baseline || !baseline.corpus.fingerprint || baseline.corpus.chunks < 1) return false;
  for (const mode of evaluationModes) {
    const run = evaluations[mode];
    if (!run || run.system !== mode || !run.completed_at || run.results.length === 0) return false;
    if (run.summary.total !== run.results.length || run.results.length !== baseline.results.length) return false;
    if (run.corpus.fingerprint !== baseline.corpus.fingerprint || run.corpus.documents !== baseline.corpus.documents ||
        run.corpus.chunks !== baseline.corpus.chunks || run.corpus.top_k !== 4) return false;
    const ids = new Set<string>();
    for (let index = 0; index < run.results.length; index++) {
      const item = run.results[index], expected = baseline.results[index];
      if (ids.has(item.id) || item.id !== expected.id || item.type !== expected.type || item.question !== expected.question ||
          item.expected_answer !== expected.expected_answer || item.required_sources.join("|") !== expected.required_sources.join("|")) return false;
      ids.add(item.id);
    }
  }
  return true;
}

function quote(text: string) {
  const lines = [];
  for (const line of text.replace(/\r\n/g, "\n").split("\n")) lines.push("> " + line);
  return lines.join("\n");
}

export function evaluationReport(evaluations: Evaluations): string {
  if (!canDownloadReport(evaluations)) throw new Error("Run all three modes on the same corpus and questions first.");
  const baseline = evaluations.standard!;
  const { documents, chunks, top_k } = baseline.corpus;
  const lines = [
    "# Benchmark answers", "",
    `HelioWorks has ${documents} synthetic business documents and ${chunks} chunks, split at 650 characters with 65-character overlap. Vector Standard retrieves ${top_k} excerpts per question (${(100 * top_k / chunks).toFixed(2)}% of the chunks). All modes use the same ${baseline.results.length} seed-only questions.`, "",
    "- Vector Standard: one vector search, top_k=4.",
    "- Vector Multi-step: up to three dependent vector searches, with verified extraction and one retry when needed.",
    "- Graph RAG: validated read templates over reviewed facts, with selected supporting chunks; meeting and email-only facts can be unsupported.", "",
    "Source coverage measures retrieved expected documents, not answer correctness. Times describe these runs, not a performance guarantee. Model calls include planning, extraction retries and answer generation. Counts cover finished questions, exclude readiness checks and are unavailable for errors. Embedding calls, token usage and monetary cost are not estimated.", "",
    "## Results", "",
    "| Mode | Category | Finished | Source coverage | Average time |",
    "|---|---|---:|---:|---:|",
  ];
  for (const mode of evaluationModes) {
    const run = evaluations[mode]!;
    for (const [category, summary] of Object.entries({ Overall: run.summary, ...run.categories })) {
      lines.push(`| ${evaluationNames[mode]} | ${category} | ${summary.successful}/${summary.total} | ${coverage(summary.average_source_coverage)} | ${seconds(summary.average_response_time_seconds)} |`);
    }
  }
  lines.push("", "Averages include finished questions, including incomplete retrieval; errors are listed below.", "");
  for (const mode of evaluationModes) {
    const run = evaluations[mode]!;
    lines.push(`${evaluationNames[mode]} — completed ${run.completed_at}; ${work(run.summary.calls)}.`, "");
  }
  lines.push("## Answers", "");
  for (let index = 0; index < baseline.results.length; index++) {
    const expected = baseline.results[index];
    lines.push(`### ${expected.id} · ${expected.type} — ${expected.question}`, "", "Expected answer:", "", quote(expected.expected_answer), "",
               `Relevant sources: ${expected.required_sources.join(", ")}.`, "");
    for (const mode of evaluationModes) {
      const item = evaluations[mode]!.results[index];
      lines.push(`**${evaluationNames[mode]}**`, "", quote(item.answer ?? "No answer returned."), "");
      const references = [];
      for (const source of item.sources) references.push(source.reference);
      lines.push(`Retrieved sources: ${references.length ? references.join(", ") : "none"}.`, "",
                 `Source coverage: ${coverage(item.source_coverage)} · Time: ${seconds(item.response_time_seconds)} · Evidence: ${evidenceStatus(item.status)} · ${work(item.calls)}.`, "");
      if (item.error) lines.push(`Error: ${item.error}`, "");
      if (item.note) lines.push(`Note: ${item.note}`, "");
    }
  }
  lines.push("## Missing evidence", "");
  let observations = 0, gaps = 0;
  for (const mode of evaluationModes) {
    let examples = 0;
    for (const item of evaluations[mode]!.results) {
      if (!item.error && item.status === "complete" && item.source_coverage === 1) continue;
      gaps++;
      if (examples >= 2) continue;
      let reason = item.error || item.note || "Some expected source documents were not retrieved.";
      const retrieved = new Set<string>();
      for (const source of item.sources) retrieved.add(source.source);
      const missing = [];
      for (const source of item.required_sources) {
        if (!retrieved.has(source)) missing.push(source);
      }
      if (!item.error && missing.length) reason += ` Missing: ${missing.join(", ")}.`;
      if (mode === "standard" && !item.error && item.required_sources.length > top_k) {
        reason += ` Four excerpts can cover at most four of the ${item.required_sources.length} required documents.`;
      }
      lines.push(`- ${item.id}, ${evaluationNames[mode]}: ${reason}`);
      observations++; examples++;
    }
  }
  if (!observations) lines.push("No missing expected source documents were recorded. Answer correctness still needs manual review.");
  if (gaps > observations) lines.push("", `Showing ${observations} examples from ${gaps} evidence gaps; all question-level details appear above.`);
  return lines.join("\n").trimEnd() + "\n";
}
