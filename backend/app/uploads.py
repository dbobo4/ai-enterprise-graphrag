from contextlib import closing
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import NAMESPACE_URL, uuid5
from zipfile import ZipFile

from langchain_core.documents import Document
from langchain_community.document_loaders import BSHTMLLoader, Docx2txtLoader, PyPDFLoader, TextLoader
from openpyxl import load_workbook
from qdrant_client import models
from typing_extensions import TypedDict

from app.graph_seed import sync_upload
from app.rag import client, ensure_collection, indexed_ids, store, text_splitter

UPLOAD_DIR = Path("/app/data/uploads")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class UploadResult(TypedDict):
    filename: str
    document_id: str
    source: str
    chunks: int
    unchanged: bool


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
        return load_sheets(path)
    raise ValueError("Unsupported document format.")


def load_sheets(path: Path) -> list[Document]:
    documents = []
    with closing(load_workbook(path, read_only=True, data_only=True, keep_links=False)) as workbook:
        for sheet in workbook:
            lines = []
            for row in sheet.iter_rows(values_only=True):
                line = " | ".join("" if value is None else str(value) for value in row)
                if line.strip(" |"):
                    lines.append(line)
            if lines:
                documents.append(Document(page_content=f"Sheet: {sheet.title}\n" + "\n".join(lines), metadata={"sheet": sheet.title}))
    return documents


def read_chunks(path: Path) -> list[Document]:
    try:
        documents = text_splitter().split_documents(load_documents(path))
        if not documents:
            raise ValueError("No readable text.")
        for document in documents:
            if "\x00" in document.page_content:
                raise ValueError("Binary content is not supported.")
        return documents
    except Exception as exc:
        raise UploadError("The document could not be read. Check its format and that it contains text.") from exc


def saved_upload(name: str, content: bytes, document_id: str) -> tuple[Path, list[Document]]:
    root = UPLOAD_DIR.resolve()
    root.mkdir(parents=True, exist_ok=True)
    directory = root / document_id
    try:
        original = next(directory.iterdir(), None)
    except FileNotFoundError:
        original = None
    if original is not None and original.read_bytes() == content:
        return original, read_chunks(original)

    # The complete file and its first accepted name become visible together.
    with TemporaryDirectory(prefix=".upload-", dir=root) as staging:
        temporary = Path(staging)
        path = temporary / (original.name if original else name)
        path.write_bytes(content)
        documents = read_chunks(path)
        if original is not None:
            path.replace(original)
            return original, documents
        try:
            # An empty directory can remain from an older upload interrupted before writing.
            directory.rmdir()
        except OSError:
            pass
        try:
            temporary.rename(directory)
        except OSError:
            try:
                winner = next(directory.iterdir(), None)
            except FileNotFoundError:
                winner = None
            if winner is None:
                raise
            if winner.read_bytes() != content:
                raise UploadError("The saved document is incomplete. Retry the same file.")
            return winner, read_chunks(winner)
        return directory / name, documents


def index_upload(documents: list[Document], ids: list[str]) -> bool:
    scope = models.Filter(must=[
        models.FieldCondition(key="metadata.kind", match=models.MatchValue(value="upload")),
        models.FieldCondition(key="metadata.document_id", match=models.MatchValue(value=documents[0].metadata["document_id"])),
    ])
    with closing(client()) as db:
        ensure_collection(db)
        existing = indexed_ids(db, scope)
        missing = []
        missing_ids = []
        for document, point_id in zip(documents, ids):
            if point_id not in existing:
                missing.append(document)
                missing_ids.append(point_id)
        obsolete = existing - set(ids)
        if missing or obsolete:
            vectors = store(db)
            if missing:
                vectors.add_documents(documents=missing, ids=missing_ids)
            if obsolete:
                vectors.delete(ids=sorted(obsolete))
        return bool(missing or obsolete)


def upload_document(filename: str, content: bytes) -> UploadResult:
    name = safe_filename(filename)
    if not content:
        raise UploadError("The document is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise UploadError("The document exceeds the 10 MB limit.")
    document_id = sha256(content).hexdigest()
    path, documents = saved_upload(name, content, document_id)
    source = f"uploads/{document_id}/{path.name}"
    ids: list[str] = []
    for index, document in enumerate(documents):
        document.metadata.update({"source": source, "document_id": document_id, "filename": path.name, "chunk": index, "kind": "upload"})
        digest = sha256(document.page_content.encode("utf-8")).hexdigest()
        ids.append(str(uuid5(NAMESPACE_URL, f"upload:{document_id}:{index}:{digest}")))

    vector_changed = index_upload(documents, ids)
    graph_changed = sync_upload(documents, ids)
    return {"filename": path.name, "document_id": document_id, "source": source, "chunks": len(documents),
            "unchanged": not vector_changed and not graph_changed}
