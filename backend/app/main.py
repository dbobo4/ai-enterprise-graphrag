import json
from collections.abc import AsyncGenerator
from contextlib import aclosing, asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.chat import stream_answer
from app.config import validate_startup
from app.contracts import Answer, ErrorEvent, SearchMode
from app.evaluation import EvaluationConflict, EvaluationRun, EvaluationUnavailable, Question, evaluate_corpus, load_questions
from app.graph import graph_status
from app.rag import answer, corpus_status, index_seed
from app.uploads import MAX_UPLOAD_BYTES, UploadError, UploadResult, upload_document


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    validate_startup()
    yield


app = FastAPI(title="Enterprise GraphRAG API", version="0.2.0", lifespan=lifespan)


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    top_k: int = Field(default=4, ge=1, le=12)


class StreamChatRequest(ChatRequest):
    mode: SearchMode = "standard"
    filename: str | None = Field(default=None, min_length=1, max_length=100)


class EvaluationRequest(BaseModel):
    system: Literal["vector", "standard", "multi-step", "graph"] = "standard"


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "stage": "naive-rag"}


@app.get("/api/corpus")
def corpus() -> dict:
    try:
        return corpus_status()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Qdrant is unavailable.") from exc


@app.get("/api/graph")
def graph() -> dict:
    try:
        return graph_status()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Graph search is unavailable.") from exc


@app.get("/api/questions")
def questions() -> list[Question]:
    try:
        return load_questions(Path("/app/evaluation/questions.json"))
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Test questions are unavailable.") from exc


def evaluation_input(request: EvaluationRequest | None = None) -> tuple[list[Question], SearchMode]:
    system = request.system if request else "standard"
    return questions(), "standard" if system == "vector" else system


@app.post("/api/evaluate")
async def evaluate(inputs: Annotated[tuple[list[Question], SearchMode], Depends(evaluation_input)]) -> EvaluationRun:
    test_questions, system = inputs
    try:
        return await evaluate_corpus(test_questions, system)
    except EvaluationUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except EvaluationConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/ingest/upload")
def ingest_upload(file: Annotated[UploadFile, File()]) -> UploadResult:
    try:
        content = file.file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="The document exceeds the 10 MB limit.")
        return upload_document(file.filename or "", content)
    except UploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="The document could not be added to both search systems. Retry the same file.") from exc
    finally:
        file.file.close()


@app.post("/api/ingest/seed")
def ingest_seed() -> dict:
    try:
        return index_seed()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Indexing failed. Check backend logs and configuration.") from exc


@app.post("/api/chat", response_model=None)
def chat(request: ChatRequest) -> Answer:
    try:
        return answer(request.question, request.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="RAG request failed. Check backend logs and API credits.") from exc


@app.post("/api/chat/stream")
async def chat_stream(request: StreamChatRequest, connection: Request) -> StreamingResponse:
    async def events() -> AsyncGenerator[str, None]:
        try:
            if await connection.is_disconnected():
                return
            stream = (stream_answer(request.question, request.top_k, request.mode, filename=request.filename)
                      if request.mode == "graph" and request.filename else stream_answer(request.question, request.top_k, request.mode))
            async with aclosing(stream):
                async for event in stream:
                    if await connection.is_disconnected():
                        return
                    yield "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
        except Exception:
            error: ErrorEvent = {"type": "error", "message": "The answer could not be completed. Please try again."}
            yield "data: " + json.dumps(error) + "\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})
