"""Opt-in only: TEST_NEO4J_URI and TEST_NEO4J_DISPOSABLE=yes must identify an empty throwaway database."""

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import NAMESPACE_URL, uuid5

from langchain_core.documents import Document

from app import graph, graph_seed, rag

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(os.getenv("TEST_NEO4J_URI") and os.getenv("TEST_NEO4J_DISPOSABLE") == "yes", "NOT RUN: requires an explicitly disposable empty Neo4j")
class Neo4jIntegrationTests(unittest.TestCase):
    def test_real_sync_idempotence_document_graph_queries_and_evaluation_sources(self):
        settings = {
            "NEO4J_URI": os.environ["TEST_NEO4J_URI"], "NEO4J_USERNAME": "neo4j", "NEO4J_DATABASE": "neo4j",
            "NEO4J_PASSWORD": os.getenv("TEST_NEO4J_PASSWORD", "enterprise-demo-password"),
        }
        with patch.dict(os.environ, settings), patch.object(rag, "SEED_DIR", ROOT / "data/seed"):
            with graph.graph_driver() as driver, graph.graph_session(driver) as session:
                count = session.run("MATCH (n) RETURN count(n) AS count").single()["count"]
                self.assertEqual(count, 0, "Refusing to test a nonempty database; use a disposable container without volumes.")
                first = graph_seed.sync_seed()
                before = session.run("MATCH (n) RETURN n.id AS id, properties(n) AS properties ORDER BY id").data()
                edges_before = session.run("MATCH (a)-[r]->(b) RETURN a.id AS start, b.id AS end, type(r) AS kind, properties(r) AS properties ORDER BY start, kind, end").data()
                self.assertEqual(graph_seed.sync_seed(), first)
                self.assertEqual(session.run("MATCH (n) RETURN n.id AS id, properties(n) AS properties ORDER BY id").data(), before)
                self.assertEqual(session.run("MATCH (a)-[r]->(b) RETURN a.id AS start, b.id AS end, type(r) AS kind, properties(r) AS properties ORDER BY start, kind, end").data(), edges_before)
                self.assertEqual(first, {"entities": 19, "documents": 14, "chunks": 14, "relationships": 52})
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
                self.assertEqual(results[0], [{"documents": 14, "chunks": 14}])
                self.assertEqual(results[1][0]["chunks"], 1)
                self.assertEqual(len(results[2]), 14)
                self.assertEqual(results[3], [])
                self.assertEqual(results[4][0]["leader"], "Tamás Fekete")
                self.assertEqual(results[4][0]["department"], "HR")
                self.assertEqual(len(results[4][0]["sources"]), 3)
                self.assertEqual(len(results[5]), 3)
                for row in results[5]:
                    self.assertEqual(row["projects"], 1)
                self.assertEqual(len(results[6]), 19)
                self.assertEqual({row["source"] for row in results[7]}, {"incidents/atlas.md", "vendors/novacloud.md"})

                plans = [
                    ("project_leader", "project:atlas"), ("entity", "policy:access"), ("entity", "incident:bridge"),
                    ("entity", "vendor:greenwire"), ("vendor_leader", "vendor:clearid"), ("leader_department", "project:atlas"),
                    ("incident_vendor", "incident:atlas"), ("vendor_leader", "vendor:greenwire"),
                    ("projects", None), ("leaders", None), ("incidents", None), ("suppliers", None),
                ]
                questions = json.loads((ROOT / "evaluation/questions.json").read_text(encoding="utf-8"))
                for (operation, entity_id), question in zip(plans, questions):
                    with self.subTest(question=question["id"]):
                        context, sources, missing = graph.graph_context(graph.CypherPlan(operation=operation, entity_id=entity_id))
                        self.assertIsNone(missing)
                        self.assertTrue(context)
                        self.assertEqual({source["source"] for source in sources}, set(question["required_sources"]))

                original, original_ids = rag.seed_chunks()
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


if __name__ == "__main__":
    unittest.main()
