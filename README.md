# Enterprise GraphRAG

An iteratively developed knowledge retrieval system, evolving from traditional RAG toward advanced GraphRAG.

The goal is a simple, understandable, production-oriented architecture, developed and evaluated locally using synthetic enterprise data instead of large-scale infrastructure.

## Getting started

1. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.
2. Start the application:

   ```bash
   docker compose up --build
   ```

3. Open the interfaces:

   - Chat: [http://localhost:3000](http://localhost:3000) — Ask questions, upload documents, select Standard or Multi-step search.
   - Evaluation: [http://localhost:3000/evaluate](http://localhost:3000/evaluate) — Run automated tests and inspect results.
   - API: [http://localhost:8000/docs](http://localhost:8000/docs) — FastAPI Swagger documentation.

Index the built-in corpus if it has not been indexed yet.

## Part 1  Naive RAG

- Next.js frontend, FastAPI backend
- Multi-stage Docker, Docker Compose
- LangChain + OpenAI + Qdrant
- Synthetic enterprise corpus (14 documents)
- Standard and Multi-step RAG
- Document upload: TXT, MD, PDF, DOCX, HTML, XLSX
- Streaming chat with source references
- Automated evaluation (12 questions)
- Backend and frontend regression tests

### Results and observations

- 12/12 evaluation questions completed.
- Average source coverage: 88.9%.
- Local and multi-hop: 100%; global: 66.7%.
- Global questions exposed limitations in retrieving all relevant documents.

Source coverage measures retrieved evidence, not answer correctness. The baseline will be used for comparison with future GraphRAG implementations.
