import os
import unittest
from contextlib import ExitStack
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from zipfile import ZipFile

from fastapi.testclient import TestClient
from langchain_core.embeddings import Embeddings
from langchain_core.runnables import RunnableLambda
from openpyxl import Workbook
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from qdrant_client import QdrantClient, models

from app import main, rag, uploads

PROJECT = Path(__file__).resolve().parents[2]
TEXT = "Uploaded knowledge for testing."


def sample_files() -> dict[str, bytes]:
    word = BytesIO()
    with ZipFile(word, "w") as archive:
        archive.writestr("word/document.xml", f'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>{TEXT}</w:t></w:r></w:p></w:body></w:document>')
    excel = BytesIO()
    workbook = Workbook()
    workbook.active.title = "Knowledge"
    workbook.active.append(["Fact", "Count"])
    workbook.active.append([TEXT, 0])
    workbook.active.append(['="FORMULA_MUST_NOT_RUN"'])
    workbook.save(excel)
    workbook.close()
    pdf = BytesIO()
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 20 200 Td ({TEXT}) Tj ET".encode())
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(pdf)
    return {
        "notes.txt": ("\ufeff" + TEXT).encode("utf-8"), "notes.md": ("# Notes\n\n" + TEXT).encode(),
        "notes.pdf": pdf.getvalue(), "notes.docx": word.getvalue(), "notes.xlsx": excel.getvalue(),
        "notes.html": f'<html><body><script>DO_NOT_EXECUTE</script><p>{TEXT}</p><img src="https://example.invalid/image"></body></html>'.encode(),
    }


class FakeEmbeddings(Embeddings):
    def __init__(self):
        self.calls = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        vectors = []
        for text in texts:
            value = int(sha256(text.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
            vectors.append([1.0, value] + [0.0] * 1534)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.db = QdrantClient(":memory:")
        self.addCleanup(self.db.close)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(self.db, "close"))
        self.stack.enter_context(patch.object(uploads, "UPLOAD_DIR", self.root))
        self.stack.enter_context(patch.object(uploads, "client", return_value=self.db))
        self.stack.enter_context(patch.object(rag, "client", return_value=self.db))
        self.stack.enter_context(patch.object(uploads, "require_key"))
        self.stack.enter_context(patch.object(rag, "require_key"))
        self.stack.enter_context(patch.dict(os.environ, {"LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false"}))
        self.embeddings = FakeEmbeddings()
        self.stack.enter_context(patch.object(rag, "OpenAIEmbeddings", return_value=self.embeddings))
        self.stack.enter_context(patch.object(rag, "ChatOpenAI", return_value=RunnableLambda(lambda prompt: "Generated answer.")))
        self.client = TestClient(main.app)
        self.addCleanup(self.client.close)

    def test_all_six_formats_are_loaded_saved_and_indexed(self):
        for name, content in sample_files().items():
            with self.subTest(filename=name):
                response = self.client.post("/api/ingest/upload", files={"file": (name, content)})
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()
                self.assertFalse(result["unchanged"])
                self.assertEqual(result["filename"], name)
                self.assertEqual(result["document_id"], sha256(content).hexdigest())
                self.assertEqual((self.root / result["document_id"] / name).read_bytes(), content)
                scope = models.Filter(must=[models.FieldCondition(key="metadata.document_id", match=models.MatchValue(value=result["document_id"]))])
                points, _ = self.db.scroll(rag.COLLECTION, scroll_filter=scope)
                self.assertEqual(len(points), result["chunks"])
                for point in points:
                    self.assertIn(TEXT, point.payload["page_content"])
                    self.assertNotIn("DO_NOT_EXECUTE", point.payload["page_content"])
                    self.assertNotIn("FORMULA_MUST_NOT_RUN", point.payload["page_content"])
                    self.assertEqual(point.payload["metadata"]["source"], result["source"])
                    self.assertEqual(point.payload["metadata"]["kind"], "upload")

    def test_renamed_duplicate_preserves_source_and_skips_embeddings(self):
        first = uploads.upload_document("notes.md", TEXT.encode())
        calls = len(self.embeddings.calls)
        repeated = uploads.upload_document("renamed.txt", TEXT.encode())
        self.assertTrue(repeated["unchanged"])
        self.assertEqual(first["document_id"], repeated["document_id"])
        self.assertEqual(first["source"], repeated["source"])
        self.assertEqual(repeated["filename"], "notes.md")
        self.assertEqual(len(self.embeddings.calls), calls)
        self.assertEqual(self.db.count(rag.COLLECTION).count, first["chunks"])
        self.assertEqual(len(list((self.root / first["document_id"]).iterdir())), 1)

    def test_same_filename_with_different_content_has_distinct_sources(self):
        first = uploads.upload_document("notes.txt", b"First document")
        second = uploads.upload_document("notes.txt", b"Second document")
        self.assertNotEqual(first["document_id"], second["document_id"])
        self.assertNotEqual(first["source"], second["source"])
        self.assertEqual(self.db.count(rag.COLLECTION).count, 2)

    def test_filenames_cannot_escape_upload_directory(self):
        self.assertEqual(uploads.safe_filename("../../notes.txt"), "notes.txt")
        self.assertEqual(uploads.safe_filename("..\\..\\notes<script>.TXT"), "notesscript.txt")
        self.assertEqual(uploads.safe_filename("CON.txt"), "document_CON.txt")
        result = uploads.upload_document("../../notes.txt", TEXT.encode())
        self.assertEqual(result["source"], f'uploads/{result["document_id"]}/notes.txt')
        self.assertTrue((self.root / result["document_id"] / "notes.txt").is_file())

    def test_invalid_empty_and_mislabeled_files_are_rejected_without_embeddings(self):
        cases = [("run.exe", b"code"), ("empty.txt", b""), ("blank.md", b" \n"), ("binary.txt", b"text\x00binary"), ("wrong.txt", b"\xff"), ("wrong.pdf", b"not PDF"), ("wrong.docx", b"not DOCX"), ("wrong.xlsx", b"not XLSX")]
        for name, content in cases:
            with self.subTest(filename=name):
                response = self.client.post("/api/ingest/upload", files={"file": (name, content)})
                self.assertEqual(response.status_code, 400, response.text)
                self.assertIsInstance(response.json()["detail"], str)
        self.assertEqual(self.embeddings.calls, [])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_size_limit_returns_413_before_processing(self):
        with patch.object(main, "MAX_UPLOAD_BYTES", 8), patch.object(main, "upload_document") as process:
            response = self.client.post("/api/ingest/upload", files={"file": ("large.txt", b"123456789")})
        self.assertEqual(response.status_code, 413)
        process.assert_not_called()

    def test_index_failure_is_sanitized_and_manual_reupload_recovers(self):
        with patch.object(uploads, "store", side_effect=ValueError("private backend details")):
            response = self.client.post("/api/ingest/upload", files={"file": ("notes.txt", TEXT.encode())})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("private backend details", response.text)
        response = self.client.post("/api/ingest/upload", files={"file": ("notes.txt", TEXT.encode())})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["unchanged"])

    def test_partial_index_is_completed_without_reindexing_existing_chunks(self):
        content = ("Longer document content. " * 100).encode()
        def fail_after_first_chunk(documents, ids):
            rag.store(self.db).add_documents(documents=documents[:1], ids=ids[:1])
            raise RuntimeError("Interrupted")
        interrupted = Mock()
        interrupted.add_documents.side_effect = fail_after_first_chunk
        with patch.object(uploads, "store", return_value=interrupted):
            with self.assertRaises(RuntimeError):
                uploads.upload_document("long.txt", content)
        existing, _ = self.db.scroll(rag.COLLECTION)
        self.assertEqual(len(existing), 1)
        resumed = Mock(wraps=rag.store(self.db))
        with patch.object(uploads, "store", return_value=resumed):
            result = uploads.upload_document("long.txt", content)
        added_ids = resumed.add_documents.call_args.kwargs["ids"]
        self.assertNotIn(str(existing[0].id), added_ids)
        self.assertEqual(len(added_ids), result["chunks"] - 1)
        self.assertEqual(self.db.count(rag.COLLECTION).count, result["chunks"])

    def test_upload_only_corpus_can_be_chatted_but_not_evaluated_as_seed(self):
        uploads.upload_document("notes.txt", TEXT.encode())
        status = rag.corpus_status()
        self.assertTrue(status["ready"])
        self.assertFalse(status["seed_ready"])
        result = rag.answer(TEXT, 4)
        self.assertTrue(result["sources"][0]["source"].startswith("uploads/"))
        with self.assertRaises(ValueError):
            rag.answer(TEXT, 4, seed_only=True)

    def test_all_twelve_baseline_results_and_seed_points_survive_upload(self):
        self.stack.enter_context(patch.object(rag, "SEED_DIR", PROJECT / "data" / "seed"))
        rag.index_seed()
        before_points, _ = self.db.scroll(rag.COLLECTION, limit=100)
        before = {}
        for point in before_points:
            before[str(point.id)] = point.payload
        with patch.object(main, "Path", return_value=PROJECT / "evaluation" / "questions.json"):
            baseline = self.client.post("/api/evaluate").json()
            upload = uploads.upload_document("notes.txt", TEXT.encode())
            after = self.client.post("/api/evaluate", json={"seed_only": False}).json()
        self.assertEqual(baseline["summary"]["successful"], 12)
        self.assertEqual(after["summary"]["successful"], 12)
        self.assertEqual(baseline["summary"]["average_source_coverage"], after["summary"]["average_source_coverage"])
        for previous, current in zip(baseline["results"], after["results"]):
            self.assertEqual(previous["sources"], current["sources"])
            self.assertEqual(previous["answer"], current["answer"])
            self.assertEqual(previous["source_coverage"], current["source_coverage"])
            for source in current["sources"]:
                self.assertFalse(source["source"].startswith("uploads/"))
        points = self.db.retrieve(rag.COLLECTION, ids=list(before), with_payload=True)
        for point in points:
            self.assertEqual(point.payload, before[str(point.id)])
        chat = self.client.post("/api/chat", json={"question": TEXT, "top_k": 4}).json()
        self.assertIn(upload["source"], [source["source"] for source in chat["sources"]])


if __name__ == "__main__":
    unittest.main()
