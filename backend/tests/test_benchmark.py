import asyncio
import json
import os
import unittest
from contextlib import ExitStack
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import AsyncMock, Mock, call, patch
from uuid import NAMESPACE_URL, uuid5

import anyio
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.runnables import RunnableLambda
from qdrant_client import QdrantClient

from app import chat, graph, graph_seed, main, rag, evaluation
from app.evaluation import run_evaluation

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = json.loads((ROOT / "evaluation/questions.json").read_text(encoding="utf-8"))


class MultiStepConnectionTests(unittest.TestCase):
    def test_twelve_evaluation_questions_reuse_the_application_loop_and_real_sdk_connection(self):
        # Real SDK and HTTP keep-alive, with canned responses served only on loopback.
        schemas = []
        document = Document(page_content="Nóra Varga leads Project Atlas.", metadata={"source": "projects/atlas.md", "chunk": 0})

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass

            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                schema = request.get("response_format", {}).get("json_schema", {}).get("name")
                schemas.append(schema)
                content = "Nóra Varga [Source: projects/atlas.md#0]"
                if schema == "QueryPlan":
                    content = json.dumps({"steps": [{"question": "Who leads Project Atlas?", "uses_previous": False}]})
                elif schema == "GroundedFact":
                    content = json.dumps({"value": "Nóra Varga", "reference": "projects/atlas.md#0", "quote": document.page_content})
                reply = {"id": "offline-completion", "object": "chat.completion", "created": 0, "model": request["model"],
                         "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content}}],
                         "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
                body = json.dumps(reply).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                self.wfile.flush()

        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            server.daemon_threads = True
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                environment = {"OPENAI_API_KEY": "offline-test-key", "OPENAI_BASE_URL": f"http://127.0.0.1:{server.server_port}/v1",
                               "OPENAI_CHAT_MODEL": "gpt-6-luna", "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false"}
                with patch.dict(os.environ, environment), TestClient(main.app) as api, ExitStack() as stack:
                    stack.enter_context(patch.object(main, "load_questions", return_value=QUESTIONS))
                    stack.enter_context(patch.object(evaluation, "corpus_status", return_value={"seed_ready": True}))
                    stack.enter_context(patch.object(evaluation, "seed_manifest", return_value={"documents": 34, "chunks": 170, "top_k": 4, "fingerprint": "offline"}))
                    stack.enter_context(patch.object(chat, "client", return_value=Mock()))
                    make = stack.enter_context(patch.object(chat, "make_retriever", return_value=Mock(ainvoke=AsyncMock(return_value=[document]))))
                    model = rag.chat_model()
                    self.assertIs(model.root_async_client._client, rag.chat_model().root_async_client._client)
                    response = api.post("/api/evaluate", json={"system": "multi-step"})
                    try:
                        result = response.json()
                        failed = []
                        for item in result["results"]:
                            if item["error"]:
                                failed.append(item["id"])
                        self.assertEqual(failed, [], f"Technical failures: {failed}")
                        self.assertEqual(result["summary"]["successful"], 12)
                        self.assertEqual(schemas, ["QueryPlan", "GroundedFact", None] * 12)
                        for item in result["results"]:
                            self.assertEqual(item["answer"], "Nóra Varga [Source: projects/atlas.md#0]")
                            self.assertEqual(item["sources"][0]["reference"], "projects/atlas.md#0")
                            self.assertEqual(item["calls"], {"llm": 3, "vector_searches": 1, "graph_queries": 0})
                        for invocation in make.call_args_list:
                            self.assertEqual(invocation.args[1:], (4, True))
                    finally:
                        # Close this test's pooled client while the application loop is still alive.
                        api.portal.call(model.root_async_client.close)
            finally:
                server.shutdown()
                thread.join(timeout=2)

    def test_chat_and_evaluation_share_the_application_loop_and_multistep_algorithm(self):
        loops = []
        document = Document(page_content="Offline evidence.", metadata={"source": "fixture.md", "chunk": 0})
        async def documents(*args, **kwargs):
            loops.append(asyncio.get_running_loop())
            return [document], True
        async def tokens(inputs):
            yield "Offline grounded answer"
        chain = Mock(ainvoke=AsyncMock(return_value="Offline grounded answer"), astream=Mock(side_effect=tokens))
        with TestClient(main.app) as api, ExitStack() as stack:
            stack.enter_context(patch.object(main, "load_questions", return_value=QUESTIONS))
            stack.enter_context(patch.object(evaluation, "corpus_status", return_value={"seed_ready": True}))
            stack.enter_context(patch.object(evaluation, "seed_manifest", return_value={"documents": 34, "chunks": 170, "top_k": 4, "fingerprint": "offline"}))
            db = stack.enter_context(patch.object(chat, "client", return_value=Mock()))
            make = stack.enter_context(patch.object(chat, "make_retriever", return_value=Mock()))
            shared = stack.enter_context(patch.object(chat, "multi_step_documents", side_effect=documents))
            stack.enter_context(patch.object(chat, "answer_chain", return_value=chain))
            evaluated = api.post("/api/evaluate", json={"system": "multi-step"})
            stream = api.post("/api/chat/stream", json={"question": "Offline question?", "mode": "multi-step"})
        self.assertEqual(evaluated.json()["summary"]["successful"], 12)
        self.assertEqual(shared.await_count, 13)
        self.assertTrue(all(loop is loops[0] for loop in loops))
        self.assertEqual(make.call_args_list[:-1], [call(db.return_value, 4, True)] * 12)
        self.assertEqual(make.call_args_list[-1].args, (db.return_value, 4))
        self.assertIn('"type": "done"', stream.text)
        self.assertIn("Offline grounded answer", stream.text)

    def test_technical_failures_remain_errors_and_log_the_stage_without_private_inputs(self):
        cases = [("Q02", "planner"), ("Q04", "retriever"), ("Q06", "extractor"),
                 ("Q08", "answer"), ("Q10", "invalid_plan"), ("Q12", "missing_plan")]
        document = Document(page_content="Nóra Varga leads Project Atlas.", metadata={"source": "projects/atlas.md", "chunk": 0})
        for question_id, stage in cases:
            with self.subTest(question=question_id, stage=stage), TestClient(main.app) as api, ExitStack() as stack:
                for item in QUESTIONS:
                    if item["id"] == question_id:
                        question = item
                        break
                stack.enter_context(patch.object(main, "load_questions", return_value=[question]))
                stack.enter_context(patch.object(evaluation, "corpus_status", return_value={"seed_ready": True}))
                stack.enter_context(patch.object(evaluation, "seed_manifest", return_value={"documents": 34, "chunks": 170, "top_k": 4, "fingerprint": "offline"}))
                db = stack.enter_context(patch.object(chat, "client", return_value=Mock()))
                retriever = Mock(ainvoke=AsyncMock(return_value=[document]))
                stack.enter_context(patch.object(chat, "make_retriever", return_value=retriever))
                failure = RuntimeError("private sk-offline-secret input https://private.invalid")
                def reply(schema, inputs):
                    if stage == "planner" and schema is chat.QueryPlan:
                        raise failure
                    if stage == "extractor" and schema is chat.GroundedFact:
                        raise failure
                    if schema is chat.QueryPlan:
                        if stage == "invalid_plan":
                            return {"steps": []}
                        if stage == "missing_plan":
                            return None
                        return {"steps": [{"question": "Who leads Project Atlas?", "uses_previous": False}]}
                    return {"value": "Nóra Varga", "reference": "projects/atlas.md#0", "quote": document.page_content}
                model = Mock()
                model.with_structured_output.side_effect = lambda schema, **kwargs: RunnableLambda(lambda inputs: reply(schema, inputs))
                stack.enter_context(patch.object(chat, "chat_model", return_value=model))
                if stage == "retriever":
                    retriever.ainvoke.side_effect = failure
                answer = Mock(ainvoke=AsyncMock(return_value="Offline answer"))
                if stage == "answer":
                    answer.ainvoke.side_effect = failure
                stack.enter_context(patch.object(chat, "answer_chain", return_value=answer))
                with self.assertLogs("app.evaluation", level="ERROR") as logs:
                    response = api.post("/api/evaluate", json={"system": "multi-step"})
                result = response.json()["results"][0]
                self.assertEqual(result["status"], "error")
                self.assertIsNone(result["answer"])
                self.assertIsNone(result["source_coverage"])
                self.assertEqual(response.json()["summary"]["successful"], 0)
                logged = " ".join(logs.output)
                self.assertIn(f"multi-step {question_id}", logged)
                self.assertIn("ValidationError" if stage.endswith("plan") else "RuntimeError", logged)
                self.assertNotIn("sk-offline-secret", logged + response.text)
                self.assertNotIn("private.invalid", logged + response.text)
                db.return_value.close.assert_called_once()
                self.assertLessEqual(retriever.ainvoke.await_count, 1)
                self.assertLessEqual(answer.ainvoke.await_count, 1)


class CorpusTests(unittest.TestCase):
    def setUp(self):
        seed_dir = patch.object(rag, "SEED_DIR", ROOT / "data/seed")
        seed_dir.start()
        self.addCleanup(seed_dir.stop)

    def test_real_corpus_has_unique_multichunk_business_documents_without_search_hints(self):
        documents, ids = rag.seed_chunks()
        paths = sorted(rag.SEED_DIR.rglob("*.md"))
        self.assertEqual(len(paths), 34)
        self.assertEqual(len(documents), 170)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertLess(4 / len(documents), 0.03)
        counts, paragraphs = {}, set()
        for document in documents:
            source = document.metadata["source"]
            counts[source] = counts.get(source, 0) + 1
            self.assertTrue(document.page_content.strip())
            self.assertLessEqual(len(document.page_content), 650)
            self.assertEqual(document.metadata["kind"], "seed")
        self.assertTrue(all(count > 1 for count in counts.values()))
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for phrase in ("graphrag", "retrieval", "test question", "corpus", "recorded in the related project",
                           "documented separately", "stored in other documents", "must be found in separate", "for testing retrieval"):
                self.assertNotIn(phrase, text.casefold(), path)
            for paragraph in text.split("\n\n"):
                if len(paragraph) > 150:
                    self.assertNotIn(paragraph, paragraphs, path)
                    paragraphs.add(paragraph)
        manifest = rag.seed_manifest()
        self.assertEqual((manifest["documents"], manifest["chunks"], manifest["top_k"]), (34, 170, 4))
        self.assertEqual(manifest, rag.seed_manifest())

    def test_gold_sources_and_distinguishing_answer_facts_exist_in_the_new_documents(self):
        evidence = {
            "Q01": ["Nóra Váradi", "2027-02-12"], "Q02": ["30 days", "5 days before expiry"],
            "Q03": ["18 applications", "external identity verification service"], "Q04": ["35 minutes", "2026-10-22"],
            "Q05": ["ClearID Kft.", "Project Bridge", "Tamás Fekete", "works in HR"],
            "Q06": ["DataLoom Zrt.", "Project Atlas Archive", "Nóra Váradi"],
            "Q07": ["2026-09-18", "Project Atlas", "NovaCloud Ltd.", "SafeDesk Kft.", "hosting", "alert monitoring"],
            "Q08": ["Project Atlas Archive", "Nóra Váradi", "works in Operations"],
            "Q09": ["2026-11-15", "2027-02-12", "2027-01-20", "2026-12-15", "2026-12-01", "2027-01-11"],
            "Q10": ["NovaCloud Ltd.", "SafeDesk Kft.", "GreenWire Zrt.", "ClearID Kft.", "DataLoom Zrt.", "ClearID Audit Kft."],
            "Q11": ["faulty firmware", "incorrect gateway routing", "print queue quota", "repeated timeouts", "duplicate alert subscription", "incompatible date format"],
            "Q12": ["30 days", "5 days before expiry", "once per year", "quarterly", "24 months", "12 months"],
        }
        categories, seen = {}, set()
        for question in QUESTIONS:
            self.assertNotIn(question["id"], seen)
            seen.add(question["id"])
            self.assertTrue(question["expected_answer"].strip())
            categories[question["type"]] = categories.get(question["type"], 0) + 1
            texts = []
            for source in question["required_sources"]:
                texts.append((rag.SEED_DIR / source).read_text(encoding="utf-8"))
            context = "\n".join(texts).casefold()
            for fact in evidence[question["id"]]:
                self.assertIn(fact.casefold(), context, (question["id"], fact))
        self.assertEqual(categories, {"local": 4, "multi-hop": 4, "global": 4})

    def test_entity_and_relationship_quotes_resolve_to_precise_chunks_and_neighbours(self):
        nodes, edges = graph_seed.seed_graph()
        chunks, entities = {}, {}
        for node in nodes:
            if node["label"] == "Chunk":
                chunks[node["id"]] = node
            elif node["label"] in graph_seed.LABELS:
                entities[node["id"]] = node
        self.assertEqual(len(entities), 34)
        for record in list(entities.values()) + edges:
            proof = record["properties"]
            if "quotes" not in proof:
                continue
            self.assertTrue(proof["chunk_ids"])
            for source, quote, chunk_id in zip(proof["evidence_sources"], proof["quotes"], proof["chunk_ids"], strict=True):
                chunk = chunks[chunk_id]["properties"]
                self.assertEqual(chunk["source"], source)
                self.assertIn(quote, chunk["text"])
        next_edges = []
        for edge in edges:
            if edge["type"] == "NEXT_CHUNK":
                first = chunks[edge["start"]]["properties"]
                second = chunks[edge["end"]]["properties"]
                self.assertEqual(first["source"], second["source"])
                self.assertEqual(first["chunk"] + 1, second["chunk"])
                next_edges.append(edge)
        self.assertEqual(len(next_edges), len(chunks) - 34)
        assignments = set()
        for start, kind, end, _, _ in graph_seed.RELATIONSHIPS:
            if kind == "SUPPLIES":
                assignments.add((start, end))
        self.assertIn(("vendor:dataloom", "project:atlas-archive"), assignments)
        self.assertNotIn(("vendor:dataloom", "project:atlas"), assignments)
        self.assertIn(("vendor:clearid", "project:bridge"), assignments)
        self.assertIn(("vendor:clearid-audit", "project:bridge-north"), assignments)
        self.assertIn(("vendor:safedesk", "project:atlas"), assignments)

    def test_repeated_entities_and_edges_keep_all_original_evidence(self):
        nodes, edges = graph_seed.seed_graph()
        people = []
        employment = []
        for node in nodes:
            if node["id"] == "person:nora-varga":
                people.append(node["properties"])
        for edge in edges:
            if edge["start"] == "person:nora-varga" and edge["type"] == "WORKS_IN":
                employment.append(edge["properties"])
        self.assertEqual((len(people), len(employment)), (1, 1))
        sources = ["people/roles.md", "emails/atlas-window.md"]
        self.assertEqual(people[0]["evidence_sources"], sources)
        self.assertEqual(employment[0]["evidence_sources"], sources)
        self.assertIn("From: Nóra Varga, IT.", employment[0]["quotes"])
        self.assertNotIn(people[0]["description"], people[0]["quotes"])

    def test_an_inexact_business_quote_fails_seed_build(self):
        start, kind, end, source, quote = graph_seed.RELATIONSHIPS[0]
        broken = [(start, kind, end, source, quote.lower())]
        with patch.object(graph_seed, "RELATIONSHIPS", broken), self.assertRaisesRegex(ValueError, "No exact supporting chunk"):
            graph_seed.seed_graph()


class OfflineEmbeddings(Embeddings):
    def embed_documents(self, texts):
        vectors = []
        for _ in texts:
            vectors.append([1.0] + [0.0] * 1535)
        return vectors

    def embed_query(self, text):
        return [1.0] + [0.0] * 1535


class SeedSyncTests(unittest.TestCase):
    def test_qdrant_resync_adds_updates_and_removes_seed_chunks_but_preserves_uploads(self):
        with ExitStack() as stack:
            db = QdrantClient(":memory:")
            self.addCleanup(db.close)
            stack.enter_context(patch.object(db, "close"))
            stack.enter_context(patch.object(rag, "client", return_value=db))
            stack.enter_context(patch.object(rag, "SEED_DIR", ROOT / "data/seed"))
            stack.enter_context(patch.object(rag, "OpenAIEmbeddings", return_value=OfflineEmbeddings()))
            original, original_ids = rag.seed_chunks()
            self.assertGreater(len(original), 100)  # Exercise scroll pagination, not only its first page.
            rag.index_seed()
            self.assertTrue(rag.corpus_status()["seed_ready"])
            upload_id = str(uuid5(NAMESPACE_URL, "offline-upload"))
            upload = Document(page_content="An uploaded fixture must survive seed synchronization.", metadata={"source": "uploads/kept.txt", "chunk": 0, "kind": "upload"})
            rag.store(db).add_documents([upload], ids=[upload_id])
            upload_before = deepcopy(db.retrieve(rag.COLLECTION, [upload_id])[0].payload)
            tracked = Mock(wraps=rag.store(db))
            with patch.object(rag, "store", return_value=tracked):
                self.assertTrue(rag.index_seed()["unchanged"])
                tracked.add_documents.assert_not_called()
                tracked.delete.assert_not_called()
            updated, ids = [], []
            removed_source = "emails/archive-capacity.md"
            for index, (document, chunk_id) in enumerate(zip(original, original_ids)):
                if document.metadata["source"] == removed_source:
                    continue
                if index == 0:
                    document = Document(page_content=document.page_content + " Offline change fixture.", metadata=dict(document.metadata))
                    chunk_id = str(uuid5(NAMESPACE_URL, "offline-updated-chunk"))
                updated.append(document)
                ids.append(chunk_id)
            updated.append(Document(page_content="A new offline seed fixture.", metadata={"source": "fixture/new.md", "document_id": "new", "chunk": 0, "kind": "seed"}))
            ids.append(str(uuid5(NAMESPACE_URL, "offline-new-chunk")))
            with patch.object(rag, "seed_chunks", return_value=(updated, ids)), patch.object(rag, "store", return_value=tracked):
                result = rag.index_seed()
                self.assertEqual(result["embedded_now"], 2)
                self.assertEqual(rag.indexed_seed_ids(db), set(ids))
                self.assertTrue(rag.corpus_status()["seed_ready"])
                self.assertTrue(rag.index_seed()["unchanged"])
            self.assertFalse(rag.corpus_status()["seed_ready"])
            self.assertEqual(db.retrieve(rag.COLLECTION, [upload_id])[0].payload, upload_before)
            self.assertNotIn(upload_id, tracked.delete.call_args.kwargs["ids"])
            self.assertEqual(set(tracked.add_documents.call_args.kwargs["ids"]), set(ids) - set(original_ids))

    def test_neo4j_writer_merges_idempotently_and_prunes_only_obsolete_managed_records(self):
        # A recording transaction checks MERGE identities and prune parameters; real Cypher stays opt-in.
        class Transaction:
            def __init__(self):
                self.nodes = {"foreign": {"id": "foreign", "dataset": "other"}, "obsolete": {"id": "obsolete", "dataset": graph_seed.DATASET}}
                self.edges = {"foreign-edge": {"id": "foreign-edge", "dataset": "other"}, "obsolete-edge": {"id": "obsolete-edge", "dataset": graph_seed.DATASET}}

            def run(self, query, **parameters):
                if "MERGE (n:" in query:
                    for row in parameters["rows"]:
                        self.nodes[row["id"]] = deepcopy(row["properties"])
                elif "MERGE (a)-[r:" in query:
                    for row in parameters["rows"]:
                        assert row["start"] in self.nodes and row["end"] in self.nodes
                        self.edges[row["id"]] = deepcopy(row["properties"])
                else:
                    records = self.edges if "DELETE r" in query else self.nodes
                    obsolete = []
                    for key, value in records.items():
                        if value["dataset"] == parameters["dataset"] and key not in parameters["ids"]:
                            obsolete.append(key)
                    for key in obsolete:
                        del records[key]
                result = Mock()
                result.consume.return_value.counters.nodes_created = 0
                result.consume.return_value.counters.relationships_created = 0
                return result

        with patch.object(rag, "SEED_DIR", ROOT / "data/seed"):
            nodes, edges = graph_seed.seed_graph()
        tx = Transaction()
        graph_seed.write_seed(tx, nodes, edges)
        first = deepcopy((tx.nodes, tx.edges))
        graph_seed.write_seed(tx, nodes, edges)
        self.assertEqual((tx.nodes, tx.edges), first)
        self.assertEqual(len(tx.nodes), len(nodes) + 1)
        self.assertEqual(len(tx.edges), len(edges) + 1)
        target = nodes[0]["id"]
        tx.nodes[target]["obsolete_property"] = True
        graph_seed.write_seed(tx, nodes, edges)
        self.assertNotIn("obsolete_property", tx.nodes[target])
        self.assertIn("foreign", tx.nodes)
        self.assertIn("foreign-edge", tx.edges)


class EvaluationModeTests(unittest.TestCase):
    def test_three_modes_are_disjoint_seed_only_and_include_consistent_corpus_metadata(self):
        with TestClient(main.app) as client, ExitStack() as stack:
            stack.enter_context(patch.object(main, "load_questions", return_value=QUESTIONS))
            stack.enter_context(patch.object(evaluation, "corpus_status", return_value={"seed_ready": True}))
            stack.enter_context(patch.object(evaluation, "graph_status", return_value={"ready": True}))
            stack.enter_context(patch.object(evaluation, "seed_manifest", return_value={"documents": 34, "chunks": 158, "top_k": 4, "fingerprint": "offline"}))
            handlers = {}
            for name in ("answer", "answer_multi_step", "graph_answer"):
                handlers[name] = stack.enter_context(patch.object(evaluation, name, return_value={"answer": "Offline answer fixture", "sources": [], "calls": {"llm": 1, "vector_searches": 0, "graph_queries": 0}, "status": "missing"}))
            for mode, handler in (("standard", "answer"), ("multi-step", "answer_multi_step"), ("graph", "graph_answer")):
                for response in handlers.values():
                    response.reset_mock()
                response = client.post("/api/evaluate", json={"system": mode, "top_k": 12, "seed_only": False})
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()
                self.assertEqual(result["system"], mode)
                self.assertEqual((result["corpus"]["chunks"], result["corpus"]["top_k"]), (158, 4))
                self.assertTrue(result["completed_at"])
                self.assertEqual(result["summary"]["incomplete"], 12)
                for name, respond in handlers.items():
                    self.assertEqual(respond.call_count, 12 if name == handler else 0)
                for question, invocation in zip(QUESTIONS, handlers[handler].call_args_list):
                    self.assertEqual(invocation.args, (question["question"], 4))
                    self.assertEqual(invocation.kwargs, {"seed_only": True} if mode == "standard" else {})

    def test_evaluation_refuses_unsynchronized_seed_data_before_model_calls(self):
        with TestClient(main.app) as client, patch.object(main, "load_questions", return_value=QUESTIONS), patch.object(evaluation, "corpus_status", return_value={"seed_ready": False}), patch.object(evaluation, "graph_status", return_value={"ready": False}), patch.object(evaluation, "answer") as standard, patch.object(evaluation, "answer_multi_step") as multi, patch.object(evaluation, "graph_answer") as graphs:
            for mode in ("standard", "multi-step", "graph"):
                self.assertEqual(client.post("/api/evaluate", json={"system": mode}).status_code, 409)
            standard.assert_not_called()
            multi.assert_not_called()
            graphs.assert_not_called()

    def test_changed_corpus_during_evaluation_is_not_exported_as_a_consistent_run(self):
        first = {"documents": 34, "chunks": 158, "top_k": 4, "fingerprint": "before"}
        second = dict(first, fingerprint="after")
        with TestClient(main.app) as client, patch.object(main, "load_questions", return_value=QUESTIONS[:1]), patch.object(evaluation, "corpus_status", return_value={"seed_ready": True}), patch.object(evaluation, "seed_manifest", side_effect=[first, second]), patch.object(evaluation, "answer", return_value={"answer": "Offline answer", "sources": []}):
            response = client.post("/api/evaluate", json={"system": "standard"})
        self.assertEqual(response.status_code, 409)
        self.assertIn("changed during evaluation", response.json()["detail"])

    def test_multistep_evaluation_reuses_chat_planning_retrieval_extraction_and_answering(self):
        document = Document(page_content="Nóra Varga leads Project Atlas.", metadata={"source": "projects/atlas.md", "chunk": 0})
        model = Mock()
        def structured(schema, **kwargs):
            value = {"steps": [{"question": "Who leads Atlas?", "uses_previous": False}]}
            if schema is chat.GroundedFact:
                value = {"value": "Nóra Varga", "reference": "projects/atlas.md#0", "quote": document.page_content}
            return RunnableLambda(lambda inputs: value)
        model.with_structured_output.side_effect = structured
        retriever = Mock(ainvoke=AsyncMock(return_value=[document]))
        async def evaluate_in_worker():
            return await anyio.to_thread.run_sync(chat.answer_multi_step, "Who leads Atlas?", 4)
        with patch.object(chat, "client", return_value=Mock()), patch.object(chat, "make_retriever", return_value=retriever) as make, patch.object(chat, "chat_model", return_value=model), patch.object(chat, "multi_step_documents", wraps=chat.multi_step_documents) as shared, patch.object(chat, "answer_chain", return_value=Mock(ainvoke=AsyncMock(return_value="Offline grounded answer"))):
            result = anyio.run(evaluate_in_worker)
        shared.assert_awaited_once()
        self.assertEqual(make.call_args.args[1:], (4, True))
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["calls"], {"llm": 3, "vector_searches": 1, "graph_queries": 0})
        self.assertEqual(result["sources"][0]["reference"], "projects/atlas.md#0")

    def test_missing_evidence_and_errors_remain_distinct_in_metrics(self):
        replies = [
            {"answer": "Unsupported fixture", "sources": [], "status": "unsupported", "note": "Outside reviewed operations.", "calls": {"llm": 1, "vector_searches": 0, "graph_queries": 0}},
            RuntimeError("private details"),
        ]
        result = run_evaluation(QUESTIONS[:2], Mock(side_effect=replies))
        self.assertEqual(result["summary"]["successful"], 1)
        self.assertEqual(result["summary"]["incomplete"], 1)
        self.assertEqual(result["summary"]["average_source_coverage"], 0)
        self.assertEqual(result["results"][0]["status"], "unsupported")
        self.assertEqual(result["results"][1]["status"], "error")
        self.assertIsNone(result["results"][1]["calls"])
        self.assertIsNone(result["results"][1]["source_coverage"])
        self.assertNotIn("private details", str(result))


if __name__ == "__main__":
    unittest.main()
