"use client";

import { useEffect, useState } from "react";
import { canDownloadReport, coverage, evaluationModes, evaluationNames, evaluationReport, evidenceStatus, seconds, work,
         type Evaluation, type EvaluationMode, type Evaluations, type Question } from "../evaluation-report";

export default function Evaluate() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [evaluations, setEvaluations] = useState<Evaluations>({});
  const [running, setRunning] = useState<EvaluationMode | null>(null);
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

  async function runEvaluation(system: EvaluationMode) {
    setRunning(system); setMessage("");
    try {
      const response = await fetch("/api/evaluate", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ system }),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(typeof error.detail === "string" ? error.detail : "Evaluation could not be completed.");
      }
      const evaluation: Evaluation = await response.json();
      setEvaluations(previous => ({ ...previous, [system]: evaluation }));
    } catch (error) { setMessage(`${evaluationNames[system]}: ${error instanceof Error ? error.message : "Evaluation could not be completed."}`); }
    finally { setRunning(null); }
  }

  function downloadReport() {
    const report = evaluationReport(evaluations);
    const url = URL.createObjectURL(new Blob([report], { type: "text/markdown;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url; link.download = "baseline_answers.md"; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  const summaries = [];
  for (const system of evaluationModes) {
    const evaluation = evaluations[system];
    if (!evaluation) continue;
    for (const [category, summary] of Object.entries({ Overall: evaluation.summary, ...evaluation.categories })) {
      summaries.push({ system, category, summary });
    }
  }

  return (
    <main className="container">
      <h1>Evaluation</h1>
      <p className="muted">Compare three searches on the same {questions.length || "built-in"} questions. Vector Standard retrieves four seed excerpts; Multi-step and Graph RAG can do more work.</p>
      <div className="evaluation-actions">{evaluationModes.map(system => <button key={system} onClick={() => runEvaluation(system)} disabled={running !== null}>
        {running === system ? `Running ${evaluationNames[system]}…` : `Run ${evaluationNames[system]}`}
      </button>)}
        <button onClick={downloadReport} disabled={running !== null || !canDownloadReport(evaluations)}>Download evaluation report</button>
      </div>
      <p className="muted" role="status">{running ? "Evaluating all questions. This may take a few minutes." : message}</p>
      <section className="panel">
        <h2>Results</h2>
        <p className="muted">Source coverage is the share of expected documents retrieved. It does not measure answer correctness. Averages include completed questions only.</p>
        {summaries.length > 0 && <div className="evaluation-table"><table>
          <thead><tr><th scope="col">Mode</th><th scope="col">Category</th><th scope="col">Finished</th><th scope="col">Incomplete evidence</th><th scope="col">Source coverage</th><th scope="col">Average time</th><th scope="col">Work in finished questions</th></tr></thead>
          <tbody>{summaries.map(({ system, category, summary }) => <tr key={`${system}-${category}`}>
            <th scope="row">{evaluationNames[system]}</th><td>{category}</td><td>{summary.successful} / {summary.total}</td><td>{summary.incomplete}</td>
            <td>{coverage(summary.average_source_coverage)}</td><td>{seconds(summary.average_response_time_seconds)}</td><td>{work(summary.calls)}</td>
          </tr>)}</tbody>
        </table></div>}
      </section>
      {questions.map(question => <section className="panel evaluation-result" key={question.id}>
        <h2>{question.id} · {question.type} — {question.question}</h2>
        <p className="evaluation-answer"><strong>Expected answer:</strong> {question.expected_answer}</p>
        <p className="muted">Expected sources: {question.required_sources.join(", ")}</p>
        <div className="answer-comparison evaluation-comparison">{evaluationModes.map(system => {
          const item = evaluations[system]?.results.find(result => result.id === question.id);
          return <div key={system}>
            <h3>{evaluationNames[system]}</h3>
            {!item ? <p className="muted">No evaluation results yet.</p> : <>
              {item.error && <p className="evaluation-error" role="alert">{item.error}</p>}
              <p className="muted">Source coverage: {coverage(item.source_coverage)} · Response time: {seconds(item.response_time_seconds)}</p>
              <p className="muted">Evidence: {evidenceStatus(item.status)} · {work(item.calls)}</p>
              {item.note && <p className="muted">{item.note}</p>}
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
