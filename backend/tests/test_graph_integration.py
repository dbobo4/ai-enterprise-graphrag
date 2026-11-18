"""Opt-in only: TEST_NEO4J_URI and TEST_NEO4J_DISPOSABLE=yes must identify an empty throwaway database."""

import json
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from uuid import NAMESPACE_URL, uuid5

from langchain_core.documents import Document

from app import graph, graph_seed, rag
from app.config import Settings

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(os.getenv("TEST_NEO4J_URI") and os.getenv("TEST_NEO4J_DISPOSABLE") == "yes", "NOT RUN: requires an explicitly disposable empty Neo4j")
class Neo4jIntegrationTests(unittest.TestCase):
    def test_real_sync_idempotence_document_graph_queries_and_evaluation_sources(self):
        settings = Settings(neo4j_uri=os.environ["TEST_NEO4J_URI"], neo4j_username="neo4j", neo4j_database="neo4j",
                            neo4j_password=os.getenv("TEST_NEO4J_PASSWORD", "enterprise-demo-password"))
        with patch.object(graph, "get_settings", return_value=settings), patch.object(rag, "SEED_DIR", ROOT / "data/seed"):
            with graph.graph_driver() as driver, graph.graph_session(driver) as session:
                count = session.run("MATCH (n) RETURN count(n) AS count").single()["count"]
                self.assertEqual(count, 0, "Refusing to test a nonempty database; use a disposable container without volumes.")
                nodes, edges = graph_seed.seed_graph()
                original, original_ids = rag.seed_chunks()
                document_count = len(list(rag.SEED_DIR.rglob("*.md")))
                first = graph_seed.sync_seed()
                before = session.run("MATCH (n) RETURN n.id AS id, properties(n) AS properties ORDER BY id").data()
                edges_before = session.run("MATCH (a)-[r]->(b) RETURN a.id AS start, b.id AS end, type(r) AS kind, properties(r) AS properties ORDER BY start, kind, end").data()
                self.assertEqual(graph_seed.sync_seed(), first)
                self.assertEqual(session.run("MATCH (n) RETURN n.id AS id, properties(n) AS properties ORDER BY id").data(), before)
                self.assertEqual(session.run("MATCH (a)-[r]->(b) RETURN a.id AS start, b.id AS end, type(r) AS kind, properties(r) AS properties ORDER BY start, kind, end").data(), edges_before)
                self.assertEqual(first, {"entities": len({item[0] for item in graph_seed.NODES}), "documents": document_count, "chunks": len(original), "relationships": len(edges)})
                self.assertTrue(graph.graph_status()["ready"])

                text = (ROOT / "backend/graph.cypher").read_text(encoding="utf-8")
                lines = []
                for line in text.splitlines():
                    if not line.lstrip().startswith("//"):
                        lines.append(line)
                statements = []
                for statement in "\n".join(lines).split(";"):
                    if statement.strip():
                        statements.append(statement.strip())
                self.assertEqual(len(statements), 8)
                results = []
                for statement in statements:
                    results.append(session.run(statement).data())
                self.assertEqual(results[0], [{"documents": document_count, "chunks": len(original)}])
                chunk_counts = {}
                for document in original:
                    source = document.metadata["source"]
                    chunk_counts[source] = chunk_counts.get(source, 0) + 1
                self.assertEqual(results[1][0]["chunks"], max(chunk_counts.values()))
                self.assertEqual(len(results[2]), list(chunk_counts.values()).count(min(chunk_counts.values())))
                self.assertEqual(results[3], [])
                self.assertEqual(results[4][0]["leader"], "Tamás Fekete")
                self.assertEqual(results[4][0]["department"], "HR")
                self.assertEqual(len(results[4][0]["sources"]), 3)
                self.assertEqual(len(results[5]), sum(node[1] == "Vendor" for node in graph_seed.NODES))
                for row in results[5]:
                    self.assertGreaterEqual(row["projects"], 1)
                self.assertEqual(len(results[6]), len({item[:3] for item in graph_seed.RELATIONSHIPS}))
                self.assertEqual({row["source"] for row in results[7]}, {"incidents/atlas.md", "vendors/novacloud.md", "vendors/safedesk.md"})

                plans = [
                    ("project_leader", "project:atlas-archive"), ("entity", "policy:access"), ("entity", "incident:bridge"),
                    ("unsupported", None), ("vendor_department", "vendor:clearid"), ("vendor_leader", "vendor:dataloom"),
                    ("incident_vendor", "incident:atlas"), ("leader_department", "project:atlas-archive"),
                    ("projects", None), ("suppliers", None), ("incidents", None), ("policies", None),
                ]
                questions = json.loads((ROOT / "evaluation/questions.json").read_text(encoding="utf-8"))
                for (operation, entity_id), question in zip(plans, questions):
                    with self.subTest(question=question["id"]):
                        context, sources, missing = graph.graph_context(graph.CypherPlan(operation=operation, entity_id=entity_id))
                        if operation == "unsupported":
                            self.assertEqual((context, sources, missing), ("", [], graph.UNSUPPORTED))
                            continue
                        self.assertIsNone(missing)
                        self.assertTrue(context)
                        self.assertEqual({source["source"] for source in sources}, set(question["required_sources"]))

                fixture, fixture_ids = [], []
                for index, content in enumerate(rag.text_splitter().split_text("Minimal multi chunk fixture. " * 60)):
                    fixture.append(Document(page_content=content, metadata={"source": "test/sequence.md", "document_id": "sequence", "chunk": index}))
                    fixture_ids.append(str(uuid5(NAMESPACE_URL, f"test:sequence:{index}:{content}")))
                self.assertGreater(len(fixture), 1)
                with patch.object(graph_seed, "seed_chunks", return_value=(original + fixture, original_ids + fixture_ids)):
                    graph_seed.sync_seed()
                    graph_seed.sync_seed()
                sequence = session.run("MATCH (a:Chunk)-[r:NEXT_CHUNK]->(b:Chunk) WHERE a.source = 'test/sequence.md' RETURN a.chunk AS start, b.chunk AS end ORDER BY start").data()
                expected = []
                for index in range(len(fixture) - 1):
                    expected.append({"start": index, "end": index + 1})
                self.assertEqual(sequence, expected)
                # Reverting the fixture removes only obsolete records from this managed dataset.
                self.assertEqual(graph_seed.sync_seed(), first)
                self.assertEqual(session.run("MATCH (n) WHERE n.source = 'test/sequence.md' RETURN count(n) AS count").single()["count"], 0)

                uploaded = []
                for index, document in enumerate(fixture):
                    metadata = {"source": "uploads/fixture/sequence.md", "document_id": "fixture", "filename": "sequence.md",
                                "chunk": index, "kind": "upload", "page": index}
                    uploaded.append(Document(page_content=document.page_content, metadata=metadata))
                graph_seed.sync_upload(uploaded, fixture_ids)
                with ThreadPoolExecutor(max_workers=2) as workers:
                    first_write = workers.submit(graph_seed.sync_upload, uploaded, fixture_ids)
                    second_write = workers.submit(graph_seed.sync_upload, uploaded, fixture_ids)
                    self.assertFalse(first_write.result(timeout=15))
                    self.assertFalse(second_write.result(timeout=15))
                self.assertEqual(graph_seed.sync_seed(), first)
                record = session.run(
                    "MATCH (d:Document {dataset: $dataset})-[:CONTAINS]->(c:Chunk)-[r:NEXT_CHUNK]->(:Chunk) "
                    "RETURN count(DISTINCT d) AS documents, count(r) AS links",
                    dataset=graph_seed.UPLOAD_DATASET,
                ).single()
                self.assertEqual((record["documents"], record["links"]), (1, len(uploaded) - 1))
                _, sources, missing = graph.retrieve_upload("multi chunk", "sequence.md", 4)
                self.assertIsNone(missing)
                self.assertTrue(sources)
                self.assertTrue(all(source["source"] == "uploads/fixture/sequence.md" for source in sources))
                self.assertTrue(graph.graph_status()["uploads_ready"])


if __name__ == "__main__":
    unittest.main()
