"use client";

import { useEffect, useState } from "react";

type Question = { id: string; type: string; question: string; expected_answer: string; required_sources: string[] };
type Source = { source: string; chunk: number; reference: string; snippet: string };
type Result = Question & {
  answer: string | null; sources: Source[]; source_coverage: number | null; response_time_seconds: number; error: string | null;
};
type Summary = { total: number; successful: number; average_source_coverage: number | null; average_response_time_seconds: number | null };
type Evaluation = { results: Result[]; summary: Summary; categories: Record<string, Summary> };

function coverage(value: number | null) { return value === null ? "—" : `${(value * 100).toFixed(1)}%`; }
function seconds(value: number | null) { return value === null ? "—" : `${value.toFixed(2)} s`; }

export default function Evaluate() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    async function loadQuestions() {
      try {
        const response = await fetch("/api/questions");
        if (!response.ok) throw new Error();
        setQuestions(await response.json());
      } catch { setMessage("Test questions could not be loaded."); }
    }
    void loadQuestions();
  }, []);

  async function runEvaluation() {
    setBusy(true); setMessage("");
    try {
      const response = await fetch("/api/evaluate", { method: "POST" });
      if (!response.ok) throw new Error();
      setEvaluation(await response.json());
    } catch { setMessage("Evaluation could not be completed. Please try again."); }
    finally { setBusy(false); }
  }

  const summaries: Record<string, Summary> = evaluation ? { Overall: evaluation.summary, ...evaluation.categories } : {};

  return (
    <main className="container">
      <h1>Evaluation</h1>
      <p className="muted">Compare generated answers with expected answers and check source coverage.</p>
      <button onClick={runEvaluation} disabled={busy}>{busy ? "Running evaluation…" : "Run Evaluation"}</button>
      <p className="muted" role="status">{busy ? "Evaluating all questions. This may take a few minutes." : message}</p>
      {!evaluation && <section className="panel">
        <h2>Test questions ({questions.length})</h2>
        <ul>{questions.map(item => <li key={item.id}><strong>{item.id} · {item.type}</strong> — {item.question}</li>)}</ul>
      </section>}
      {evaluation && <>
        <section className="panel">
          <h2>Results</h2>
          <p className="muted">Source coverage is the share of expected documents retrieved. It does not measure answer correctness. Averages include completed questions only.</p>
          <div className="evaluation-table">
            <table>
              <thead><tr><th scope="col">Category</th><th scope="col">Completed</th><th scope="col">Average source coverage</th><th scope="col">Average response time</th></tr></thead>
              <tbody>{Object.entries(summaries).map(([category, summary]) => <tr key={category}>
                <th scope="row">{category}</th><td>{summary.successful} / {summary.total}</td>
                <td>{coverage(summary.average_source_coverage)}</td><td>{seconds(summary.average_response_time_seconds)}</td>
              </tr>)}</tbody>
            </table>
          </div>
        </section>
        {evaluation.results.map(item => <section className="panel evaluation-result" key={item.id}>
          <h2>{item.id} · {item.type} — {item.question}</h2>
          {item.error && <p className="evaluation-error" role="alert">{item.error}</p>}
          <p className="muted">Source coverage: {coverage(item.source_coverage)} · Response time: {seconds(item.response_time_seconds)}</p>
          <div className="answer-comparison">
            <div><h3>Generated answer</h3><p className="evaluation-answer">{item.answer ?? "No answer was returned."}</p></div>
            <div><h3>Expected answer</h3><p className="evaluation-answer">{item.expected_answer}</p></div>
          </div>
          <div className="answer-comparison">
            <div><h3>Retrieved sources</h3>
              {item.sources.length ? <ul>{item.sources.map(source => <li key={source.reference}>
                <strong>{source.reference}</strong><p className="muted">{source.snippet}</p>
              </li>)}</ul> : <p className="muted">{item.error ? "Unavailable for this question." : "No sources were retrieved."}</p>}
            </div>
            <div><h3>Expected sources</h3><ul>{item.required_sources.map(source => <li key={source}>{source}</li>)}</ul></div>
          </div>
        </section>)}
      </>}
    </main>
  );
}
