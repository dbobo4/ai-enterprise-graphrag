"""Reviewed HelioWorks facts. Sync with: docker compose exec backend python -m app.graph_seed"""

from uuid import NAMESPACE_URL, uuid5

from app.rag import seed_chunks

DATASET = "helioworks-seed-v1"
LABELS = {"Company", "Department", "Person", "Project", "Vendor", "Incident", "Policy"}
RELATION_TYPES = {
    "HAS_DEPARTMENT": ("Company", "Department"), "WORKS_IN": ("Person", "Department"),
    "LEADS": ("Person", "Project"), "SUPPLIES": ("Vendor", "Project"),
    "AFFECTS": ("Incident", "Project"), "APPROVES": ("Department", "Policy"),
    "OWNS_CONTRACT": ("Department", "Vendor"),
}

# id, label, source, properties. Dates and names are attributes, not extra nodes.
NODES = [
    ("company:helioworks", "Company", "company.md", {"name": "HelioWorks Kft."}),
    ("department:it", "Department", "company.md", {"name": "IT"}),
    ("department:hr", "Department", "company.md", {"name": "HR"}),
    ("department:procurement", "Department", "company.md", {"name": "Procurement"}),
    ("department:finance", "Department", "company.md", {"name": "Finance"}),
    ("person:nora-varga", "Person", "people/roles.md", {"name": "Nóra Varga", "role": "systems engineering lead"}),
    ("person:tamas-fekete", "Person", "people/roles.md", {"name": "Tamás Fekete", "role": "onboarding process owner"}),
    ("person:reka-kiss", "Person", "people/roles.md", {"name": "Réka Kiss", "role": "supplier coordination lead"}),
    ("person:bence-molnar", "Person", "people/roles.md", {"name": "Bence Molnár", "role": "oversees cost reporting"}),
    ("project:atlas", "Project", "projects/atlas.md", {"name": "Project Atlas", "purpose": "Internal support ticketing platform", "go_live": "2026-11-15"}),
    ("project:beacon", "Project", "projects/beacon.md", {"name": "Project Beacon", "purpose": "Office network renewal", "go_live": "2027-01-20"}),
    ("project:bridge", "Project", "projects/bridge.md", {"name": "Project Bridge", "purpose": "Employee onboarding", "go_live": "2026-12-01"}),
    ("vendor:novacloud", "Vendor", "vendors/novacloud.md", {"name": "NovaCloud Ltd.", "service": "Managed API gateway hosting", "renewal_date": "2027-03-01"}),
    ("vendor:greenwire", "Vendor", "vendors/greenwire.md", {"name": "GreenWire Zrt.", "service": "Network switches and equipment maintenance", "renewal_date": "2027-06-30"}),
    ("vendor:clearid", "Vendor", "vendors/clearid.md", {"name": "ClearID Kft.", "service": "Identity and document verification", "expiry_date": "2027-01-31"}),
    ("incident:atlas", "Incident", "incidents/atlas.md", {"name": "September 2026 API outage", "date": "2026-09-18", "duration_minutes": 42, "root_cause": "Incorrect gateway routing rule introduced during deployment"}),
    ("incident:beacon", "Incident", "incidents/beacon.md", {"name": "August 2026 switch interruption", "date": "2026-08-25", "root_cause": "Faulty firmware on a replacement network switch"}),
    ("incident:bridge", "Incident", "incidents/bridge.md", {"name": "October 2026 onboarding delays", "date": "2026-10-09", "root_cause": "Repeated timeouts in an external verification service"}),
    ("policy:access", "Policy", "policies/access.md", {"name": "Temporary accounts", "max_initial_days": 30}),
]

# start, relationship, end, source. Each edge has its own evidence.
RELATIONSHIPS = [
    ("company:helioworks", "HAS_DEPARTMENT", "department:it", "company.md"),
    ("company:helioworks", "HAS_DEPARTMENT", "department:hr", "company.md"),
    ("company:helioworks", "HAS_DEPARTMENT", "department:procurement", "company.md"),
    ("company:helioworks", "HAS_DEPARTMENT", "department:finance", "company.md"),
    ("person:nora-varga", "WORKS_IN", "department:it", "people/roles.md"),
    ("person:tamas-fekete", "WORKS_IN", "department:hr", "people/roles.md"),
    ("person:reka-kiss", "WORKS_IN", "department:procurement", "people/roles.md"),
    ("person:bence-molnar", "WORKS_IN", "department:finance", "people/roles.md"),
    ("person:nora-varga", "LEADS", "project:atlas", "projects/atlas.md"),
    ("person:reka-kiss", "LEADS", "project:beacon", "projects/beacon.md"),
    ("person:tamas-fekete", "LEADS", "project:bridge", "projects/bridge.md"),
    ("vendor:novacloud", "SUPPLIES", "project:atlas", "vendors/novacloud.md"),
    ("vendor:greenwire", "SUPPLIES", "project:beacon", "vendors/greenwire.md"),
    ("vendor:clearid", "SUPPLIES", "project:bridge", "vendors/clearid.md"),
    ("incident:atlas", "AFFECTS", "project:atlas", "incidents/atlas.md"),
    ("incident:beacon", "AFFECTS", "project:beacon", "incidents/beacon.md"),
    ("incident:bridge", "AFFECTS", "project:bridge", "incidents/bridge.md"),
    ("department:it", "APPROVES", "policy:access", "policies/access.md"),
    ("department:procurement", "OWNS_CONTRACT", "vendor:novacloud", "vendors/novacloud.md"),
]


def document_graph(documents: list, chunk_ids: list[str]) -> tuple[list[dict], list[dict]]:
    if len(documents) != len(chunk_ids):
        raise ValueError("Every chunk needs its original vector point id.")
    nodes = {}
    edges = []
    by_source = {}
    for document, chunk_id in zip(documents, chunk_ids):
        metadata = document.metadata
        source, index = metadata["source"], metadata["chunk"]
        doc_id = "document:" + source
        if chunk_id in nodes or not isinstance(index, int) or index < 0 or not document.page_content.strip():
            raise ValueError("Invalid or duplicate chunk.")
        nodes[doc_id] = {"id": doc_id, "label": "Document", "source_id": source, "source": source, "document_id": metadata["document_id"]}
        row = {"id": chunk_id, "label": "Chunk", "source_id": source, "source": source, "chunk": index, "text": document.page_content}
        for field in ("page", "section"):
            if field in metadata:
                row[field] = metadata[field]
        nodes[chunk_id] = row
        edges.append({"start": doc_id, "type": "CONTAINS", "end": chunk_id, "source_id": source})
        by_source.setdefault(source, []).append((index, chunk_id))
    for source, chunks in by_source.items():
        chunks.sort()
        for position, (index, chunk_id) in enumerate(chunks):
            if index != position:
                raise ValueError("Chunk numbers must start at zero and be consecutive.")
            if position > 0:
                edges.append({"start": chunks[position - 1][1], "type": "NEXT_CHUNK", "end": chunk_id, "source_id": source})
    return list(nodes.values()), edges


def seed_graph() -> tuple[list[dict], list[dict]]:
    documents, chunk_ids = seed_chunks()
    nodes, edges = document_graph(documents, chunk_ids)
    sources = set()
    for node in nodes:
        if node["label"] == "Document":
            sources.add(node["source"])
    entity_labels = {}
    for entity_id, label, source, properties in NODES:
        if entity_id in entity_labels or label not in LABELS or source not in sources:
            raise ValueError("Invalid seed entity or source.")
        entity_labels[entity_id] = label
        nodes.append({"id": entity_id, "label": label, "source_id": source, **properties})
        edges.append({"start": entity_id, "type": "SUPPORTED_BY", "end": "document:" + source, "source_id": source})
    for start, kind, end, source in RELATIONSHIPS:
        labels = (entity_labels.get(start), entity_labels.get(end))
        if kind not in RELATION_TYPES or labels != RELATION_TYPES[kind] or source not in sources:
            raise ValueError("Invalid seed relationship or source.")
        edges.append({"start": start, "type": kind, "end": end, "source_id": source})
    for node in nodes:
        node["dataset"] = DATASET
    edge_ids = set()
    for edge in edges:
        edge["id"] = str(uuid5(NAMESPACE_URL, f'{DATASET}:{edge["start"]}:{edge["type"]}:{edge["end"]}'))
        edge["dataset"] = DATASET
        if edge["id"] in edge_ids:
            raise ValueError("Duplicate seed relationship.")
        edge_ids.add(edge["id"])
    return nodes, edges


def write_seed(tx, nodes: list[dict], edges: list[dict]) -> None:
    for node in nodes:
        label = node["label"]
        if label not in LABELS | {"Document", "Chunk"}:
            raise ValueError("Unknown node label.")
        base = label if label in ("Document", "Chunk") else "Entity"
        properties = dict(node)
        del properties["label"]
        tx.run(f"MERGE (n:{base} {{id: $id}}) SET n:{label} SET n = $properties", id=node["id"], properties=properties).consume()
    for edge in edges:
        kind = edge["type"]
        if kind not in set(RELATION_TYPES) | {"CONTAINS", "NEXT_CHUNK", "SUPPORTED_BY"}:
            raise ValueError("Unknown relationship type.")
        properties = dict(edge)
        for field in ("start", "end", "type"):
            del properties[field]
        tx.run(f"MATCH (a {{id: $start, dataset: $dataset}}), (b {{id: $end, dataset: $dataset}}) "
               f"MERGE (a)-[r:{kind} {{id: $id}}]->(b) SET r = $properties",
               start=edge["start"], end=edge["end"], dataset=DATASET, id=edge["id"], properties=properties).consume()
    node_ids = [node["id"] for node in nodes]
    edge_ids = [edge["id"] for edge in edges]
    tx.run("MATCH ()-[r]->() WHERE r.dataset = $dataset AND NOT r.id IN $ids DELETE r", dataset=DATASET, ids=edge_ids).consume()
    tx.run("MATCH (n) WHERE n.dataset = $dataset AND NOT n.id IN $ids DETACH DELETE n", dataset=DATASET, ids=node_ids).consume()


def sync_seed() -> dict[str, int]:
    from app.graph import graph_driver, graph_session

    nodes, edges = seed_graph()
    with graph_driver() as driver, graph_session(driver) as session:
        for label in ("Entity", "Document", "Chunk"):
            session.run(f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE").consume()
        session.execute_write(write_seed, nodes, edges)
    counts = {"entities": 0, "documents": 0, "chunks": 0, "relationships": len(edges)}
    for node in nodes:
        key = {"Document": "documents", "Chunk": "chunks"}.get(node["label"], "entities")
        counts[key] += 1
    return counts


if __name__ == "__main__":
    try:
        counts = sync_seed()
    except Exception:
        raise SystemExit("Graph sync failed. Check Neo4j availability and configuration.") from None
    print(f'Graph synced: {counts["entities"]} entities, {counts["documents"]} documents, {counts["chunks"]} chunks, {counts["relationships"]} relationships.')
