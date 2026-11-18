import logging
import traceback
from collections.abc import Callable
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from time import perf_counter

from anyio import to_thread
from pydantic import TypeAdapter
from typing_extensions import TypedDict

from app.chat import answer_multi_step
from app.contracts import Answer, Calls, EvidenceStatus, SearchMode, SeedManifest, Source
from app.graph import graph_answer, graph_status
from app.rag import answer, corpus_status, seed_manifest

logger = logging.getLogger(__name__)


class Question(TypedDict):
    id: str
    type: str
    question: str
    expected_answer: str
    required_sources: list[str]


class Result(Question):
    answer: str | None
    sources: list[Source]
    source_coverage: float | None
    error: str | None
    status: EvidenceStatus
    note: str | None
    calls: Calls | None
    response_time_seconds: float


class Summary(TypedDict):
    total: int
    successful: int
    average_source_coverage: float | None
    average_response_time_seconds: float | None
    incomplete: int
    calls: Calls | None


class Evaluation(TypedDict):
    results: list[Result]
    summary: Summary
    categories: dict[str, Summary]


class EvaluationRun(Evaluation):
    system: SearchMode
    corpus: SeedManifest
    completed_at: str


class EvaluationUnavailable(RuntimeError):
    pass


class EvaluationConflict(RuntimeError):
    pass


def load_questions(path: Path) -> list[Question]:
    return TypeAdapter(list[Question]).validate_json(path.read_bytes())


def log_failure(question_id: str, system: str, error: Exception) -> None:
    # Record exception types, causes and code locations, never messages, inputs or credentials.
    causes, seen = [], set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        detail = type(error).__name__
        if isinstance(error, RuntimeError) and "event loop is closed" in str(error).casefold():
            detail += " (event_loop_closed)"
        status = getattr(error, "status_code", None)
        if isinstance(status, int):
            detail += f" (HTTP {status})"
        frames = []
        for frame in traceback.extract_tb(error.__traceback__):
            frames.append(f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}")
        causes.append(f"{detail} at {' > '.join(frames[-6:]) or 'unknown'}")
        error = error.__cause__ or (None if error.__suppress_context__ else error.__context__)
    logger.error("Evaluation %s %s failed: %s", system, question_id, " <- ".join(causes))


def summarize(results: list[Result]) -> Summary:
    successful = 0
    coverage = 0.0
    response_time = 0.0
    incomplete = 0
    calls: Calls = {"llm": 0, "vector_searches": 0, "graph_queries": 0}
    measured_calls = 0
    for result in results:
        if result["error"] is None:
            successful += 1
            coverage += result["source_coverage"] or 0.0
            response_time += result["response_time_seconds"]
            if result.get("status", "complete") != "complete":
                incomplete += 1
            work = result["calls"]
            if work is not None:
                measured_calls += 1
                calls["llm"] += work["llm"]
                calls["vector_searches"] += work["vector_searches"]
                calls["graph_queries"] += work["graph_queries"]

    return {
        "total": len(results), "successful": successful,
        "average_source_coverage": coverage / successful if successful else None,
        "average_response_time_seconds": response_time / successful if successful else None,
        "incomplete": incomplete, "calls": calls if measured_calls else None,
    }


def run_evaluation(questions: list[Question], answer_question: Callable[[str, int], Answer], *, system: SearchMode = "standard") -> Evaluation:
    results = []
    for question in questions:
        result: Result = {
            **question,
            "answer": None, "sources": [], "source_coverage": None, "error": None,
            "status": "error", "note": None, "calls": None, "response_time_seconds": 0.0,
        }
        started = perf_counter()
        try:
            response = answer_question(question["question"], 4)
            retrieved = set()
            for source in response["sources"]:
                retrieved.add(source["source"])
            required = set(question["required_sources"])
            coverage = len(required & retrieved) / len(required)
            result["source_coverage"] = coverage
            result["answer"] = response["answer"]
            result["sources"] = response["sources"]
            result["calls"] = response.get("calls")
            result["status"] = response.get("status", "complete")
            result["note"] = response.get("note")
            if result["status"] == "complete" and coverage < 1:
                result["status"] = "partial" if response["sources"] else "missing"
                result["note"] = "Some expected source documents were not retrieved."
        except Exception as exc:
            log_failure(question["id"], system, exc)
            result["error"] = "This question could not be evaluated."
        result["response_time_seconds"] = perf_counter() - started
        results.append(result)

    categories = {}
    for category in ("local", "multi-hop", "global"):
        category_results = []
        for result in results:
            if result["type"] == category:
                category_results.append(result)
        categories[category] = summarize(category_results)

    return {"results": results, "summary": summarize(results), "categories": categories}


async def evaluate_corpus(questions: list[Question], system: SearchMode) -> EvaluationRun:
    return await to_thread.run_sync(evaluate_in_worker, questions, system)


def evaluate_in_worker(questions: list[Question], system: SearchMode) -> EvaluationRun:
    manifest = seed_manifest()
    if system == "graph":
        try:
            ready = graph_status()["ready"]
        except Exception as exc:
            raise EvaluationUnavailable("Graph search is unavailable.") from exc
        respond = graph_answer
    else:
        try:
            ready = corpus_status()["seed_ready"]
        except Exception as exc:
            raise EvaluationUnavailable("Vector search is unavailable.") from exc
        respond = answer_multi_step if system == "multi-step" else partial(answer, seed_only=True)
    if not ready:
        raise EvaluationConflict("Synchronize the built-in knowledge before evaluation.")
    result = run_evaluation(questions, respond, system=system)
    if seed_manifest() != manifest:
        raise EvaluationConflict("Built-in documents changed during evaluation. Run it again after synchronization.")
    return {**result, "system": system, "corpus": manifest, "completed_at": datetime.now(timezone.utc).isoformat()}
