// HelioWorks Graph & Schema. All facts originate in data/seed; no LLM extraction.
// Start: docker compose up --build
// Load or resync: docker compose exec backend python -m app.graph_seed
// No OpenAI or Qdrant calls are made by the sync command. Run again to verify stable counts.
// Only nodes/edges tagged dataset=helioworks-seed-v1 are synchronized; obsolete managed records are removed atomically.
// Neo4j Community uses neo4j/<NEO4J_PASSWORD>, default enterprise-demo-password for this local demo.
// Its /data is stored in neo4j_data. Existing volume passwords are not changed by NEO4J_AUTH.
// The initial username is neo4j; database defaults to neo4j. Do not select an uncreated database.
//
// Entity subgraph: Company, Department, Person, Project, Vendor, Incident, Policy (19 nodes).
// Entity.id is a stable typed key. All nodes carry dataset and source_id (the actual corpus-relative path).
// Person: name, role. Project: name, purpose, go_live. Vendor: name, service, renewal_date OR expiry_date.
// Incident: name, date, root_cause, duration_minutes only where documented. Policy: name, max_initial_days.
// Company/Department: name; Human Resources membership is recorded under the company department name HR.
// Dates, roles and names are properties. Incidents need nodes to link project impacts to supplier evidence.
// The access Policy needs a node because IT approval is a relationship; other policies remain documents.
//
// Company-HAS_DEPARTMENT->Department; Person-WORKS_IN->Department; Person-LEADS->Project;
// Vendor-SUPPLIES->Project; Incident-AFFECTS->Project; Department-APPROVES->Policy;
// Department-OWNS_CONTRACT->Vendor (only the explicitly documented NovaCloud contract).
// Every relationship has a stable id, dataset and source_id. No unrecorded contract owners are inferred.
//
// Separate document graph: Document-CONTAINS->Chunk; Chunk-NEXT_CHUNK->Chunk.
// Entity-SUPPORTED_BY->Document connects the two subgraphs through real evidence.
// Document.id = document:<source path>; document_id preserves the old metadata stem, which is not globally unique.
// Chunk.id equals its existing Qdrant UUID; text/source/chunk come unchanged from rag.seed_chunks().
// page/section are stored only if present in the input metadata. These Markdown seeds have neither.
// The current seeds are single-chunk; a separate offline multi-chunk fixture tests NEXT_CHUNK.
//
// Graph search: gpt-6.1-sol, medium reasoning, Responses API, strict CypherPlan schema, no temperature.
// OPENAI_CYPHER_MODEL can change the planner only; answer/embedding models remain unchanged.
// Nine fixed read templates in app/graph.py cover direct entity facts, four relation paths and four lists.
// The model selects operation/entity_id, never executable Cypher. Unknown keys, entities and operations fail validation.
// Writes/admin queries cannot pass the exact read-statement allowlist; all values are parameters.
// Each query has a 10-second timeout and a row limit (24 facts, 64 evidence chunks).
// READ_ACCESS is routing, not database authorization. Community has no Enterprise read-only role boundary.
// The allowlist is the enforcement boundary. The trusted sync CLI alone performs writes.
// Unsupported questions return an explicit limitation; missing evidence returns no claim; no Vector fallback.
// Graph evaluation uses the same 12 questions and metric; top_k=4 remains the Vector baseline only.
// Compare using /evaluate: run each system independently; both results remain visible side by side.
// Source coverage measures retrieved expected documents, not semantic correctness.
//
// Execute the following 8 read queries in Neo4j Browser, individually or through cypher-shell.
// They use the exact managed dataset, need no parameters and do not require APOC or Enterprise features.
// No runtime measurements are claimed here; actual local execution remains part of validation.

// 1. Document and chunk counts, including an empty graph.
OPTIONAL MATCH (d:Document {dataset: 'helioworks-seed-v1'})
WITH count(d) AS documents
OPTIONAL MATCH (c:Chunk {dataset: 'helioworks-seed-v1'})
RETURN documents, count(c) AS chunks;

// 2. A document with the most chunks (deterministic tie break).
MATCH (d:Document {dataset: 'helioworks-seed-v1'})
OPTIONAL MATCH (d)-[:CONTAINS]->(c:Chunk)
RETURN d.source AS document, count(c) AS chunks ORDER BY chunks DESC, document LIMIT 1;

// 3. All documents tied for the fewest chunks, including documents without chunks.
MATCH (d:Document {dataset: 'helioworks-seed-v1'})
OPTIONAL MATCH (d)-[:CONTAINS]->(c:Chunk)
WITH d, count(c) AS chunks ORDER BY chunks, d.source
WITH collect({document: d.source, chunks: chunks}) AS rows, min(chunks) AS fewest
UNWIND rows AS row
WITH row, fewest WHERE row.chunks = fewest
RETURN row.document AS document, row.chunks AS chunks ORDER BY document;

// 4. Empty text, missing metadata, orphaned or multiply owned chunks. Zero rows is healthy.
MATCH (c:Chunk {dataset: 'helioworks-seed-v1'})
OPTIONAL MATCH (d:Document)-[:CONTAINS]->(c)
WITH c, collect(d) AS owners
WHERE trim(coalesce(c.text, '')) = '' OR c.source IS NULL OR c.id IS NULL OR c.chunk IS NULL
   OR c.chunk < 0 OR size(owners) <> 1 OR any(d IN owners WHERE d.source <> c.source)
RETURN c.id AS chunk_id, c.source AS source, c.chunk AS chunk, size(owners) AS documents LIMIT 64;

// 5. Real 3-hop traversal: supplier -> project <- leader -> department, with edge evidence.
MATCH (v:Vendor {id: 'vendor:clearid', dataset: 'helioworks-seed-v1'})-[a:SUPPLIES]->(p:Project)<-[b:LEADS]-(l:Person)-[c:WORKS_IN]->(d:Department)
RETURN v.name AS vendor, p.name AS project, l.name AS leader, d.name AS department,
       [a.source_id, b.source_id, c.source_id] AS sources LIMIT 24;

// 6. Aggregation: projects and names per supplier.
MATCH (v:Vendor {dataset: 'helioworks-seed-v1'})-[r:SUPPLIES]->(p:Project)
RETURN v.name AS vendor, count(DISTINCT p) AS projects, collect(DISTINCT p.name) AS names,
       collect(DISTINCT r.source_id) AS sources ORDER BY vendor LIMIT 24;

// 7. Actual business node/relationship structure and provenance, not a hand-drawn schema.
MATCH (a:Entity {dataset: 'helioworks-seed-v1'})-[r]->(b:Entity {dataset: 'helioworks-seed-v1'})
RETURN a.id AS start, labels(a) AS start_labels, type(r) AS relationship, b.id AS end,
       labels(b) AS end_labels, r.source_id AS source ORDER BY start, relationship, end LIMIT 64;

// 8. Follow an incident to its supplier and its actual evidence chunks.
MATCH (i:Incident {id: 'incident:atlas', dataset: 'helioworks-seed-v1'})-[a:AFFECTS]->(p:Project)<-[b:SUPPLIES]-(v:Vendor)
MATCH (d:Document {dataset: 'helioworks-seed-v1'})-[:CONTAINS]->(c:Chunk)
WHERE d.source IN [a.source_id, b.source_id]
RETURN i.date AS incident_date, p.name AS project, v.name AS vendor, d.source AS source,
       c.chunk AS chunk, c.text AS evidence ORDER BY source, chunk LIMIT 64;
