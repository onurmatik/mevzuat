import json
import shutil
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib import admin, messages
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings, RequestFactory

from .admin import DocumentAdmin
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
                "resmi_gazete_tarihi": "2020-01-01",
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
                "resmi_gazete_tarihi": "2021-01-01",
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
                "resmi_gazete_tarihi": "2021-05-05",
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
        self.assertEqual(kwargs["max_num_results"], 10)
        expected_filters = {
            "type": "and",
            "filters": [
                {"type": "eq", "key": "type", "value": "kanun"},
                {"type": "gte", "key": "date", "value": "2020-01-01"},
                {"type": "lte", "key": "date", "value": "2020-12-31"},
            ],
        }
        self.assertEqual(kwargs["filters"], expected_filters)


class DocumentAdminActionErrorTest(TestCase):
    def setUp(self):
        self.request = RequestFactory().get("/")
        self.admin = DocumentAdmin(Document, admin.site)
        self.doc = Document.objects.create(
            title="Doc", metadata={"resmi_gazete_tarihi": "2020-01-01"}
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

    def test_fetch_original_shows_error(self):
        self._assert_error("fetch_original", "fetch_and_store_document")

    def test_convert_to_markdown_shows_error(self):
        self._assert_error("convert_to_markdown", "convert_pdf_to_markdown")

    def test_sync_with_vectorstore_shows_error(self):
        self._assert_error("sync_with_vectorstore", "sync_with_vectorstore")
