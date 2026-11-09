"use client";

import { useEffect, useState } from "react";
import type { SearchSystem, Source } from "../chat-stream";

type Question = { id: string; type: string; question: string; expected_answer: string; required_sources: string[] };
type Result = Question & {
  answer: string | null; sources: Source[]; source_coverage: number | null; response_time_seconds: number; error: string | null;
};
type Summary = { total: number; successful: number; average_source_coverage: number | null; average_response_time_seconds: number | null };
type Evaluation = { results: Result[]; summary: Summary; categories: Record<string, Summary> };
const systems: SearchSystem[] = ["vector", "graph"];
const names = { vector: "Vector RAG", graph: "Graph RAG" };

function coverage(value: number | null) { return value === null ? "—" : `${(value * 100).toFixed(1)}%`; }
function seconds(value: number | null) { return value === null ? "—" : `${value.toFixed(2)} s`; }

export default function Evaluate() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [evaluations, setEvaluations] = useState<Partial<Record<SearchSystem, Evaluation>>>({});
  const [running, setRunning] = useState<SearchSystem | null>(null);
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

  async function runEvaluation(system: SearchSystem) {
    setRunning(system); setMessage("");
    try {
      const response = await fetch("/api/evaluate", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ system }),
      });
      if (!response.ok) throw new Error();
      const evaluation: Evaluation = await response.json();
      setEvaluations(previous => ({ ...previous, [system]: evaluation }));
    } catch { setMessage(`${names[system]} evaluation could not be completed. Please try again.`); }
    finally { setRunning(null); }
  }

  const summaries = [];
  for (const system of systems) {
    const evaluation = evaluations[system];
    if (!evaluation) continue;
    for (const [category, summary] of Object.entries({ Overall: evaluation.summary, ...evaluation.categories })) {
      summaries.push({ system, category, summary });
    }
  }

  return (
    <main className="container">
      <h1>Evaluation</h1>
      <p className="muted">Compare both search systems on the same 12 built-in questions. Vector RAG uses Standard search with four seed excerpts.</p>
      <div className="evaluation-actions">{systems.map(system => <button key={system} onClick={() => runEvaluation(system)} disabled={running !== null}>
        {running === system ? `Running ${names[system]}…` : `Run ${names[system]}`}
      </button>)}</div>
      <p className="muted" role="status">{running ? "Evaluating all questions. This may take a few minutes." : message}</p>
      <section className="panel">
        <h2>Results</h2>
        <p className="muted">Source coverage is the share of expected documents retrieved. It does not measure answer correctness. Averages include completed questions only.</p>
        {summaries.length > 0 && <div className="evaluation-table"><table>
          <thead><tr><th scope="col">System</th><th scope="col">Category</th><th scope="col">Completed</th><th scope="col">Average source coverage</th><th scope="col">Average response time</th></tr></thead>
          <tbody>{summaries.map(({ system, category, summary }) => <tr key={`${system}-${category}`}>
            <th scope="row">{names[system]}</th><td>{category}</td><td>{summary.successful} / {summary.total}</td>
            <td>{coverage(summary.average_source_coverage)}</td><td>{seconds(summary.average_response_time_seconds)}</td>
          </tr>)}</tbody>
        </table></div>}
      </section>
      {questions.map(question => <section className="panel evaluation-result" key={question.id}>
        <h2>{question.id} · {question.type} — {question.question}</h2>
        <p className="evaluation-answer"><strong>Expected answer:</strong> {question.expected_answer}</p>
        <p className="muted">Expected sources: {question.required_sources.join(", ")}</p>
        <div className="answer-comparison">{systems.map(system => {
          const item = evaluations[system]?.results.find(result => result.id === question.id);
          return <div key={system}>
            <h3>{names[system]}</h3>
            {!item ? <p className="muted">No evaluation results yet.</p> : <>
              {item.error && <p className="evaluation-error" role="alert">{item.error}</p>}
              <p className="muted">Source coverage: {coverage(item.source_coverage)} · Response time: {seconds(item.response_time_seconds)}</p>
              <p className="evaluation-answer">{item.answer ?? "No answer was returned."}</p>
              <h3>Retrieved sources</h3>
              {item.sources.length ? <ul>{item.sources.map(source => <li key={source.reference}>
                <strong>{source.reference}</strong><p className="muted">{source.snippet}</p>
              </li>)}</ul> : <p className="muted">{item.error ? "Unavailable for this question." : "No sources were retrieved."}</p>}
            </>}
          </div>;
        })}</div>
      </section>)}
    </main>
  );
}
