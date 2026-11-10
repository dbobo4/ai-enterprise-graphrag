"""Reviewed HelioWorks facts. Sync: docker compose exec backend python -m app.graph_seed"""

from uuid import NAMESPACE_URL, uuid5

from app.rag import seed_chunks

DATASET = "helioworks-seed-v1"
LABELS = {"Company", "Department", "Person", "Project", "Vendor", "Incident", "Policy"}
RELATION_TYPES = {
    "HAS_DEPARTMENT": ("Company", "Department"), "WORKS_IN": ("Person", "Department"),
    "LEADS": ("Person", "Project"), "SUPPLIES": ("Vendor", "Project"), "AFFECTS": ("Incident", "Project"),
    "APPROVES": ("Department", "Policy"), "OWNS_CONTRACT": ("Department", "Vendor"),
}

# id, label, source, properties. Quotes identify actual supporting chunks, not whole documents.
NODES = [
    ("company:helioworks", "Company", "company.md", {"name": "HelioWorks Kft.", "quote": "HelioWorks Kft. has five departments: IT, HR, Procurement, Finance and Operations."}),
    ("department:it", "Department", "company.md", {"name": "IT", "quote": "HelioWorks Kft. has five departments: IT, HR, Procurement, Finance and Operations."}),
    ("department:hr", "Department", "company.md", {"name": "HR", "quote": "HelioWorks Kft. has five departments: IT, HR, Procurement, Finance and Operations."}),
    ("department:procurement", "Department", "company.md", {"name": "Procurement", "quote": "HelioWorks Kft. has five departments: IT, HR, Procurement, Finance and Operations."}),
    ("department:finance", "Department", "company.md", {"name": "Finance", "quote": "HelioWorks Kft. has five departments: IT, HR, Procurement, Finance and Operations."}),
    ("department:operations", "Department", "company.md", {"name": "Operations", "quote": "HelioWorks Kft. has five departments: IT, HR, Procurement, Finance and Operations."}),
    ("person:nora-varga", "Person", "people/roles.md", {"name": "Nóra Varga", "role": "systems engineering lead", "quote": "Nóra Varga works in IT as a systems engineering lead."}),
    ("person:tamas-fekete", "Person", "people/roles.md", {"name": "Tamás Fekete", "role": "onboarding process owner", "quote": "Tamás Fekete works in HR as an onboarding process owner."}),
    ("person:reka-kiss", "Person", "people/roles.md", {"name": "Réka Kiss", "role": "supplier coordination lead", "quote": "Réka Kiss works in Procurement as a supplier coordination lead."}),
    ("person:bence-molnar", "Person", "people/roles.md", {"name": "Bence Molnár", "role": "cost reporting owner", "quote": "Bence Molnár works in Finance as a cost reporting owner."}),
    ("person:nora-varadi", "Person", "people/roles.md", {"name": "Nóra Váradi", "role": "records migration owner", "quote": "Nóra Váradi works in Operations as a records migration owner."}),
    ("person:peter-varga", "Person", "people/roles.md", {"name": "Péter Varga", "role": "financial controls analyst", "quote": "Péter Varga works in Finance as a financial controls analyst."}),
    ("person:miklos-fekete", "Person", "people/roles.md", {"name": "Miklós Fekete", "role": "warehouse process owner", "quote": "Miklós Fekete works in Operations as a warehouse process owner."}),
    ("project:atlas", "Project", "projects/atlas.md", {"name": "Project Atlas", "purpose": "internal support ticketing platform", "go_live": "2026-11-15", "quote": "Nóra Varga leads Project Atlas, the internal support ticketing platform, with a target go-live of 2026-11-15."}),
    ("project:beacon", "Project", "projects/beacon.md", {"name": "Project Beacon", "purpose": "office network renewal", "go_live": "2027-01-20", "quote": "Réka Kiss leads Project Beacon, the office network renewal, with a target go-live of 2027-01-20."}),
    ("project:bridge", "Project", "projects/bridge.md", {"name": "Project Bridge", "purpose": "employee onboarding service", "go_live": "2026-12-01", "quote": "Tamás Fekete leads Project Bridge, the employee onboarding service, with a target go-live of 2026-12-01."}),
    ("project:atlas-archive", "Project", "projects/atlas-archive.md", {"name": "Project Atlas Archive", "purpose": "records migration programme", "go_live": "2027-02-12", "quote": "Nóra Váradi leads Project Atlas Archive, the records migration programme, with a target go-live of 2027-02-12."}),
    ("project:bridge-north", "Project", "projects/bridge-north.md", {"name": "Project Bridge North", "purpose": "warehouse onboarding programme", "go_live": "2027-01-11", "quote": "Miklós Fekete leads Project Bridge North, the warehouse onboarding programme, with a target go-live of 2027-01-11."}),
    ("project:beacon-lab", "Project", "projects/beacon-lab.md", {"name": "Project Beacon Lab", "purpose": "finance network sandbox", "go_live": "2026-12-15", "quote": "Péter Varga leads Project Beacon Lab, the finance network sandbox, with a target go-live of 2026-12-15."}),
    ("vendor:novacloud", "Vendor", "vendors/novacloud.md", {"name": "NovaCloud Ltd.", "service": "managed API gateway hosting", "renewal_date": "2027-03-01", "quote": "NovaCloud Ltd. supplies managed API gateway hosting for Project Atlas. The agreement renews on 2027-03-01 and Procurement owns the contract."}),
    ("vendor:greenwire", "Vendor", "vendors/greenwire.md", {"name": "GreenWire Zrt.", "service": "network switches and equipment maintenance", "renewal_date": "2027-06-30", "quote": "GreenWire Zrt. supplies network switches and equipment maintenance for Project Beacon and Project Bridge North. The framework renews on 2027-06-30."}),
    ("vendor:clearid", "Vendor", "vendors/clearid.md", {"name": "ClearID Kft.", "service": "identity and document verification", "expiry_date": "2027-01-31", "quote": "ClearID Kft. provides identity and document verification for Project Bridge. The agreement expires on 2027-01-31."}),
    ("vendor:dataloom", "Vendor", "vendors/dataloom.md", {"name": "DataLoom Zrt.", "service": "managed archive storage", "renewal_date": "2027-04-30", "quote": "DataLoom Zrt. supplies managed archive storage for Project Atlas Archive. The agreement renews on 2027-04-30."}),
    ("vendor:safedesk", "Vendor", "vendors/safedesk.md", {"name": "SafeDesk Kft.", "service": "alert monitoring", "renewal_date": "2027-05-31", "quote": "SafeDesk Kft. supplies alert monitoring for Project Atlas and Project Beacon Lab. The agreement renews on 2027-05-31."}),
    ("vendor:clearid-audit", "Vendor", "vendors/clearid-audit.md", {"name": "ClearID Audit Kft.", "service": "terminal access audits", "expiry_date": "2027-02-28", "quote": "ClearID Audit Kft. supplies terminal access audits for Project Bridge North. The agreement expires on 2027-02-28."}),
    ("incident:atlas", "Incident", "incidents/atlas.md", {"name": "September 2026 API outage", "date": "2026-09-18", "duration_minutes": 42, "root_cause": "incorrect gateway routing rule introduced during deployment", "status": "closed", "quote": "On 2026-09-18, Project Atlas suffered an API outage lasting 42 minutes. The root cause was an incorrect gateway routing rule introduced during deployment. The incident is closed."}),
    ("incident:beacon", "Incident", "incidents/beacon.md", {"name": "August 2026 switch interruption", "date": "2026-08-25", "root_cause": "faulty firmware on a replacement network switch", "status": "closed", "quote": "On 2026-08-25, Project Beacon recorded intermittent office network disconnections. The root cause was faulty firmware on a replacement network switch. The incident is closed."}),
    ("incident:bridge", "Incident", "incidents/bridge.md", {"name": "October 2026 onboarding delays", "date": "2026-10-09", "affected_applications": 18, "root_cause": "repeated timeouts in the external identity verification service", "status": "closed", "quote": "On 2026-10-09, Project Bridge experienced onboarding delays affecting 18 applications. The root cause was repeated timeouts in the external identity verification service. The incident is closed."}),
    ("incident:atlas-archive", "Incident", "incidents/atlas-archive.md", {"name": "October 2026 manifest rejection", "date": "2026-10-27", "root_cause": "incompatible date format in the batch manifest", "status": "closed", "quote": "On 2026-10-27, Project Atlas Archive rejected a pilot document batch. The root cause was an incompatible date format in the batch manifest. The incident is closed."}),
    ("incident:bridge-north", "Incident", "incidents/bridge-north.md", {"name": "September 2026 training print queue", "date": "2026-09-30", "root_cause": "exhausted local print queue quota", "status": "closed", "quote": "On 2026-09-30, Project Bridge North could not print its training handover packs. The root cause was an exhausted local print queue quota. The incident is closed."}),
    ("incident:beacon-lab", "Incident", "incidents/beacon-lab.md", {"name": "October 2026 sandbox alert loop", "date": "2026-10-16", "root_cause": "duplicate alert subscription left enabled after a training exercise", "status": "closed", "quote": "On 2026-10-16, Project Beacon Lab generated repeated sandbox alerts. The root cause was a duplicate alert subscription left enabled after a training exercise. The incident is closed."}),
    ("policy:access", "Policy", "policies/access.md", {"name": "Temporary accounts", "max_initial_days": 30, "renewal_notice_days": 5, "quote": "IT approves the Temporary accounts policy. Temporary third-party accounts have a maximum initial validity of 30 days. Renewal requests must arrive 5 days before expiry."}),
    ("policy:data", "Policy", "policies/data.md", {"name": "Data retention", "confidential_retention_months": 24, "training_retention_months": 12, "quote": "Finance approves the Data retention policy. Confidential project files are retained for 24 months after project closure. Public training materials are kept for 12 months after withdrawal."}),
    ("policy:vendors", "Policy", "policies/vendors.md", {"name": "Supplier management", "risk_review": "once per year", "performance_review": "quarterly", "quote": "Procurement approves the Supplier management policy. Supplier risk is reviewed once per year and service performance is reviewed quarterly."}),
]

# start, relationship, end, source. Evidence comes from the stated business fact's quote.
RELATIONSHIPS = [
    ("company:helioworks", "HAS_DEPARTMENT", "department:it", "company.md"),
    ("company:helioworks", "HAS_DEPARTMENT", "department:hr", "company.md"),
    ("company:helioworks", "HAS_DEPARTMENT", "department:procurement", "company.md"),
    ("company:helioworks", "HAS_DEPARTMENT", "department:finance", "company.md"),
    ("company:helioworks", "HAS_DEPARTMENT", "department:operations", "company.md"),
    ("person:nora-varga", "WORKS_IN", "department:it", "people/roles.md"),
    ("person:tamas-fekete", "WORKS_IN", "department:hr", "people/roles.md"),
    ("person:reka-kiss", "WORKS_IN", "department:procurement", "people/roles.md"),
    ("person:bence-molnar", "WORKS_IN", "department:finance", "people/roles.md"),
    ("person:nora-varadi", "WORKS_IN", "department:operations", "people/roles.md"),
    ("person:peter-varga", "WORKS_IN", "department:finance", "people/roles.md"),
    ("person:miklos-fekete", "WORKS_IN", "department:operations", "people/roles.md"),
    ("person:nora-varga", "LEADS", "project:atlas", "projects/atlas.md"),
    ("person:reka-kiss", "LEADS", "project:beacon", "projects/beacon.md"),
    ("person:tamas-fekete", "LEADS", "project:bridge", "projects/bridge.md"),
    ("person:nora-varadi", "LEADS", "project:atlas-archive", "projects/atlas-archive.md"),
    ("person:peter-varga", "LEADS", "project:beacon-lab", "projects/beacon-lab.md"),
    ("person:miklos-fekete", "LEADS", "project:bridge-north", "projects/bridge-north.md"),
    ("vendor:novacloud", "SUPPLIES", "project:atlas", "vendors/novacloud.md"),
    ("vendor:greenwire", "SUPPLIES", "project:beacon", "vendors/greenwire.md"),
    ("vendor:greenwire", "SUPPLIES", "project:bridge-north", "vendors/greenwire.md"),
    ("vendor:clearid", "SUPPLIES", "project:bridge", "vendors/clearid.md"),
    ("vendor:dataloom", "SUPPLIES", "project:atlas-archive", "vendors/dataloom.md"),
    ("vendor:safedesk", "SUPPLIES", "project:atlas", "vendors/safedesk.md"),
    ("vendor:safedesk", "SUPPLIES", "project:beacon-lab", "vendors/safedesk.md"),
    ("vendor:clearid-audit", "SUPPLIES", "project:bridge-north", "vendors/clearid-audit.md"),
    ("incident:atlas", "AFFECTS", "project:atlas", "incidents/atlas.md"),
    ("incident:beacon", "AFFECTS", "project:beacon", "incidents/beacon.md"),
    ("incident:bridge", "AFFECTS", "project:bridge", "incidents/bridge.md"),
    ("incident:atlas-archive", "AFFECTS", "project:atlas-archive", "incidents/atlas-archive.md"),
    ("incident:bridge-north", "AFFECTS", "project:bridge-north", "incidents/bridge-north.md"),
    ("incident:beacon-lab", "AFFECTS", "project:beacon-lab", "incidents/beacon-lab.md"),
    ("department:it", "APPROVES", "policy:access", "policies/access.md"),
    ("department:finance", "APPROVES", "policy:data", "policies/data.md"),
    ("department:procurement", "APPROVES", "policy:vendors", "policies/vendors.md"),
    ("department:procurement", "OWNS_CONTRACT", "vendor:novacloud", "vendors/novacloud.md"),
]


def document_graph(documents: list, chunk_ids: list[str]) -> tuple[list[dict], list[dict]]:
    if len(documents) != len(chunk_ids):
        raise ValueError("Every chunk needs its original vector point id.")
    nodes, edges, by_source = {}, [], {}
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
    by_source = {}
    for document, chunk_id in zip(documents, chunk_ids):
        by_source.setdefault(document.metadata["source"], []).append((document.page_content, chunk_id))
    entities = {}
    for entity_id, label, source, properties in NODES:
        if entity_id in entities or label not in LABELS or source not in by_source:
            raise ValueError("Invalid seed entity or source.")
        evidence = []
        quote = " ".join(properties["quote"].split()).casefold()
        for content, chunk_id in by_source[source]:
            if quote in " ".join(content.split()).casefold():
                evidence.append(chunk_id)
        if not evidence:
            raise ValueError(f"No supporting chunk for {entity_id}.")
        node = {"id": entity_id, "label": label, "source_id": source, "chunk_ids": evidence, **properties}
        entities[entity_id] = node
        nodes.append(node)
        edges.append({"start": entity_id, "type": "SUPPORTED_BY", "end": "document:" + source,
                      "source_id": source, "quote": properties["quote"], "chunk_ids": evidence})
    for start, kind, end, source in RELATIONSHIPS:
        labels = (entities.get(start, {}).get("label"), entities.get(end, {}).get("label"))
        if kind not in RELATION_TYPES or labels != RELATION_TYPES[kind]:
            raise ValueError("Invalid seed relationship.")
        owner = end if kind in ("LEADS", "APPROVES", "OWNS_CONTRACT") else start
        evidence = entities[owner]
        if evidence["source_id"] != source:
            raise ValueError("Relationship evidence must belong to its stated source.")
        edges.append({"start": start, "type": kind, "end": end, "source_id": source,
                      "quote": evidence["quote"], "chunk_ids": evidence["chunk_ids"]})
    for node in nodes:
        node["dataset"] = DATASET
    seen = set()
    for edge in edges:
        edge["id"] = str(uuid5(NAMESPACE_URL, f'{DATASET}:{edge["start"]}:{edge["type"]}:{edge["end"]}'))
        edge["dataset"] = DATASET
        if edge["id"] in seen:
            raise ValueError("Duplicate seed relationship.")
        seen.add(edge["id"])
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
        raise SystemExit("Graph sync failed. Check Neo4j availability, seed evidence and configuration.") from None
    print(f'Graph synced: {counts["entities"]} entities, {counts["documents"]} documents, {counts["chunks"]} chunks, {counts["relationships"]} relationships.')
