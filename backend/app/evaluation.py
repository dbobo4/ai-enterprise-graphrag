from collections.abc import Callable
from time import perf_counter


def summarize(results: list[dict]) -> dict:
    successful = 0
    coverage = 0.0
    response_time = 0.0
    for result in results:
        if result["error"] is None:
            successful += 1
            coverage += result["source_coverage"]
            response_time += result["response_time_seconds"]

    return {
        "total": len(results), "successful": successful,
        "average_source_coverage": coverage / successful if successful else None,
        "average_response_time_seconds": response_time / successful if successful else None,
    }


def run_evaluation(questions: list[dict], answer_question: Callable[[str, int], dict]) -> dict:
    results = []
    for question in questions:
        result = {
            "id": question["id"], "type": question["type"], "question": question["question"],
            "expected_answer": question["expected_answer"], "required_sources": question["required_sources"],
            "answer": None, "sources": [], "source_coverage": None, "error": None,
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
        except Exception:
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
