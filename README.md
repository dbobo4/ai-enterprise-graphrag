# Enterprise GraphRAG

A knowledge assistant for company documents and uploads, with Vector RAG, Graph RAG and source citations.

## Architecture & Design

- Keep HTTP validation in routes, workflows in services and database access at their edges so each can be tested separately.
- Validate shared settings at API startup so configuration errors surface before requests.
- Type streaming events, evaluation results and graph records so their fields are explicit at each boundary.
- Reuse the same chunk content and stable IDs in both databases so repeated writes converge without duplicating records.
- Keep normalized entity descriptions separate from exact source quotes so entity merges preserve every original reference.
- Publish validated files atomically so parallel requests can reuse the same complete upload.
- Write Neo4j records in labeled batches to reduce database round trips.
- Share answer and source handling across retrieval modes while evaluating each mode on the same seed questions.

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

After changing seed documents, use **Prepare documents** in Chat and rerun the graph sync command. Keep seed files fixed while synchronizing. Seed synchronization removes obsolete seed records and preserves uploads.

Uploads store the same chunks and document metadata in Qdrant and Neo4j. Retry the same file to complete a partial write. In Graph RAG, enter the saved filename to search uploaded text or leave it blank to search company facts. Business entities come from the reviewed seed.

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

- Both vector modes finished 12/12 questions. Standard reached 62.5% source coverage in 2.53 s on average, and Multi-step reached 76.4% in 7.25 s.
- Global coverage was 37.5% for both. Multi-step stopped on some questions when intermediate evidence could not be verified.

Detailed answers, sources and call counts are in [evaluation/baseline_answers.md](evaluation/baseline_answers.md). Use **Download evaluation report** to save an Evaluation run.

## Part 2 Graph & Schema

- Neo4j integrated into Docker Compose
- Document and chunk graph for seed files and uploads with `CONTAINS` and `NEXT_CHUNK` links
- Reviewed knowledge graph with 34 entities across companies, departments, people, projects, vendors, incidents and policies
- Exact quotes on business edges and `SUPPORTED_BY` links from entities to source documents
- Batched, idempotent Python seed loading and [8 Cypher queries](backend/graph.cypher)
- LLM-guided Text2Cypher with validated, parameterized read templates
- Vector RAG and Graph RAG selectable in the same streaming chat
- Comparative evaluation: Vector Standard, Vector Multi-step and Graph RAG
- Backend, frontend and Neo4j integration tests

### Results and observations

- Graph RAG finished 12/12 questions with 91.7% source coverage and a 5.53 s average response time.
- Multi-hop and global source coverage reached 100%. Q04 was unsupported, and Q12 omitted the 12-month retention rule for public training materials despite finding all expected documents.

Source coverage measures how many expected source documents were retrieved. Answer correctness requires a separate review.
