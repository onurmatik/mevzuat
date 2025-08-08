from datetime import date
import json
import shutil
import tempfile
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

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
            default_vector_store=vs,
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
