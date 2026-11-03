from contextlib import closing
from hashlib import sha256
from pathlib import Path
from threading import Lock
from uuid import NAMESPACE_URL, uuid5
from zipfile import ZipFile

from langchain_core.documents import Document
from langchain_community.document_loaders import BSHTMLLoader, Docx2txtLoader, PyPDFLoader, TextLoader
from openpyxl import load_workbook
from qdrant_client import models

from app.rag import COLLECTION, client, require_key, store, text_splitter

UPLOAD_DIR = Path("/app/data/uploads")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
UPLOAD_LOCK = Lock()


class UploadError(ValueError):
    pass


def safe_filename(filename: str) -> str:
    name = Path(filename.replace("\\", "/").rsplit("/", 1)[-1])
    suffix = name.suffix.lower()
    if suffix not in (".txt", ".md", ".pdf", ".docx", ".html", ".xlsx"):
        raise UploadError("Choose a TXT, MD, PDF, DOCX, HTML or XLSX document.")
    stem = ""
    for character in name.stem:
        if character.isalnum() or character in " ._-":
            stem += character
    stem = stem.strip(" .")[:80] or "document"
    reserved = stem.split(".", 1)[0].upper()
    if reserved in ("CON", "PRN", "AUX", "NUL") or (len(reserved) == 4 and reserved[:3] in ("COM", "LPT") and reserved[3] in "123456789"):
        stem = "document_" + stem
    return stem + suffix


def load_documents(path: Path) -> list[Document]:
    suffix = path.suffix.lower()
    if suffix in (".docx", ".xlsx"):
        with ZipFile(path) as archive:
            expanded_size = 0
            for entry in archive.infolist():
                expanded_size += entry.file_size
            required = "word/document.xml" if suffix == ".docx" else "xl/workbook.xml"
            if expanded_size > 50 * 1024 * 1024 or required not in archive.namelist():
                raise ValueError("Invalid or oversized document archive.")
    if suffix in (".txt", ".md"):
        return TextLoader(str(path), encoding="utf-8-sig").load()
    if suffix == ".pdf":
        with path.open("rb") as document:
            if document.read(5) != b"%PDF-":
                raise ValueError("Invalid PDF document.")
        return PyPDFLoader(str(path)).load()
    if suffix == ".docx":
        return Docx2txtLoader(str(path)).load()
    if suffix == ".html":
        return BSHTMLLoader(str(path), open_encoding="utf-8-sig", bs_kwargs={"features": "html.parser"}, get_text_separator="\n").load()
    if suffix == ".xlsx":
        documents = []
        with closing(load_workbook(path, read_only=True, data_only=True, keep_links=False)) as workbook:
            for sheet in workbook:
                lines = []
                for row in sheet.iter_rows(values_only=True):
                    values = []
                    for value in row:
                        values.append("" if value is None else str(value))
                    line = " | ".join(values)
                    if line.strip(" |"):
                        lines.append(line)
                if lines:
                    documents.append(Document(page_content=f"Sheet: {sheet.title}\n" + "\n".join(lines), metadata={"sheet": sheet.title}))
        return documents
    raise ValueError("Unsupported document format.")


def upload_document(filename: str, content: bytes) -> dict:
    name = safe_filename(filename)
    if not content:
        raise UploadError("The document is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise UploadError("The document exceeds the 10 MB limit.")
    document_id = sha256(content).hexdigest()

    with UPLOAD_LOCK:
        directory = UPLOAD_DIR / document_id
        directory.mkdir(parents=True, exist_ok=True)
        original = next(directory.iterdir(), None)
        path = original or directory / name
        if original is None:
            path.write_bytes(content)
        try:
            documents = text_splitter().split_documents(load_documents(path))
            if not documents:
                raise ValueError("No readable text.")
            for document in documents:
                if "\x00" in document.page_content:
                    raise ValueError("Binary content is not supported.")
        except Exception as exc:
            if original is None:
                path.unlink(missing_ok=True)
                directory.rmdir()
            raise UploadError("The document could not be read. Check its format and that it contains text.") from exc

        source = f"uploads/{document_id}/{path.name}"
        ids = []
        for index, document in enumerate(documents):
            document.metadata.update({"source": source, "document_id": document_id, "filename": path.name, "chunk": index, "kind": "upload"})
            digest = sha256(document.page_content.encode("utf-8")).hexdigest()
            ids.append(str(uuid5(NAMESPACE_URL, f"upload:{document_id}:{index}:{digest}")))

        with closing(client()) as db:
            exists = db.collection_exists(COLLECTION)
            previous = set()
            if exists:
                points = db.retrieve(collection_name=COLLECTION, ids=ids, with_payload=False, with_vectors=False)
                for point in points:
                    previous.add(str(point.id))
            missing = []
            missing_ids = []
            for document, point_id in zip(documents, ids):
                if point_id not in previous:
                    missing.append(document)
                    missing_ids.append(point_id)
            if missing:
                require_key()
                if not exists:
                    db.create_collection(COLLECTION, vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE))
                store(db).add_documents(documents=missing, ids=missing_ids)

        return {"filename": path.name, "document_id": document_id, "source": source, "chunks": len(documents), "unchanged": not missing}
