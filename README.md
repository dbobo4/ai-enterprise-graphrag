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

After changing seed documents, use **Prepare documents** in Chat and rerun the graph sync command. Seed synchronization removes obsolete seed records and preserves uploaded documents.

Neo4j settings are listed in [.env.example](.env.example). `NEO4J_PASSWORD` initializes the password on first start; an existing volume keeps its original password. `NEO4J_DATABASE` defaults to `neo4j`. Compose sets the backend connection to `bolt://neo4j:7687` with username `neo4j`; outside Docker, use `NEO4J_URI` and `NEO4J_USERNAME` for the local connection. Neo4j data persists in the `neo4j_data` volume.

## Part 1  Naive RAG

- Next.js frontend, FastAPI backend
- Multi-stage Docker, Docker Compose
- LangChain + OpenAI + Qdrant
- Synthetic HelioWorks corpus: 34 business documents split into 170 chunks, similar project names and multiple suppliers
- Vector Standard (top_k=4) and Multi-step RAG with verified intermediate evidence and one extraction retry
- Document upload: TXT, MD, PDF, DOCX, HTML, XLSX
- Streaming chat with source references
- Seed-only evaluation on 12 local, multi-hop and global questions
- Backend and frontend regression tests

### Results and observations

- Both vector modes processed 12/12 questions; source coverage was 62.5% for Standard and 77.8% for Multi-step.
- Average response time: Standard 3.04 s, Multi-step 10.23 s.
- Standard's four excerpts cover 2.35% of the chunks. Global coverage was 37.5% vs. 41.7%; Multi-step can stop when intermediate evidence cannot be verified.

Detailed answers, sources and call counts are in [evaluation/baseline_answers.md](evaluation/baseline_answers.md). Use **Download evaluation report** to save an Evaluation run.

## Part 2 Graph & Schema

- Neo4j integrated into Docker Compose
- Document and chunk graph from the same 34 documents
- Reviewed knowledge graph with 34 business entities and precise supporting chunks
- Idempotent Python seed loading
- 8 reproducible Cypher queries
- LLM-guided Text2Cypher with validated, parameterized read templates
- Vector RAG and Graph RAG selectable in the same streaming chat
- Comparative evaluation: Vector Standard, Vector Multi-step and Graph RAG
- Backend, frontend and Neo4j integration tests

### Results and observations

- Graph RAG processed 12/12 questions, with 91.7% source coverage and a 6.46 s average response time.
- Multi-hop and global source coverage reached 100%; latency fell between Standard and Multi-step.
- Q04 is unsupported; Q12 omitted the 12-month retention rule for public training materials despite finding all expected documents.

Source coverage measures retrieved evidence, not answer correctness. Timings come from one local run per mode. Graph RAG uses reviewed relationships and selected evidence chunks, with no Vector fallback.
