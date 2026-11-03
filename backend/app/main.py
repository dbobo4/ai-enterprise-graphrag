import json
from contextlib import aclosing
from functools import partial
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.chat import stream_answer
from app.evaluation import run_evaluation
from app.rag import answer, corpus_status, index_seed
from app.uploads import MAX_UPLOAD_BYTES, UploadError, upload_document

app = FastAPI(title="Enterprise GraphRAG API", version="0.2.0")


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    top_k: int = Field(default=4, ge=1, le=12)


class StreamChatRequest(ChatRequest):
    mode: Literal["standard", "multi-step"] = "standard"


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "stage": "naive-rag"}


@app.get("/api/corpus")
def corpus() -> dict:
    try:
        return corpus_status()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Qdrant is unavailable.") from exc


@app.get("/api/questions")
def questions() -> list[dict]:
    path = Path("/app/evaluation/questions.json")
    return json.loads(path.read_text(encoding="utf-8"))


@app.post("/api/evaluate")
def evaluate() -> dict:
    try:
        test_questions = questions()
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Test questions are unavailable.") from exc
    return run_evaluation(test_questions, partial(answer, seed_only=True))


@app.post("/api/ingest/upload")
def ingest_upload(file: UploadFile = File(...)) -> dict:
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
        raise HTTPException(status_code=502, detail="The document could not be added. Please try again.") from exc
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


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict:
    try:
        return answer(request.question, request.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="RAG request failed. Check backend logs and API credits.") from exc


@app.post("/api/chat/stream")
async def chat_stream(request: StreamChatRequest, connection: Request) -> StreamingResponse:
    async def events():
        try:
            if await connection.is_disconnected():
                return
            async with aclosing(stream_answer(request.question, request.top_k, request.mode)) as stream:
                async for event in stream:
                    if await connection.is_disconnected():
                        return
                    yield "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
        except Exception:
            yield "data: " + json.dumps({"type": "error", "message": "The answer could not be completed. Please try again."}) + "\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})
