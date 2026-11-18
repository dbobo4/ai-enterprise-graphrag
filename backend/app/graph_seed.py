"""Reviewed HelioWorks facts. Sync: docker compose exec backend python -m app.graph_seed"""

from typing import TypedDict
from uuid import NAMESPACE_URL, uuid5

from langchain_core.documents import Document
from neo4j import ManagedTransaction, Session

from app.rag import seed_chunks

DATASET = "helioworks-seed-v1"
UPLOAD_DATASET = "uploads"
LABELS = {"Company", "Department", "Person", "Project", "Vendor", "Incident", "Policy"}
RELATION_TYPES = {
    "HAS_DEPARTMENT": ("Company", "Department"), "WORKS_IN": ("Person", "Department"),
    "LEADS": ("Person", "Project"), "SUPPLIES": ("Vendor", "Project"), "AFFECTS": ("Incident", "Project"),
    "APPROVES": ("Department", "Policy"), "OWNS_CONTRACT": ("Department", "Vendor"),
}

EDGE_ENDPOINTS = dict.fromkeys(RELATION_TYPES, ("Entity", "Entity")) | {
    "CONTAINS": ("Document", "Chunk"), "NEXT_CHUNK": ("Chunk", "Chunk"), "SUPPORTED_BY": ("Entity", "Document"),
}


class Evidence(TypedDict):
    source_id: str
    quote: str
    chunk_id: str


class Node(TypedDict):
    id: str
    label: str
    properties: dict[str, str | int | list[str]]


class Edge(TypedDict):
    id: str
    start: str
    type: str
    end: str
    properties: dict[str, str | int | list[str]]

# id, label, source, properties. Quotes identify actual supporting chunks, not whole documents.
NODES: list[tuple[str, str, str, dict[str, str | int]]] = [
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
    ("person:nora-varga", "Person", "emails/atlas-window.md", {"name": "Nóra Varga", "role": "systems engineering lead", "quote": "From: Nóra Varga, IT."}),
]

# start, relationship, end, source, exact quote
RELATIONSHIPS: list[tuple[str, str, str, str, str]] = [
    ("company:helioworks", "HAS_DEPARTMENT", "department:it", "company.md", "HelioWorks Kft. has five departments: IT, HR, Procurement, Finance and Operations."),
    ("company:helioworks", "HAS_DEPARTMENT", "department:hr", "company.md", "HelioWorks Kft. has five departments: IT, HR, Procurement, Finance and Operations."),
    ("company:helioworks", "HAS_DEPARTMENT", "department:procurement", "company.md", "HelioWorks Kft. has five departments: IT, HR, Procurement, Finance and Operations."),
    ("company:helioworks", "HAS_DEPARTMENT", "department:finance", "company.md", "HelioWorks Kft. has five departments: IT, HR, Procurement, Finance and Operations."),
    ("company:helioworks", "HAS_DEPARTMENT", "department:operations", "company.md", "HelioWorks Kft. has five departments: IT, HR, Procurement, Finance and Operations."),
    ("person:nora-varga", "WORKS_IN", "department:it", "people/roles.md", "Nóra Varga works in IT as a systems engineering lead."),
    ("person:tamas-fekete", "WORKS_IN", "department:hr", "people/roles.md", "Tamás Fekete works in HR as an onboarding process owner."),
    ("person:reka-kiss", "WORKS_IN", "department:procurement", "people/roles.md", "Réka Kiss works in Procurement as a supplier coordination lead."),
    ("person:bence-molnar", "WORKS_IN", "department:finance", "people/roles.md", "Bence Molnár works in Finance as a cost reporting owner."),
    ("person:nora-varadi", "WORKS_IN", "department:operations", "people/roles.md", "Nóra Váradi works in Operations as a records migration owner."),
    ("person:peter-varga", "WORKS_IN", "department:finance", "people/roles.md", "Péter Varga works in Finance as a financial controls analyst."),
    ("person:miklos-fekete", "WORKS_IN", "department:operations", "people/roles.md", "Miklós Fekete works in Operations as a warehouse process owner."),
    ("person:nora-varga", "LEADS", "project:atlas", "projects/atlas.md", "Nóra Varga leads Project Atlas, the internal support ticketing platform, with a target go-live of 2026-11-15."),
    ("person:reka-kiss", "LEADS", "project:beacon", "projects/beacon.md", "Réka Kiss leads Project Beacon, the office network renewal, with a target go-live of 2027-01-20."),
    ("person:tamas-fekete", "LEADS", "project:bridge", "projects/bridge.md", "Tamás Fekete leads Project Bridge, the employee onboarding service, with a target go-live of 2026-12-01."),
    ("person:nora-varadi", "LEADS", "project:atlas-archive", "projects/atlas-archive.md", "Nóra Váradi leads Project Atlas Archive, the records migration programme, with a target go-live of 2027-02-12."),
    ("person:peter-varga", "LEADS", "project:beacon-lab", "projects/beacon-lab.md", "Péter Varga leads Project Beacon Lab, the finance network sandbox, with a target go-live of 2026-12-15."),
    ("person:miklos-fekete", "LEADS", "project:bridge-north", "projects/bridge-north.md", "Miklós Fekete leads Project Bridge North, the warehouse onboarding programme, with a target go-live of 2027-01-11."),
    ("vendor:novacloud", "SUPPLIES", "project:atlas", "vendors/novacloud.md", "NovaCloud Ltd. supplies managed API gateway hosting for Project Atlas."),
    ("vendor:greenwire", "SUPPLIES", "project:beacon", "vendors/greenwire.md", "GreenWire Zrt. supplies network switches and equipment maintenance for Project Beacon and Project Bridge North."),
    ("vendor:greenwire", "SUPPLIES", "project:bridge-north", "vendors/greenwire.md", "GreenWire Zrt. supplies network switches and equipment maintenance for Project Beacon and Project Bridge North."),
    ("vendor:clearid", "SUPPLIES", "project:bridge", "vendors/clearid.md", "ClearID Kft. provides identity and document verification for Project Bridge."),
    ("vendor:dataloom", "SUPPLIES", "project:atlas-archive", "vendors/dataloom.md", "DataLoom Zrt. supplies managed archive storage for Project Atlas Archive."),
    ("vendor:safedesk", "SUPPLIES", "project:atlas", "vendors/safedesk.md", "SafeDesk Kft. supplies alert monitoring for Project Atlas and Project Beacon Lab."),
    ("vendor:safedesk", "SUPPLIES", "project:beacon-lab", "vendors/safedesk.md", "SafeDesk Kft. supplies alert monitoring for Project Atlas and Project Beacon Lab."),
    ("vendor:clearid-audit", "SUPPLIES", "project:bridge-north", "vendors/clearid-audit.md", "ClearID Audit Kft. supplies terminal access audits for Project Bridge North."),
    ("incident:atlas", "AFFECTS", "project:atlas", "incidents/atlas.md", "On 2026-09-18, Project Atlas suffered an API outage lasting 42 minutes."),
    ("incident:beacon", "AFFECTS", "project:beacon", "incidents/beacon.md", "On 2026-08-25, Project Beacon recorded intermittent office network disconnections."),
    ("incident:bridge", "AFFECTS", "project:bridge", "incidents/bridge.md", "On 2026-10-09, Project Bridge experienced onboarding delays affecting 18 applications."),
    ("incident:atlas-archive", "AFFECTS", "project:atlas-archive", "incidents/atlas-archive.md", "On 2026-10-27, Project Atlas Archive rejected a pilot document batch."),
    ("incident:bridge-north", "AFFECTS", "project:bridge-north", "incidents/bridge-north.md", "On 2026-09-30, Project Bridge North could not print its training handover packs."),
    ("incident:beacon-lab", "AFFECTS", "project:beacon-lab", "incidents/beacon-lab.md", "On 2026-10-16, Project Beacon Lab generated repeated sandbox alerts."),
    ("department:it", "APPROVES", "policy:access", "policies/access.md", "IT approves the Temporary accounts policy."),
    ("department:finance", "APPROVES", "policy:data", "policies/data.md", "Finance approves the Data retention policy."),
    ("department:procurement", "APPROVES", "policy:vendors", "policies/vendors.md", "Procurement approves the Supplier management policy."),
    ("department:procurement", "OWNS_CONTRACT", "vendor:novacloud", "vendors/novacloud.md", "NovaCloud Ltd. supplies managed API gateway hosting for Project Atlas. The agreement renews on 2027-03-01 and Procurement owns the contract."),
    ("person:nora-varga", "WORKS_IN", "department:it", "emails/atlas-window.md", "From: Nóra Varga, IT."),
]


def edge_record(start: str, kind: str, end: str, dataset: str, source: str) -> Edge:
    edge_id = str(uuid5(NAMESPACE_URL, f"{dataset}:{start}:{kind}:{end}"))
    return {"id": edge_id, "start": start, "type": kind, "end": end,
            "properties": {"id": edge_id, "dataset": dataset, "source_id": source}}


def document_graph(documents: list[Document], chunk_ids: list[str], dataset: str = DATASET) -> tuple[list[Node], list[Edge]]:
    if len(documents) != len(chunk_ids):
        raise ValueError("Every chunk needs its original vector point id.")
    nodes: dict[str, Node] = {}
    edges: list[Edge] = []
    sequences: dict[str, list[tuple[int, str]]] = {}
    for document, chunk_id in zip(documents, chunk_ids):
        metadata = document.metadata
        source, index = metadata["source"], metadata["chunk"]
        doc_id = "document:" + (f'upload:{metadata["document_id"]}' if dataset == UPLOAD_DATASET else source)
        if chunk_id in nodes or not isinstance(index, int) or index < 0 or not document.page_content.strip():
            raise ValueError("Invalid or duplicate chunk.")
        common = {"dataset": dataset, "source_id": source, "source": source, "document_id": metadata["document_id"]}
        if doc_id not in nodes:
            properties = {**common, "id": doc_id}
            for field in ("filename", "title", "total_pages", "author", "subject", "creator", "producer",
                          "creationdate", "moddate", "keywords", "format", "trapped"):
                if isinstance(metadata.get(field), (str, int)):
                    properties[field] = metadata[field]
            nodes[doc_id] = {"id": doc_id, "label": "Document", "properties": properties}
        row = {**common, "id": chunk_id, "chunk": index, "text": document.page_content}
        for field in ("page", "page_label", "section", "sheet"):
            if isinstance(metadata.get(field), (str, int)):
                row[field] = metadata[field]
        nodes[chunk_id] = {"id": chunk_id, "label": "Chunk", "properties": row}
        edges.append(edge_record(doc_id, "CONTAINS", chunk_id, dataset, source))
        sequences.setdefault(source, []).append((index, chunk_id))
    for source, chunks in sequences.items():
        chunks.sort()
        for position, (index, chunk_id) in enumerate(chunks):
            if index != position:
                raise ValueError("Chunk numbers must start at zero and be consecutive.")
            if position > 0:
                edges.append(edge_record(chunks[position - 1][1], "NEXT_CHUNK", chunk_id, dataset, source))
    return list(nodes.values()), edges


def resolve_evidence(source: str, quote: str, chunks: dict[str, list[tuple[str, str]]]) -> list[Evidence]:
    evidence: list[Evidence] = []
    if quote.strip():
        for text, chunk_id in chunks.get(source, []):
            if quote in text:
                evidence.append({"source_id": source, "quote": quote, "chunk_id": chunk_id})
    if not evidence:
        raise ValueError(f"No exact supporting chunk in {source}: {quote}")
    return evidence


def set_evidence(record: Node | Edge, evidence: list[Evidence]) -> None:
    properties = record["properties"]
    # Aligned lists store each original source/quote/chunk tuple in Neo4j properties.
    properties["evidence_sources"] = [item["source_id"] for item in evidence]
    properties["quotes"] = [item["quote"] for item in evidence]
    properties["chunk_ids"] = [item["chunk_id"] for item in evidence]
    properties["source_id"] = evidence[0]["source_id"]
    properties["quote"] = evidence[0]["quote"]


def seed_graph() -> tuple[list[Node], list[Edge]]:
    documents, chunk_ids = seed_chunks()
    nodes, edges = document_graph(documents, chunk_ids)
    chunks: dict[str, list[tuple[str, str]]] = {}
    for document, chunk_id in zip(documents, chunk_ids):
        chunks.setdefault(document.metadata["source"], []).append((document.page_content, chunk_id))

    entities: dict[str, Node] = {}
    records: dict[str, Edge] = {}
    proofs: dict[str, list[Evidence]] = {}
    descriptions: dict[str, list[str]] = {}
    for entity_id, label, source, declared in NODES:
        if label not in LABELS:
            raise ValueError(f"Unknown entity label: {label}.")
        attributes = dict(declared)
        quote = str(attributes.pop("quote"))
        name = str(attributes["name"])
        detail = attributes.get("purpose") or attributes.get("role") or attributes.get("service") or attributes.get("root_cause")
        description = str(attributes.pop("description", f"{name}: {detail}" if detail else f"{name} ({label.lower()})"))
        variants = descriptions.setdefault(entity_id, [])
        if description not in variants:
            variants.append(description)
        node = entities.setdefault(entity_id, {"id": entity_id, "label": label, "properties": {"id": entity_id, "dataset": DATASET}})
        if node["label"] != label:
            raise ValueError(f"Conflicting labels for {entity_id}.")
        properties = node["properties"]
        for key, value in attributes.items():
            if key in properties and properties[key] != value:
                raise ValueError(f"Conflicting {key} for {entity_id}.")
            properties[key] = value
        evidence = resolve_evidence(source, quote, chunks)
        support = edge_record(entity_id, "SUPPORTED_BY", "document:" + source, DATASET, source)
        records[support["id"]] = support
        for identity in (entity_id, support["id"]):
            saved = proofs.setdefault(identity, [])
            for item in evidence:
                if item not in saved:
                    saved.append(item)

    for start, kind, end, source, quote in RELATIONSHIPS:
        if kind not in RELATION_TYPES or start not in entities or end not in entities:
            raise ValueError(f"Invalid business relationship: {start} {kind} {end}.")
        if (entities[start]["label"], entities[end]["label"]) != RELATION_TYPES[kind]:
            raise ValueError(f"Incompatible relationship endpoints: {start} {kind} {end}.")
        edge = edge_record(start, kind, end, DATASET, source)
        records[edge["id"]] = edge
        saved = proofs.setdefault(edge["id"], [])
        for item in resolve_evidence(source, quote, chunks):
            if item not in saved:
                saved.append(item)

    for entity_id, node in entities.items():
        node["properties"]["description"] = "; ".join(descriptions[entity_id])
        set_evidence(node, proofs[entity_id])
        nodes.append(node)
    for edge in records.values():
        set_evidence(edge, proofs[edge["id"]])
        edges.append(edge)
    return nodes, edges


def write_graph(tx: ManagedTransaction, nodes: list[Node], edges: list[Edge], dataset: str) -> int:
    node_groups: dict[str, list[Node]] = {}
    edge_groups: dict[str, list[Edge]] = {}
    for node in nodes:
        if node["label"] not in LABELS | {"Document", "Chunk"} or node["properties"]["dataset"] != dataset:
            raise ValueError("Invalid node label or dataset.")
        node_groups.setdefault(node["label"], []).append(node)
    for edge in edges:
        if edge["type"] not in EDGE_ENDPOINTS or edge["properties"]["dataset"] != dataset:
            raise ValueError("Invalid relationship type or dataset.")
        edge_groups.setdefault(edge["type"], []).append(edge)

    created = 0
    # Write the Document first to serialize relationship MERGEs for concurrent uploads of that document.
    for label in ("Document", "Chunk", *sorted(LABELS)):
        if label not in node_groups:
            continue
        base = label if label in ("Document", "Chunk") else "Entity"
        query = f"UNWIND $rows AS row MERGE (n:{base} {{id: row.id}}) SET n:{label} SET n = row.properties"
        created += tx.run(query, rows=node_groups[label]).consume().counters.nodes_created
    for kind, rows in edge_groups.items():
        start, end = EDGE_ENDPOINTS[kind]
        query = (
            f"UNWIND $rows AS row MATCH (a:{start} {{id: row.start, dataset: $dataset}}), "
            f"(b:{end} {{id: row.end, dataset: $dataset}}) "
            f"MERGE (a)-[r:{kind} {{id: row.id}}]->(b) SET r = row.properties"
        )
        created += tx.run(query, rows=rows, dataset=dataset).consume().counters.relationships_created
    return created


def write_seed(tx: ManagedTransaction, nodes: list[Node], edges: list[Edge]) -> None:
    write_graph(tx, nodes, edges, DATASET)
    node_ids = [node["id"] for node in nodes]
    edge_ids = [edge["id"] for edge in edges]
    tx.run("MATCH ()-[r]->() WHERE r.dataset = $dataset AND NOT r.id IN $ids DELETE r", dataset=DATASET, ids=edge_ids).consume()
    tx.run("MATCH (n) WHERE n.dataset = $dataset AND NOT n.id IN $ids DETACH DELETE n", dataset=DATASET, ids=node_ids).consume()


def ensure_constraints(session: Session) -> None:
    for label in ("Entity", "Document", "Chunk"):
        session.run(f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE").consume()


def write_upload(tx: ManagedTransaction, nodes: list[Node], edges: list[Edge], ids: list[str]) -> bool:
    created = write_graph(tx, nodes, edges, UPLOAD_DATASET)
    obsolete = tx.run(
        "MATCH (d:Document {id: $id, dataset: $dataset})-[:CONTAINS]->(c:Chunk {dataset: $dataset}) "
        "WHERE NOT c.id IN $ids DETACH DELETE c",
        id=nodes[0]["id"], dataset=UPLOAD_DATASET, ids=ids,
    ).consume().counters.nodes_deleted
    return bool(created or obsolete)


def sync_upload(documents: list[Document], ids: list[str]) -> bool:
    from app.graph import graph_driver, graph_session

    nodes, edges = document_graph(documents, ids, UPLOAD_DATASET)
    with graph_driver() as driver, graph_session(driver) as session:
        ensure_constraints(session)
        return session.execute_write(write_upload, nodes, edges, ids)


def sync_seed() -> dict[str, int]:
    from app.graph import graph_driver, graph_session

    nodes, edges = seed_graph()
    with graph_driver() as driver, graph_session(driver) as session:
        ensure_constraints(session)
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
