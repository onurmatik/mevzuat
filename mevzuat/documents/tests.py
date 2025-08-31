import json
import shutil
import tempfile
from types import SimpleNamespace
from unittest.mock import patch, PropertyMock

from django.contrib import admin, messages
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings, RequestFactory
from django.core.management import call_command

from .admin import DocumentAdmin, MevzuatTertibFilter
from .models import Document, DocumentType, VectorStore


class DocumentListAPITest(TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.tempdir)
        self.override.enable()

        type1 = DocumentType.objects.create(
            id=1, name="Kanun", fetcher="MevzuatFetcher"
        )
        type2 = DocumentType.objects.create(
            id=2, name="Tüzük", fetcher="MevzuatFetcher"
        )

        Document.objects.create(
            title="Law 1",
            type=type1,
            document=ContentFile(b"a", name="law1.pdf"),
            metadata={
                "mevzuat_tur": 1,
                "mevzuat_no": "1",
                "mevzuat_tertib": 1,
                "resmiGazeteTarihi": "01.01.2020",
            },
        )
        Document.objects.create(
            title="Law 2",
            type=type2,
            document=ContentFile(b"b", name="law2.pdf"),
            metadata={
                "mevzuat_tur": 2,
                "mevzuat_no": "2",
                "mevzuat_tertib": 1,
                "resmiGazeteTarihi": "01.01.2021",
            },
        )
        Document.objects.create(
            title="Law 3",
            type=type1,
            document=ContentFile(b"c", name="law3.pdf"),
            metadata={
                "mevzuat_tur": 1,
                "mevzuat_no": "3",
                "mevzuat_tertib": 1,
                "resmiGazeteTarihi": "05.05.2021",
            },
        )

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.tempdir)

    def test_filter_by_mevzuat_tur(self):
        response = self.client.get("/api/documents/list", {"type": 1})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertTrue(all(item["type"] == 1 for item in data))

    def test_filter_by_year(self):
        response = self.client.get("/api/documents/list", {"year": 2021})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertTrue(all(item["date"].startswith("2021") for item in data))

    def test_filter_by_both(self):
        response = self.client.get("/api/documents/list", {"type": 1, "year": 2021})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["type"], 1)
        self.assertTrue(data[0]["date"].startswith("2021"))

    def test_filter_by_month(self):
        response = self.client.get("/api/documents/list", {"year": 2021, "month": 1})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertTrue(all(item["date"].startswith("2021-01") for item in data))

    def test_filter_by_date(self):
        response = self.client.get("/api/documents/list", {"date": "2021-05-05"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["date"], "2021-05-05")

    def test_filter_by_date_range(self):
        params = {"start_date": "2020-01-01", "end_date": "2021-04-30"}
        response = self.client.get("/api/documents/list", params)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertTrue(all("2020-01-01" <= item["date"] <= "2021-04-30" for item in data))


class DocumentTypeAPITest(TestCase):
    def setUp(self):
        vs = VectorStore.objects.create(name="VS1", oai_vs_id="vs1")
        DocumentType.objects.create(
            id=1,
            name="Kanun",
            fetcher="MevzuatFetcher",
            vector_store=vs,
        )
        DocumentType.objects.create(id=2, name="Tüzük", fetcher="MevzuatFetcher")

    def test_list_document_types(self):
        response = self.client.get("/api/documents/types")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [{"id": 1, "label": "Kanun"}])


class VectorStoreSearchAPITest(TestCase):
    def setUp(self):
        self.vs = VectorStore.objects.create(name="VS1", oai_vs_id="vs1")

    @patch("mevzuat.documents.api.OpenAI")
    def test_search_with_filters(self, MockOpenAI):
        instance = MockOpenAI.return_value
        instance.vector_stores.search.return_value = {"data": []}

        payload = {
            "query": "term",
            "filters": {"type": "eq", "key": "type", "value": "blog"},
        }

        url = f"/api/documents/vector-stores/{self.vs.uuid}/search"
        response = self.client.post(
            url, data=json.dumps(payload), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        instance.vector_stores.search.assert_called_with(
            vector_store_id="vs1",
            query="term",
            filters={"type": "eq", "key": "type", "value": "blog"},
            max_num_results=10,
            ranking_options=None,
            rewrite_query=True,
        )


class DocumentSearchAPITest(TestCase):
    def setUp(self):
        self.vs1 = VectorStore.objects.create(name="VS1", oai_vs_id="vs1")
        self.vs2 = VectorStore.objects.create(name="VS2", oai_vs_id="vs2")
        DocumentType.objects.create(
            id=1,
            name="Kanun",
            slug="kanun",
            fetcher="MevzuatFetcher",
            vector_store=self.vs1,
        )
        DocumentType.objects.create(
            id=2,
            name="Tüzük",
            slug="tuzuk",
            fetcher="MevzuatFetcher",
            vector_store=self.vs2,
        )

    @patch("mevzuat.documents.api.OpenAI")
    def test_search_across_vector_stores(self, MockOpenAI):
        instance = MockOpenAI.return_value
        instance.vector_stores.search.return_value = SimpleNamespace(data=[])

        response = self.client.get("/api/documents/search", {"query": "term"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(instance.vector_stores.search.call_count, 2)

    @patch("mevzuat.documents.api.OpenAI")
    def test_search_with_filters(self, MockOpenAI):
        instance = MockOpenAI.return_value
        instance.vector_stores.search.return_value = SimpleNamespace(data=[])

        params = {
            "query": "term",
            "type": "kanun",
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
        }
        response = self.client.get("/api/documents/search", params)
        self.assertEqual(response.status_code, 200)

        instance.vector_stores.search.assert_called_once()
        args, kwargs = instance.vector_stores.search.call_args
        self.assertEqual(kwargs["vector_store_id"], "vs1")
        self.assertEqual(kwargs["query"], "term")
        self.assertEqual(kwargs["max_num_results"], 11)
        expected_filters = {
            "type": "and",
            "filters": [
                {"type": "eq", "key": "type", "value": "kanun"},
                {"type": "gte", "key": "date", "value": "2020-01-01"},
                {"type": "lte", "key": "date", "value": "2020-12-31"},
            ],
        }
        self.assertEqual(kwargs["filters"], expected_filters)

    @patch("mevzuat.documents.api.OpenAI")
    def test_search_pagination(self, MockOpenAI):
        instance = MockOpenAI.return_value
        item = SimpleNamespace(
            content=[SimpleNamespace(text="t", type="text")],
            filename="f",
            score=1.0,
            attributes={"type": "kanun"},
        )
        instance.vector_stores.search.return_value = SimpleNamespace(data=[item, item, item])

        response = self.client.get(
            "/api/documents/search", {"query": "term", "limit": 2, "type": "kanun"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["has_more"])

        response = self.client.get(
            "/api/documents/search",
            {"query": "term", "limit": 2, "offset": 2, "type": "kanun"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["has_more"])

        calls = instance.vector_stores.search.call_args_list
        self.assertEqual(calls[0].kwargs["max_num_results"], 3)
        self.assertEqual(calls[1].kwargs["max_num_results"], 5)


class DocumentAdminConfigTest(TestCase):
    def test_mevzuat_tertib_in_admin_lists(self):
        self.assertIn("mevzuat_tertib", DocumentAdmin.list_display)
        self.assertIn(MevzuatTertibFilter, DocumentAdmin.list_filter)


class FetchDocumentsCommandTest(TestCase):
    def test_fetches_only_missing_documents_for_active_types(self):
        active_type = DocumentType.objects.create(
            name="Active", fetcher="MevzuatFetcher", active=True
        )
        inactive_type = DocumentType.objects.create(
            name="Inactive", fetcher="MevzuatFetcher", active=False
        )

        doc_missing = Document.objects.create(
            title="Missing", type=active_type, metadata={}
        )
        Document.objects.create(
            title="Present",
            type=active_type,
            document=ContentFile(b"data", name="present.pdf"),
            metadata={"resmiGazeteTarihi": "01.01.2020"},
        )
        Document.objects.create(
            title="Inactive", type=inactive_type, metadata={}
        )

        with patch.object(Document, "fetch_and_store_document", autospec=True) as mock_fetch:
            call_command("fetch_documents")

        mock_fetch.assert_called_once_with(doc_missing)

class DocumentAdminActionErrorTest(TestCase):
    def setUp(self):
        self.request = RequestFactory().get("/")
        self.admin = DocumentAdmin(Document, admin.site)
        self.doc = Document.objects.create(
            title="Doc", metadata={"resmiGazeteTarihi": "01.01.2020"}
        )

    def _assert_error(self, action, method_name):
        with patch.object(Document, method_name, side_effect=Exception("boom")):
            with patch.object(self.admin, "message_user") as mock_msg:
                getattr(self.admin, action)(self.request, Document.objects.all())
                error_calls = [
                    c
                    for c in mock_msg.call_args_list
                    if c.kwargs.get("level") == messages.ERROR
                ]
                self.assertEqual(len(error_calls), 1)
                self.assertIn("boom", error_calls[0].args[1])

    def test_fetch_document_shows_error(self):
        self._assert_error("fetch_document", "fetch_and_store_document")

    def test_convert_to_markdown_shows_error(self):
        self._assert_error("convert_to_markdown", "convert_pdf_to_markdown")

    def test_sync_with_vectorstore_shows_error(self):
        self._assert_error("sync_with_vectorstore", "sync_with_vectorstore")


class DocumentSyncWithVectorStoreStorageTest(TestCase):
    def setUp(self):
        vs = VectorStore.objects.create(name="VS1", oai_vs_id="vs1")
        doc_type = DocumentType.objects.create(
            name="Kanun", fetcher="MevzuatFetcher", vector_store=vs
        )
        self.doc = Document.objects.create(
            title="Doc",
            type=doc_type,
            document=ContentFile(b"a", name="doc.pdf"),
            metadata={
                "mevzuat_tur": 1,
                "mevzuat_tertib": 1,
                "mevzuat_no": "1",
                "resmiGazeteTarihi": "01.01.2020",
            },
        )

    @patch("openai.OpenAI")
    def test_sync_uses_storage_open(self, MockOpenAI):
        client = MockOpenAI.return_value
        client.files.create.return_value = SimpleNamespace(id="file-123")
        client.vector_stores.files.create.return_value = None

        # Simulate a storage backend where ``.path`` is unsupported
        with patch.object(type(self.doc.document), "path", new_callable=PropertyMock, side_effect=NotImplementedError):
            with patch.object(self.doc.document, "open", wraps=self.doc.document.open) as mock_open:
                self.doc.sync_with_vectorstore()
                mock_open.assert_called_once_with("rb")

        self.assertEqual(self.doc.oai_file_id, "file-123")
        client.files.create.assert_called_once()
        file_arg = client.files.create.call_args.kwargs["file"]
        self.assertIsInstance(file_arg, tuple)
        self.assertTrue(file_arg[0].endswith(".pdf"))
        self.assertEqual(file_arg[1], b"a")
        client.vector_stores.files.create.assert_called_once()


class FetchNewCommandTest(TestCase):
    @patch("mevzuat.documents.management.commands.fetch_new.fetch_documents")
    def test_fetches_all_active_document_types(self, mock_fetch):
        mock_fetch.return_value = [
            {"mevzuatNo": "1"},
            {"mevzuatNo": "2"},
        ]
        dt_active1 = DocumentType.objects.create(name="Active 1", fetcher="KanunFetcher", active=True)
        dt_active2 = DocumentType.objects.create(name="Active 2", fetcher="KanunFetcher", active=True)
        dt_inactive = DocumentType.objects.create(name="Inactive", fetcher="KanunFetcher", active=False)

        call_command("fetch_new")

        self.assertEqual(mock_fetch.call_count, 2)
        self.assertEqual(Document.objects.filter(type=dt_active1).count(), 2)
        self.assertEqual(Document.objects.filter(type=dt_active2).count(), 2)
        self.assertEqual(Document.objects.filter(type=dt_inactive).count(), 0)


class SyncVectorstoreCommandTest(TestCase):
    @patch("mevzuat.documents.models.Document.sync_with_vectorstore", autospec=True)
    def test_syncs_unprocessed_active_documents(self, mock_sync):
        dt_active = DocumentType.objects.create(name="Active", fetcher="KanunFetcher", active=True)
        dt_inactive = DocumentType.objects.create(name="Inactive", fetcher="KanunFetcher", active=False)
        doc1 = Document.objects.create(title="Doc1", type=dt_active)
        doc2 = Document.objects.create(title="Doc2", type=dt_active, oai_file_id="")
        Document.objects.create(title="Doc3", type=dt_active, oai_file_id="file-1")
        Document.objects.create(title="Doc4", type=dt_inactive)

        call_command("sync_vectorstore")

        self.assertEqual(mock_sync.call_count, 2)
        called_pks = {call.args[0].pk for call in mock_sync.call_args_list}
        self.assertEqual(called_pks, {doc1.pk, doc2.pk})
