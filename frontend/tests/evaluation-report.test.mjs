// Offline formatter fixtures only. They are never saved as benchmark results.
import assert from "node:assert/strict";
import test from "node:test";
import { canDownloadReport, evaluationModes, evaluationReport } from "../app/evaluation-report.ts";

function summarize(results) {
  let successful = 0, coverage = 0, seconds = 0, incomplete = 0;
  const calls = { llm: 0, vector_searches: 0, graph_queries: 0 };
  for (const result of results) {
    if (result.error) continue;
    successful++; coverage += result.source_coverage; seconds += result.response_time_seconds;
    if (result.status !== "complete") incomplete++;
    for (const key of Object.keys(calls)) calls[key] += result.calls[key];
  }
  return { total: results.length, successful, incomplete, average_source_coverage: successful ? coverage / successful : null,
           average_response_time_seconds: successful ? seconds / successful : null, calls: successful ? calls : null };
}

function fixtures() {
  const runs = {};
  for (const mode of evaluationModes) {
    const results = [];
    for (const [id, type, count] of [["FORMAT-1", "local", 1], ["FORMAT-2", "global", 6]]) {
      const required = [];
      for (let index = 0; index < count; index++) required.push(`fixture/source-${index}.md`);
      const found = mode === "standard" ? required.slice(0, 4) : required;
      const sources = [];
      for (const source of found) sources.push({ source, chunk: 0, reference: `${source}#0`, snippet: "Offline source fixture" });
      results.push({ id, type, question: `Offline formatter fixture ${id}`, expected_answer: "Expected fixture text",
        required_sources: required, answer: `OFFLINE FORMAT FIXTURE: ${mode} ${id}`, sources,
        source_coverage: found.length / required.length, response_time_seconds: 0.125, error: null,
        status: found.length === required.length ? "complete" : "partial", note: null,
        calls: { llm: mode === "multi-step" ? 5 : 2, vector_searches: mode === "graph" ? 0 : mode === "multi-step" ? 3 : 1, graph_queries: mode === "graph" ? 2 : 0 } });
    }
    const categories = {};
    for (const category of ["local", "multi-hop", "global"]) categories[category] = summarize(results.filter(item => item.type === category));
    runs[mode] = { system: mode, results, summary: summarize(results), categories, completed_at: "offline fixture time",
                   corpus: { documents: 34, chunks: 158, top_k: 4, fingerprint: "offline-fixture" } };
  }
  return runs;
}

test("report requires all three completed modes with the same corpus and questions", () => {
  const runs = fixtures();
  assert.equal(canDownloadReport(runs), true);
  for (const mode of evaluationModes) {
    const missing = { ...runs }; delete missing[mode];
    assert.equal(canDownloadReport(missing), false);
    assert.throws(() => evaluationReport(missing), /Run all three/);
  }
  for (const change of [
    run => { run.corpus.fingerprint = "different"; },
    run => { run.results[0].question = "Changed question"; },
    run => { run.results[0].expected_answer = "Changed expected answer"; },
    run => { run.results[0].required_sources = ["other.md"]; },
    run => { run.results.pop(); },
    run => { run.completed_at = ""; },
    run => { run.results[1].id = run.results[0].id; },
  ]) {
    const changed = fixtures(); change(changed.graph);
    assert.equal(canDownloadReport(changed), false);
  }
});

test("Markdown preserves supplied answers, sources, all categories, timings and work", () => {
  const runs = fixtures();
  const report = evaluationReport(runs);
  assert.match(report, /34 synthetic business documents and 158 chunks/);
  assert.match(report, /2\.53%/);
  for (const mode of evaluationModes) {
    for (const result of runs[mode].results) assert.ok(report.includes(result.answer));
  }
  for (const category of ["Overall", "local", "multi-hop", "global"]) assert.ok(report.includes(`| ${category} |`));
  assert.match(report, /fixture\/source-5\.md#0/);
  assert.match(report, /66\.7%/);
  assert.match(report, /0\.13 s/);
  assert.match(report, /5 model calls, 3 vector searches/);
  assert.match(report, /Four excerpts can cover at most four of the 6 required documents/);
  assert.match(report, /not answer correctness/);
  assert.doesNotMatch(report, /semantic accuracy|91\.7%|88\.9%/);
});

test("unsupported, insufficient and failed runs remain visible without fabricated answers or times", () => {
  const runs = fixtures();
  const graph = runs.graph.results[1];
  Object.assign(graph, { answer: "Unsupported fixture", sources: [], source_coverage: 0, status: "unsupported", note: "Outside the reviewed graph operations." });
  const multi = runs["multi-step"].results[1];
  Object.assign(multi, { answer: "No verified intermediate fixture", status: "insufficient", note: "Extraction could not be verified after one retry." });
  const failed = runs.standard.results[0];
  Object.assign(failed, { answer: null, sources: [], source_coverage: null, error: "Offline service failure fixture", status: "error", calls: null });
  for (const mode of evaluationModes) runs[mode].summary = summarize(runs[mode].results);
  const report = evaluationReport(runs);
  assert.match(report, /> No answer returned\./);
  assert.match(report, /Source coverage: —/);
  assert.match(report, /Error: Offline service failure fixture/);
  assert.match(report, /Evidence: Question unsupported/);
  assert.match(report, /Evidence: Intermediate evidence unverified/);
  assert.match(report, /Call counts unavailable/);
  assert.match(report, /Extraction could not be verified after one retry/);
});

test("multiline answers stay quoted and successful evidence does not claim semantic correctness", () => {
  const runs = fixtures();
  runs.graph.results[0].answer = "First line\n## A heading inside an answer\nLast line";
  for (const mode of evaluationModes) {
    Object.assign(runs[mode].results[1], { status: "complete", source_coverage: 1 });
  }
  const report = evaluationReport(runs);
  assert.match(report, /> First line\n> ## A heading inside an answer\n> Last line/);
  assert.match(report, /Answer correctness still needs manual review/);
});

test("observations name actual missing documents and keep at most two examples per mode", () => {
  const runs = fixtures();
  for (const mode of evaluationModes) {
    const sample = runs[mode].results[1];
    const results = [];
    for (let index = 0; index < 5; index++) {
      results.push({ ...sample, id: `GAP-${index}`, sources: [], source_coverage: 0, status: "missing" });
    }
    runs[mode].results = results;
    runs[mode].summary = summarize(results);
  }
  const observations = evaluationReport(runs).split("## Missing evidence\n")[1];
  assert.equal(observations.split("\n").filter(line => line.startsWith("- ")).length, 6);
  assert.match(observations, /Missing: fixture\/source-0\.md/);
  assert.match(observations, /Showing 6 examples from 15 evidence gaps/);
  for (const label of ["Vector Standard", "Vector Multi-step", "Graph RAG"]) assert.ok(observations.includes(label));
});
