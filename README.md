# Enterprise GraphRAG

An iteratively developed knowledge retrieval system, evolving from traditional RAG toward advanced GraphRAG.

The goal is a simple, understandable, production-oriented architecture, developed and evaluated locally using synthetic enterprise data instead of large-scale infrastructure.

## Getting started

1. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.
2. Start the application:

   ```bash
   docker compose up --build
   ```

3. Once Neo4j is ready, load or resync the graph in another terminal:

   ```bash
   docker compose exec backend python -m app.graph_seed
   ```

4. Open the interfaces:

   - Chat: [http://localhost:3000](http://localhost:3000) — Select Vector RAG (Standard or Multi-step) or Graph RAG, ask questions and inspect sources.
   - Evaluation: [http://localhost:3000/evaluate](http://localhost:3000/evaluate) — Run each search system and compare results side by side.
   - API: [http://localhost:8000/docs](http://localhost:8000/docs) — FastAPI Swagger documentation.
   - Neo4j Browser: [http://localhost:7474](http://localhost:7474) — Inspect the graph and run Cypher queries.

For Vector RAG, index the built-in corpus in Chat if it has not been indexed yet. Graph loading does not call OpenAI or change Qdrant.

Neo4j settings are listed in [.env.example](.env.example). `NEO4J_PASSWORD` initializes the password on first start; an existing volume keeps its original password. `NEO4J_DATABASE` defaults to `neo4j`. Compose sets the backend connection to `bolt://neo4j:7687` with username `neo4j`; outside Docker, use `NEO4J_URI` and `NEO4J_USERNAME` for the local connection. Neo4j data persists in the `neo4j_data` volume.

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

## Part 2 Graph & Schema

- Neo4j integrated into Docker Compose
- Document and chunk graph from the existing 14 documents
- Knowledge graph with 19 business entities and source references
- Idempotent Python seed loading
- 8 reproducible Cypher queries
- LLM-guided Text2Cypher with validated query templates
- Vector RAG and Graph RAG selectable in the same streaming chat
- Comparative evaluation on the same 12 questions
- Backend, frontend and Neo4j integration tests

### Results and observations

- Both systems completed 12/12 evaluation questions.
- Average source coverage: Vector RAG 88.9%, Graph RAG 91.7%.
- Local and multi-hop: 100% for both; global: 66.7% vs. 75.0%.
- Average response time: Vector RAG 3.33 s, Graph RAG 3.74 s.
- Graph RAG achieved higher source coverage, with slightly higher latency.

Source coverage measures retrieved evidence, not answer correctness. Results are based on a single local evaluation.
