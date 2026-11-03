"use client";

import { useEffect, useRef, useState } from "react";
import { readChatStream, type Source } from "./chat-stream";

type ChatResult = { answer: string; sources: Source[]; top_k: number };
type CorpusStatus = { documents: number; indexed_chunks: number; ready: boolean; seed_ready: boolean };
type UploadResult = { filename: string; unchanged: boolean };

export default function Home() {
  const [corpus, setCorpus] = useState<CorpusStatus | null>(null);
  const [available, setAvailable] = useState(true);
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<ChatResult | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploadMessage, setUploadMessage] = useState("");
  const [uploadError, setUploadError] = useState(false);
  const [mode, setMode] = useState("standard");
  const [streaming, setStreaming] = useState(false);
  const controller = useRef<AbortController | null>(null);

  async function refresh() {
    try {
      const response = await fetch("/api/corpus");
      if (!response.ok) throw new Error("Service unavailable");
      setCorpus(await response.json());
      setAvailable(true);
    } catch { setAvailable(false); }
  }

  useEffect(() => {
    void refresh();
    return () => { controller.current?.abort(); };
  }, []);

  async function request(path: string, body?: object) {
    const response = await fetch(path, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) throw new Error("The request could not be completed.");
    return response.json();
  }

  async function indexCorpus() {
    setBusy(true); setMessage("Preparing documents...");
    try {
      await request("/api/ingest/seed");
      setMessage("Documents are ready.");
      await refresh();
    } catch (error) { setMessage(String(error)); }
    finally { setBusy(false); }
  }

  async function ask() {
    if (question.trim().length < 3 || controller.current) return;
    const current = new AbortController();
    controller.current = current;
    setBusy(true); setStreaming(true); setMessage("Searching documents…"); setResult(null);
    try {
      const response = await fetch("/api/chat/stream", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, top_k: 4, mode }), signal: current.signal,
      });
      await readChatStream(response, event => {
        if (event.type === "sources") {
          setResult({ answer: "", sources: event.sources, top_k: event.top_k });
          setMessage("Writing answer…");
        }
        if (event.type === "token") {
          setResult(previous => previous ? { ...previous, answer: previous.answer + event.text } : previous);
          setMessage("");
        }
      }, current.signal);
      setMessage("");
    } catch {
      setMessage(current.signal.aborted ? "Response stopped." : "The answer could not be completed. Please try again.");
    } finally {
      controller.current = null;
      setBusy(false); setStreaming(false);
    }
  }

  async function upload() {
    if (!file) return;
    setBusy(true); setUploadError(false); setUploadMessage(`Adding ${file.name}…`);
    let failure = "The document could not be added. Please try again.";
    try {
      const body = new FormData();
      body.append("file", file);
      const response = await fetch("/api/ingest/upload", { method: "POST", body });
      if (!response.ok) {
        const error = await response.json();
        if (typeof error.detail === "string") failure = error.detail;
        throw new Error();
      }
      const result: UploadResult = await response.json();
      setUploadMessage(`${result.filename} ${result.unchanged ? "is already available." : "is ready to search."}`);
      await refresh();
    } catch {
      setUploadError(true);
      setUploadMessage(`${file.name}: ${failure}`);
    } finally { setBusy(false); }
  }

  return (
    <main className="container">
      <h1>Knowledge assistant</h1>
      <p className="muted">Search company documents and your uploads, and explore their sources.</p>
      {!available && <p role="status">Knowledge base is unavailable.</p>}
      <div className="columns">
        <section className="panel">
          <h2>Chat</h2>
          <label htmlFor="search-mode" className="muted">Search mode</label>
          <select id="search-mode" value={mode} disabled={busy} onChange={event => setMode(event.target.value)}>
            <option value="standard">Standard</option><option value="multi-step">Multi-step</option>
          </select>
          <label htmlFor="question" className="muted">Your question</label>
          <textarea id="question" value={question} onChange={event => setQuestion(event.target.value)} placeholder="Ki vezeti az Atlas projektet?" />
          <button onClick={ask} disabled={busy || !corpus?.ready || question.trim().length < 3}>Ask</button>
          {streaming && <button className="stop" onClick={() => controller.current?.abort()}>Stop</button>}
          {message && <p className="muted" role="status">{message}</p>}
          {result && <div className="answer"><h2>Answer</h2><p>{result.answer}</p><h2 className="section-title">Sources</h2>
            <ul>{result.sources.map(source => <li key={source.reference}><strong>{source.reference}</strong><p className="muted">{source.snippet}</p></li>)}</ul>
          </div>}
        </section>
        <section className="panel">
          <h2>Documents</h2>
          {corpus && <p className="muted">{corpus.documents} built-in documents available.</p>}
          {corpus?.ready && <p className="muted">Ready to search.</p>}
          {corpus && !corpus.seed_ready && <button onClick={indexCorpus} disabled={busy}>Prepare documents</button>}
          <h2 className="section-title">Upload a document</h2>
          <p className="muted">TXT, MD, PDF, DOCX, HTML or XLSX · Up to 10 MB</p>
          <label htmlFor="document" className="muted">Choose a document</label>
          <input id="document" type="file" accept=".txt,.md,.pdf,.docx,.html,.xlsx" disabled={busy}
            onChange={event => { setFile(event.target.files?.[0] ?? null); setUploadMessage(""); }} />
          <button onClick={upload} disabled={busy || !file}>Upload</button>
          {uploadMessage && <p className={uploadError ? "evaluation-error" : "muted"} role={uploadError ? "alert" : "status"}>{uploadMessage}</p>}
        </section>
      </div>
    </main>
  );
}
