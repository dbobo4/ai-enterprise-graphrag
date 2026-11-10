import logging
import traceback
from collections.abc import Callable
from pathlib import Path
from time import perf_counter

logger = logging.getLogger(__name__)


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


def summarize(results: list[dict]) -> dict:
    successful = 0
    coverage = 0.0
    response_time = 0.0
    incomplete = 0
    calls = {"llm": 0, "vector_searches": 0, "graph_queries": 0}
    measured_calls = 0
    for result in results:
        if result["error"] is None:
            successful += 1
            coverage += result["source_coverage"]
            response_time += result["response_time_seconds"]
            if result.get("status", "complete") != "complete":
                incomplete += 1
            if result.get("calls") is not None:
                measured_calls += 1
                for key in calls:
                    calls[key] += result["calls"][key]

    return {
        "total": len(results), "successful": successful,
        "average_source_coverage": coverage / successful if successful else None,
        "average_response_time_seconds": response_time / successful if successful else None,
        "incomplete": incomplete, "calls": calls if measured_calls else None,
    }


def run_evaluation(questions: list[dict], answer_question: Callable[[str, int], dict], *, system: str = "standard") -> dict:
    results = []
    for question in questions:
        result = {
            "id": question["id"], "type": question["type"], "question": question["question"],
            "expected_answer": question["expected_answer"], "required_sources": question["required_sources"],
            "answer": None, "sources": [], "source_coverage": None, "error": None,
            "status": "error", "note": None, "calls": None,
        }
        started = perf_counter()
        try:
            response = answer_question(question["question"], 4)
            retrieved = set()
            for source in response["sources"]:
                retrieved.add(source["source"])
            required = set(question["required_sources"])
            result["source_coverage"] = len(required & retrieved) / len(required)
            result["answer"] = response["answer"]
            result["sources"] = response["sources"]
            result["calls"] = response.get("calls")
            result["status"] = response.get("status", "complete")
            result["note"] = response.get("note")
            if result["status"] == "complete" and result["source_coverage"] < 1:
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
