// Run these eight reads individually in Neo4j Browser or cypher-shell after loading the HelioWorks seed.
// Load it with: docker compose exec backend python -m app.graph_seed

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

// 5. Real 3-hop traversal: supplier -> project <- leader -> department, with primary sources.
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
WHERE d.source IN a.evidence_sources + b.evidence_sources AND c.id IN a.chunk_ids + b.chunk_ids
RETURN i.date AS incident_date, p.name AS project, v.name AS vendor, d.source AS source,
       c.chunk AS chunk, c.text AS evidence ORDER BY source, chunk LIMIT 64;
