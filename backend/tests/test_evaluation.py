import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from fastapi.testclient import TestClient

from app.evaluation import run_evaluation

QUESTIONS_PATH = Path(__file__).resolve().parents[2] / "evaluation" / "questions.json"
QUESTIONS = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
SOURCE = {"source": "projects/atlas.md", "chunk": 0, "reference": "projects/atlas.md#0", "snippet": "Atlas project"}
ANSWER = {"answer": "Generated answer", "sources": [SOURCE], "top_k": 4}


class EvaluationTests(unittest.TestCase):
    def test_coverage_counts_unique_expected_documents(self):
        question = dict(QUESTIONS[5])
        response = {"answer": "Generated answer", "sources": [SOURCE, SOURCE, {"source": "unrelated.md"}]}
        result = run_evaluation([question], Mock(return_value=response))["results"][0]
        self.assertEqual(result["source_coverage"], 0.5)
        self.assertEqual(result["sources"], response["sources"])

    def test_no_matching_sources_gives_zero_coverage(self):
        for sources in ([], [{"source": "unrelated.md"}]):
            with self.subTest(sources=sources):
                response = {"answer": "Generated answer", "sources": sources}
                result = run_evaluation([QUESTIONS[0]], Mock(return_value=response))
                self.assertEqual(result["results"][0]["source_coverage"], 0.0)

    def test_summary_and_categories_use_successful_questions(self):
        questions = [QUESTIONS[0], QUESTIONS[1], QUESTIONS[5], QUESTIONS[8]]
        complete = {"answer": "Generated answer", "sources": [SOURCE, {"source": "people/roles.md"}]}
        answer = Mock(side_effect=[ANSWER, ANSWER, complete, RuntimeError("Unavailable")])
        with patch("app.evaluation.perf_counter", side_effect=[0, 1, 10, 13, 20, 25, 30, 37]):
            result = run_evaluation(questions, answer)
        summary = result["summary"]
        self.assertEqual((summary["successful"], summary["total"]), (3, 4))
        self.assertAlmostEqual(summary["average_source_coverage"], 2 / 3)
        self.assertEqual(summary["average_response_time_seconds"], 3)
        local = result["categories"]["local"]
        self.assertEqual((local["successful"], local["total"]), (2, 2))
        self.assertEqual(local["average_source_coverage"], 0.5)
        self.assertEqual(local["average_response_time_seconds"], 2)
        multi_hop = result["categories"]["multi-hop"]
        self.assertEqual((multi_hop["successful"], multi_hop["total"]), (1, 1))
        self.assertEqual(multi_hop["average_source_coverage"], 1)
        self.assertEqual(multi_hop["average_response_time_seconds"], 5)
        global_summary = result["categories"]["global"]
        self.assertEqual((global_summary["successful"], global_summary["total"]), (0, 1))
        self.assertIsNone(global_summary["average_source_coverage"])
        self.assertIsNone(global_summary["average_response_time_seconds"])
        self.assertEqual(result["results"][3]["response_time_seconds"], 7)

    def test_question_failure_preserves_results_and_is_not_retried(self):
        answer = Mock(side_effect=[ANSWER, RuntimeError("private error details"), ANSWER])
        result = run_evaluation(QUESTIONS[:3], answer)
        self.assertEqual(len(result["results"]), 3)
        self.assertEqual(result["results"][0]["answer"], ANSWER["answer"])
        self.assertIsNotNone(result["results"][1]["error"])
        self.assertIsNone(result["results"][1]["answer"])
        self.assertIsNone(result["results"][1]["source_coverage"])
        self.assertEqual(result["results"][2]["answer"], ANSWER["answer"])
        self.assertEqual(result["summary"]["successful"], 2)
        self.assertNotIn("private error details", str(result))
        expected_calls = []
        for question in QUESTIONS[:3]:
            expected_calls.append(call(question["question"], 4))
        self.assertEqual(answer.call_args_list, expected_calls)

    def test_empty_and_failed_runs_have_no_averages(self):
        for questions in ([], QUESTIONS[:2]):
            with self.subTest(count=len(questions)):
                answer = Mock(side_effect=RuntimeError("Unavailable"))
                result = run_evaluation(questions, answer)
                self.assertEqual(result["summary"]["total"], len(questions))
                self.assertEqual(result["summary"]["successful"], 0)
                self.assertIsNone(result["summary"]["average_source_coverage"])
                self.assertIsNone(result["summary"]["average_response_time_seconds"])


class EvaluationApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Isolate the RAG boundary before importing the API: no model, embedding or database clients.
        spec = importlib.util.spec_from_file_location("evaluation_api_test", Path(__file__).parents[1] / "app" / "main.py")
        cls.api = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"app.rag": Mock(), "app.chat": Mock(), "app.uploads": Mock(UploadError=ValueError), spec.name: cls.api}):
            spec.loader.exec_module(cls.api)

    def setUp(self):
        self.client = TestClient(self.api.app)
        self.addCleanup(self.client.close)

    def test_post_returns_all_twelve_results_and_metrics(self):
        with patch.object(self.api, "Path", return_value=QUESTIONS_PATH), patch.object(self.api, "answer", return_value=ANSWER) as answer:
            response = self.client.post("/api/evaluate")
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(len(result["results"]), 12)
        self.assertEqual(answer.call_count, 12)
        self.assertEqual((result["summary"]["successful"], result["summary"]["total"]), (12, 12))
        for category in ("local", "multi-hop", "global"):
            summary = result["categories"][category]
            self.assertEqual((summary["successful"], summary["total"]), (4, 4))
        for question, item, invocation in zip(QUESTIONS, result["results"], answer.call_args_list):
            for field in ("id", "type", "question", "expected_answer", "required_sources"):
                self.assertEqual(item[field], question[field])
            self.assertEqual(item["answer"], ANSWER["answer"])
            self.assertEqual(item["sources"], ANSWER["sources"])
            self.assertIsNone(item["error"])
            self.assertGreaterEqual(item["source_coverage"], 0)
            self.assertLessEqual(item["source_coverage"], 1)
            self.assertGreaterEqual(item["response_time_seconds"], 0)
            self.assertEqual(invocation, call(question["question"], 4, seed_only=True))

    def test_api_keeps_successes_when_one_question_fails(self):
        answers = [ANSWER, RuntimeError("private error details")] + [ANSWER] * 10
        with patch.object(self.api, "Path", return_value=QUESTIONS_PATH), patch.object(self.api, "answer", side_effect=answers) as answer:
            response = self.client.post("/api/evaluate")
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(len(result["results"]), 12)
        self.assertEqual(result["summary"]["successful"], 11)
        self.assertEqual(result["categories"]["local"]["successful"], 3)
        self.assertIsNotNone(result["results"][1]["error"])
        self.assertEqual(result["results"][-1]["answer"], ANSWER["answer"])
        self.assertEqual(answer.call_count, 12)
        self.assertNotIn("private error details", response.text)

    def test_loading_questions_and_get_requests_do_not_run_evaluation(self):
        with patch.object(self.api, "Path", return_value=QUESTIONS_PATH), patch.object(self.api, "answer") as answer:
            self.assertEqual(self.client.get("/api/questions").json(), QUESTIONS)
            self.assertEqual(self.client.get("/api/health").status_code, 200)
            self.assertEqual(self.client.get("/api/evaluate").status_code, 405)
            answer.assert_not_called()

    def test_unavailable_question_file_returns_503_without_rag_calls(self):
        with patch.object(self.api, "questions", side_effect=FileNotFoundError), patch.object(self.api, "answer") as answer:
            response = self.client.post("/api/evaluate")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Test questions are unavailable."})
        answer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
