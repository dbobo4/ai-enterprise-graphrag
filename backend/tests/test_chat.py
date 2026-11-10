import asyncio
import json
import unittest
import unicodedata
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import AsyncMock, Mock, call, patch

from fastapi.testclient import TestClient
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.runnables import RunnableLambda
from pydantic import ValidationError
from qdrant_client import QdrantClient, models

from app import chat, main, rag

VENDOR = Document(page_content="ClearID provides verification services for Project Bridge.", metadata={"source": "vendors/clearid.md", "chunk": 0})
PROJECT = Document(page_content="Project Bridge is led by Tamás Fekete.", metadata={"source": "projects/bridge.md", "chunk": 0})
PLAN = {"steps": [{"question": "Which project uses ClearID?", "uses_previous": False}, {"question": "Who leads {previous_answer}?", "uses_previous": True}]}
PROJECT_FACT = {"value": "Project Bridge", "reference": "vendors/clearid.md#0", "quote": VENDOR.page_content}
LEADER_FACT = {"value": "Tamás Fekete", "reference": "projects/bridge.md#0", "quote": PROJECT.page_content}


class StreamingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.db = Mock()
        self.retriever = Mock(ainvoke=AsyncMock(return_value=[VENDOR]))
        self.stack.enter_context(patch.object(chat, "require_key"))
        self.stack.enter_context(patch.object(chat, "client", return_value=self.db))
        self.make_retriever = self.stack.enter_context(patch.object(chat, "make_retriever", return_value=self.retriever))
        self.closed = False
        async def tokens(inputs):
            try:
                yield "Tamás "
                yield "Fekete [Source: projects/bridge.md#0]"
            finally:
                self.closed = True
        self.chain = Mock(astream=Mock(side_effect=tokens))
        self.answer_chain = self.stack.enter_context(patch.object(chat, "answer_chain", return_value=self.chain))

    def use_plan(self, plan=PLAN, facts=None):
        answers = iter(facts if facts is not None else [PROJECT_FACT, LEADER_FACT])
        model = Mock()
        def structured(schema, **kwargs):
            if schema is chat.QueryPlan:
                return RunnableLambda(lambda inputs: plan)
            return RunnableLambda(lambda inputs: next(answers))
        model.with_structured_output.side_effect = structured
        return self.stack.enter_context(patch.object(chat, "chat_model", return_value=model))

    async def collect(self, mode="standard"):
        events = []
        async for event in chat.stream_answer("Who leads the ClearID project?", 4, mode):
            events.append(event)
        return events

    async def test_standard_stream_has_sources_tokens_done_and_unchanged_retrieval(self):
        with patch.object(chat, "multi_step_documents") as multi:
            events = await self.collect()
        self.assertEqual([event["type"] for event in events], ["sources", "token", "token", "done"])
        self.assertEqual(events[0]["sources"][0]["reference"], "vendors/clearid.md#0")
        self.assertEqual(events[1]["text"] + events[2]["text"], "Tamás Fekete [Source: projects/bridge.md#0]")
        self.make_retriever.assert_called_once_with(self.db, 4)
        self.retriever.ainvoke.assert_awaited_once_with("Who leads the ClearID project?")
        multi.assert_not_called()
        self.assertTrue(self.closed)
        self.db.close.assert_called_once()

    async def test_multi_step_resolves_entity_and_deduplicates_sources(self):
        self.use_plan()
        self.retriever.ainvoke.side_effect = [[VENDOR, VENDOR], [VENDOR, PROJECT]]
        events = await self.collect("multi-step")
        self.assertEqual(self.retriever.ainvoke.await_args_list, [call("Which project uses ClearID?"), call("Who leads Project Bridge?")])
        self.assertEqual([source["reference"] for source in events[0]["sources"]], ["vendors/clearid.md#0", "projects/bridge.md#0"])
        self.assertEqual(events[-1]["type"], "done")
        inputs = self.chain.astream.call_args.args[0]
        self.assertIn(VENDOR.page_content, inputs["context"])
        self.assertIn(PROJECT.page_content, inputs["context"])

    async def test_failed_extraction_retries_once_then_uses_only_verified_value(self):
        fabricated = {**PROJECT_FACT, "value": "Project Atlas"}
        self.use_plan(facts=[fabricated, PROJECT_FACT, LEADER_FACT])
        self.retriever.ainvoke.side_effect = [[VENDOR], [PROJECT]]
        events = await self.collect("multi-step")
        self.assertEqual(events[-1]["type"], "done")
        self.assertEqual(self.retriever.ainvoke.await_args_list, [call("Which project uses ClearID?"), call("Who leads Project Bridge?")])
        self.answer_chain.assert_called_once()

    async def test_two_failed_extractions_stop_without_another_search_or_answer(self):
        invalid = {**PROJECT_FACT, "value": "Project Atlas"}
        self.use_plan(facts=[invalid, invalid])
        calls = {"llm": 0, "vector_searches": 0, "graph_queries": 0}
        documents, complete = await chat.multi_step_documents("ClearID leader?", self.retriever, calls=calls)
        self.assertFalse(complete)
        self.assertEqual(documents, [VENDOR])
        self.assertEqual(calls, {"llm": 3, "vector_searches": 1, "graph_queries": 0})
        self.retriever.ainvoke.assert_awaited_once()
        self.answer_chain.assert_not_called()

    async def test_invalid_structured_extraction_can_recover_on_its_single_retry(self):
        self.use_plan(facts=[{"value": "Bridge"}, PROJECT_FACT, LEADER_FACT])
        self.retriever.ainvoke.side_effect = [[VENDOR], [PROJECT]]
        events = await self.collect("multi-step")
        self.assertEqual(events[-1]["type"], "done")
        self.assertEqual(self.retriever.ainvoke.await_count, 2)

    async def test_absent_structured_extraction_retries_once_and_preserves_unverified_sources(self):
        for facts, complete in (([None, PROJECT_FACT, LEADER_FACT], True), ([None, None], False)):
            with self.subTest(complete=complete):
                self.use_plan(facts=facts)
                self.retriever.ainvoke.side_effect = [[VENDOR], [PROJECT]]
                calls = {"llm": 0, "vector_searches": 0, "graph_queries": 0}
                documents, actual = await chat.multi_step_documents("Who leads the ClearID project?", self.retriever, calls=calls)
                self.assertEqual(actual, complete)
                self.assertEqual(documents, [VENDOR, PROJECT] if complete else [VENDOR])
                self.assertEqual(calls["llm"], 4 if complete else 3)
                self.assertEqual(calls["vector_searches"], 2 if complete else 1)
        self.answer_chain.assert_not_called()

    async def test_maximum_steps_are_bounded_and_duplicate_chunks_are_not_repeated(self):
        steps = []
        facts = []
        for index in range(chat.MAX_STEPS):
            steps.append({"question": f"ClearID question {index}?", "uses_previous": False})
            facts.append(PROJECT_FACT)
        factory = self.use_plan({"steps": steps}, facts)
        events = await self.collect("multi-step")
        self.assertEqual(self.retriever.ainvoke.await_count, chat.MAX_STEPS)
        self.assertEqual(len(events[0]["sources"]), 1)
        self.assertEqual(factory.call_args_list, [call(max_tokens=1200), call(max_tokens=700)])

    async def test_excess_steps_and_invalid_dependencies_fail_before_search(self):
        invalid = [
            {"steps": [{"question": "ClearID project?", "uses_previous": False}] * (chat.MAX_STEPS + 1)},
            {"steps": [{"question": "Who leads {previous_answer}?", "uses_previous": True}]},
            {"steps": [{"question": "Who leads {unknown}?", "uses_previous": False}]},
        ]
        for plan in invalid:
            with self.subTest(plan=plan):
                self.use_plan(plan)
                with self.assertRaises(ValidationError):
                    await self.collect("multi-step")
        self.retriever.ainvoke.assert_not_awaited()
        self.answer_chain.assert_not_called()

    async def test_missing_or_fabricated_intermediate_evidence_stops_dependent_search(self):
        invalid = [
            {"value": None, "reference": None, "quote": None},
            {**PROJECT_FACT, "value": "Invented Project"},
            {**PROJECT_FACT, "reference": "missing.md#0"},
            {**PROJECT_FACT, "quote": "ClearID leads Project Bridge."},
        ]
        for fact in invalid:
            with self.subTest(fact=fact):
                self.retriever.ainvoke.reset_mock()
                self.use_plan(facts=[fact, fact])
                events = await self.collect("multi-step")
                self.retriever.ainvoke.assert_awaited_once_with("Which project uses ClearID?")
                self.assertEqual(events[1], {"type": "token", "text": chat.MISSING_EVIDENCE})
                self.assertEqual(len(events[0]["sources"]), 1)
        self.answer_chain.assert_not_called()

    async def test_missing_final_evidence_preserves_sources_without_generating_a_claim(self):
        missing = {"value": None, "reference": None, "quote": None}
        self.use_plan(facts=[PROJECT_FACT, missing, missing])
        self.retriever.ainvoke.side_effect = [[VENDOR], [PROJECT]]
        events = await self.collect("multi-step")
        self.assertEqual(len(events[0]["sources"]), 2)
        self.assertEqual(events[1]["text"], chat.MISSING_EVIDENCE)
        self.answer_chain.assert_not_called()

    async def test_empty_retrieval_does_not_generate_an_answer(self):
        self.retriever.ainvoke.return_value = []
        events = await self.collect()
        self.assertEqual(events[0]["sources"], [])
        self.assertEqual(events[1]["text"], chat.MISSING_EVIDENCE)
        self.assertEqual(events[-1]["type"], "done")
        self.answer_chain.assert_not_called()

    async def test_consumer_close_releases_model_stream_and_database(self):
        stream = chat.stream_answer("ClearID project?", 4, "standard")
        await anext(stream)
        await anext(stream)
        await stream.aclose()
        self.assertTrue(self.closed)
        self.db.close.assert_called_once()

    async def test_cancellation_closes_a_waiting_model_stream(self):
        waiting = asyncio.Event()
        async def tokens(inputs):
            try:
                yield "Partial answer"
                waiting.set()
                await asyncio.Event().wait()
            finally:
                self.closed = True
        self.chain.astream.side_effect = tokens
        stream = chat.stream_answer("ClearID project?", 4, "standard")
        await anext(stream)
        await anext(stream)
        task = asyncio.create_task(anext(stream))
        await asyncio.wait_for(waiting.wait(), timeout=2)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(self.closed)
        self.db.close.assert_called_once()


class StreamApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_disconnect_before_start_does_not_start_rag(self):
        connection = Mock(is_disconnected=AsyncMock(return_value=True))
        with patch.object(main, "stream_answer") as stream:
            response = await main.chat_stream(main.StreamChatRequest(question="ClearID project?"), connection)
            frames = []
            async for frame in response.body_iterator:
                frames.append(frame)
        self.assertEqual(frames, [])
        stream.assert_not_called()

    async def test_disconnect_during_response_closes_the_iterator(self):
        closed = []
        async def events(*args):
            try:
                yield {"type": "sources", "sources": [], "top_k": 4}
                yield {"type": "token", "text": "Partial"}
            finally:
                closed.append(True)
        connection = Mock(is_disconnected=AsyncMock(side_effect=[False, False, True]))
        with patch.object(main, "stream_answer", side_effect=events):
            response = await main.chat_stream(main.StreamChatRequest(question="ClearID project?"), connection)
            frames = []
            async for frame in response.body_iterator:
                frames.append(frame)
        self.assertEqual(len(frames), 1)
        self.assertTrue(closed)

    async def test_sse_preserves_partial_tokens_and_sanitizes_errors(self):
        async def events(*args):
            yield {"type": "sources", "sources": [], "top_k": 4}
            yield {"type": "token", "text": "Tamás\nFekete"}
            raise RuntimeError("private error details")
        connection = Mock(is_disconnected=AsyncMock(return_value=False))
        with patch.object(main, "stream_answer", side_effect=events):
            response = await main.chat_stream(main.StreamChatRequest(question="ClearID project?"), connection)
            messages = []
            async for frame in response.body_iterator:
                messages.append(json.loads(frame.removeprefix("data: ")))
        self.assertEqual([message["type"] for message in messages], ["sources", "token", "error"])
        self.assertEqual(messages[1]["text"], "Tamás\nFekete")
        self.assertNotIn("private error details", str(messages))
        self.assertEqual(response.media_type, "text/event-stream")
        self.assertIn("no-transform", response.headers["cache-control"])

    async def test_http_modes_and_successful_sse_sequence(self):
        async def events(question, k, mode):
            yield {"type": "sources", "sources": [], "top_k": k}
            yield {"type": "token", "text": "Answer"}
            yield {"type": "done"}
        with TestClient(main.app) as client, patch.object(main, "stream_answer", side_effect=events) as stream:
            for mode in ("standard", "multi-step"):
                response = client.post("/api/chat/stream", json={"question": "ClearID project?", "mode": mode})
                self.assertEqual(response.status_code, 200)
                messages = []
                for frame in response.text.strip().split("\n\n"):
                    messages.append(json.loads(frame.removeprefix("data: ")))
                self.assertEqual([message["type"] for message in messages], ["sources", "token", "done"])
                stream.assert_called_with("ClearID project?", 4, mode)
            self.assertEqual(client.post("/api/chat/stream", json={"question": "ClearID project?", "mode": "agent"}).status_code, 422)
            self.assertEqual(stream.call_count, 2)

    async def test_non_streaming_chat_and_evaluation_remain_standard_and_seed_scoped(self):
        answer = {"answer": "Answer", "sources": [], "top_k": 4}
        questions_path = Path(__file__).resolve().parents[2] / "evaluation" / "questions.json"
        with TestClient(main.app) as client, patch.object(main, "answer", return_value=answer) as respond, patch.object(main, "stream_answer") as stream, patch.object(main, "Path", return_value=questions_path), patch.object(main, "corpus_status", return_value={"seed_ready": True}):
            response = client.post("/api/chat", json={"question": "ClearID project?", "mode": "multi-step"})
            self.assertEqual(response.json(), answer)
            respond.assert_called_once_with("ClearID project?", 4)
            respond.reset_mock()
            evaluation = client.post("/api/evaluate", json={"mode": "multi-step", "top_k": 12}).json()
            self.assertEqual(evaluation["summary"]["successful"], 12)
            self.assertEqual(respond.call_count, 12)
            for invocation in respond.call_args_list:
                self.assertEqual(invocation.args[1], 4)
                self.assertEqual(invocation.kwargs, {"seed_only": True})
            stream.assert_not_called()


class StreamRetrievalTests(unittest.IsolatedAsyncioTestCase):
    async def test_both_modes_retrieve_uploads_while_evaluation_retrieval_excludes_them(self):
        db = QdrantClient(":memory:")
        self.addCleanup(db.close)
        embeddings = Mock(spec=Embeddings)
        def embed(texts):
            vectors = []
            for text in texts:
                vectors.append([1.0] + [0.0] * 1535)
            return vectors
        embeddings.embed_documents.side_effect = embed
        embeddings.embed_query.return_value = [1.0] + [0.0] * 1535
        upload = Document(page_content=VENDOR.page_content, metadata={"source": "uploads/notes.txt", "chunk": 0, "kind": "upload"})
        seed = Document(page_content=PROJECT.page_content, metadata={"source": "projects/bridge.md", "chunk": 0, "kind": "seed"})
        model = Mock()
        def structured(schema, **kwargs):
            if schema is chat.QueryPlan:
                return RunnableLambda(lambda inputs: {"steps": [{"question": "Which project uses ClearID?", "uses_previous": False}]})
            return RunnableLambda(lambda inputs: {**PROJECT_FACT, "reference": "uploads/notes.txt#0"})
        model.with_structured_output.side_effect = structured
        with ExitStack() as stack:
            stack.enter_context(patch.object(db, "close"))
            stack.enter_context(patch.object(chat, "client", return_value=db))
            stack.enter_context(patch.object(rag, "client", return_value=db))
            stack.enter_context(patch.object(chat, "require_key"))
            stack.enter_context(patch.object(rag, "require_key"))
            stack.enter_context(patch.object(rag, "OpenAIEmbeddings", return_value=embeddings))
            stack.enter_context(patch.object(rag, "ChatOpenAI", return_value=RunnableLambda(lambda inputs: "Answer")))
            stack.enter_context(patch.object(chat, "chat_model", return_value=model))
            db.create_collection(rag.COLLECTION, vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE))
            rag.store(db).add_documents([upload, seed])
            for mode in ("standard", "multi-step"):
                first = None
                async for event in chat.stream_answer("ClearID project?", 4, mode):
                    if first is None:
                        first = event
                self.assertIn("uploads/notes.txt", [source["source"] for source in first["sources"]])
            baseline = rag.answer("ClearID project?", 4, seed_only=True)
            self.assertEqual([source["source"] for source in baseline["sources"]], ["projects/bridge.md"])
            result = await chat.multi_step_answer("ClearID project?", 4, seed_only=True)
            self.assertEqual([source["source"] for source in result["sources"]], ["projects/bridge.md"])
            self.assertEqual(result["status"], "insufficient")
            self.assertEqual(result["calls"], {"llm": 3, "vector_searches": 1, "graph_queries": 0})


class EvidenceTests(unittest.TestCase):
    def check(self, value, quote, text, reference="fixture.md#0"):
        fact = chat.GroundedFact(value=value, quote=quote, reference=reference)
        document = Document(page_content=text, metadata={"source": "fixture.md", "chunk": 0})
        return chat.supported_value(fact, [document])

    def test_case_canonical_unicode_whitespace_and_simple_formatting_are_harmless(self):
        name = unicodedata.normalize("NFD", "Nóra Varga")
        self.assertEqual(self.check(name, "NÓRA\u00a0VARGA leads Project Atlas.", "**Nóra Varga** leads Project Atlas."), name)
        for quote, text in [
            ("Nóra Varga leads Project Atlas.", "<strong>Nóra Varga</strong> leads `Project Atlas`."),
            ("Nóra Varga leads Project Atlas.", "__Nóra Varga__ leads _Project Atlas_."),
            ("The launch is 2026-11-15.", "The launch is 2026\u201111\u201115."),
        ]:
            value = "2026-11-15" if "launch" in quote else "Nóra Varga"
            with self.subTest(text=text):
                self.assertEqual(self.check(value, quote, text), value)

    def test_distinct_people_accents_tokens_and_numeric_values_never_match_loosely(self):
        cases = [
            ("Nóra Varga", "Nóra Váradi leads Project Atlas.", "Nóra Váradi leads Project Atlas."),
            ("Nora Varga", "Nóra Varga leads Project Atlas.", "Nóra Varga leads Project Atlas."),
            ("Nóra Varga", "Nóra Vargai leads Project Atlas.", "Nóra Vargai leads Project Atlas."),
            ("Nóra Varga", "Nóra Varga-Szabó leads Project Atlas.", "Nóra Varga-Szabó leads Project Atlas."),
            ("30", "The validity is 130 days.", "The validity is 130 days."),
            ("30", "The value is 30.5.", "The value is 30.5."),
            ("30", "The value is -30.", "The value is -30."),
            ("2026", "The launch is 2026-11-15.", "The launch is 2026-11-15."),
            ("30", "The value is 30%.", "The value is 30%."),
            ("x2", "The formula is x².", "The formula is x²."),
            ("Nóra Varga", "Nóra Varga leads Project Atlas.", "Nóra Varga advises Project Atlas."),
        ]
        for value, quote, text in cases:
            with self.subTest(value=value, quote=quote):
                self.assertIsNone(self.check(value, quote, text))
        self.assertIsNone(self.check("Nóra Varga", "Nóra Varga leads.", "Nóra Varga leads.", reference="other.md#0"))
        self.assertIsNone(self.check("{previous_answer}", "{previous_answer}", "{previous_answer}"))


if __name__ == "__main__":
    unittest.main()
