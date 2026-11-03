import assert from "node:assert/strict";
import test from "node:test";
import { readChatStream } from "../app/chat-stream.ts";

const source = { source: "projects/bridge.md", chunk: 0, reference: "projects/bridge.md#0", snippet: "Tamás Fekete" };
const sources = { type: "sources", sources: [source], top_k: 4 };
const done = { type: "done" };

function frames(events, newline = "\n") {
  let text = "";
  for (const event of events) text += `data: ${JSON.stringify(event)}${newline}${newline}`;
  return new TextEncoder().encode(text);
}

function response(chunks, cancel = () => {}, keepOpen = false) {
  let index = 0;
  return new Response(new ReadableStream({
    pull(controller) {
      if (index < chunks.length) controller.enqueue(chunks[index++]);
      else if (!keepOpen) controller.close();
    },
    cancel,
  }), { headers: { "Content-Type": "text/event-stream" } });
}

test("split UTF-8 characters and SSE frames preserve source order and assemble partial answers", async () => {
  const events = [sources, { type: "token", text: "Tamás " }, { type: "token", text: "Fekete\n[Source: projects/bridge.md#0]" }, done];
  const chunks = [];
  for (const byte of frames(events)) chunks.push(Uint8Array.of(byte));
  const received = [];
  let answer = "";
  await readChatStream(response(chunks), event => {
    received.push(event);
    if (event.type === "token") answer += event.text;
  }, new AbortController().signal);
  assert.deepEqual(received, events);
  assert.equal(answer, "Tamás Fekete\n[Source: projects/bridge.md#0]");
});

test("CRLF boundaries and multiple events in one chunk are read correctly", async () => {
  const received = [];
  await readChatStream(response([frames([sources, done], "\r\n")]), event => received.push(event), new AbortController().signal);
  assert.deepEqual(received, [sources, done]);
});

test("server errors preserve the partial answer and do not become successful completion", async () => {
  const events = [sources, { type: "token", text: "Partial answer" }, { type: "error", message: "The answer could not be completed." }];
  let answer = "";
  await assert.rejects(readChatStream(response([frames(events)]), event => {
    if (event.type === "token") answer += event.text;
  }, new AbortController().signal), /could not be completed/);
  assert.equal(answer, "Partial answer");
});

test("unexpected end without a done event is an error", async () => {
  await assert.rejects(readChatStream(response([frames([sources])]), () => {}, new AbortController().signal), /interrupted/);
});

test("abort interrupts a pending read and cancels the HTTP reader", async () => {
  const controller = new AbortController();
  let cancelled = 0;
  let seen;
  const tokenSeen = new Promise(resolve => { seen = resolve; });
  const pending = readChatStream(response([frames([sources, { type: "token", text: "Partial" }])], () => { cancelled++; }, true), event => {
    if (event.type === "token") seen();
  }, controller.signal);
  await tokenSeen;
  controller.abort();
  await assert.rejects(pending, { name: "AbortError" });
  assert.equal(cancelled, 1);
});

test("abort prevents additional buffered tokens from being displayed", async () => {
  const controller = new AbortController();
  const events = [sources, { type: "token", text: "First" }, { type: "token", text: "Second" }, done];
  let answer = "";
  await assert.rejects(readChatStream(response([frames(events)]), event => {
    if (event.type === "token") { answer += event.text; controller.abort(); }
  }, controller.signal), { name: "AbortError" });
  assert.equal(answer, "First");
});

test("HTTP failures and malformed stream frames are rejected", async () => {
  await assert.rejects(readChatStream(new Response("Unavailable", { status: 503 }), () => {}, new AbortController().signal));
  await assert.rejects(readChatStream(response([new TextEncoder().encode("data: broken\n\n")]), () => {}, new AbortController().signal));
});
