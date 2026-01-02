import json
import shutil
import tempfile
from types import SimpleNamespace
from unittest.mock import patch, PropertyMock

from django.contrib import admin, messages
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings, RequestFactory
from django.core.management import call_command

from .admin import (
    DocumentAdmin,
    MevzuatTertipFilter,
    HasEmbeddingFilter,
    TranslatedFilter,
    SummarizedFilter,
)
from .models import Document, DocumentType


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
        self.assertTrue(all(item["type"] == "kanun" for item in data))

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
        self.assertEqual(data[0]["type"], "kanun")
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
        DocumentType.objects.create(
            id=1,
            name="Kanun",
            slug="kanun",
            fetcher="MevzuatFetcher",
        )
        DocumentType.objects.create(id=2, name="Tüzük", slug="tuzuk", fetcher="MevzuatFetcher")

    def test_list_document_types(self):
        response = self.client.get("/api/documents/types")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [{"id": 1, "label": "Kanun"}, {"id": 2, "label": "Tüzük"}])








class DocumentAdminConfigTest(TestCase):
    def test_mevzuat_tertib_in_admin_lists(self):
        self.assertIn("mevzuat_tertip", DocumentAdmin.list_display)
        self.assertIn(MevzuatTertipFilter, DocumentAdmin.list_filter)
        self.assertIn("has_embedding", DocumentAdmin.list_display)
        self.assertIn(HasEmbeddingFilter, DocumentAdmin.list_filter)
        self.assertIn("is_translated", DocumentAdmin.list_display)
        self.assertIn(TranslatedFilter, DocumentAdmin.list_filter)
        self.assertIn("is_summarized", DocumentAdmin.list_display)
        self.assertIn(SummarizedFilter, DocumentAdmin.list_filter)


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
            with patch.object(Document, "convert_pdf_to_markdown", autospec=True) as mock_convert:
                call_command("download_documents")

        mock_fetch.assert_called_once_with(doc_missing)
        mock_convert.assert_called_once_with(doc_missing, overwrite=False)

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


class EmbeddingGenerationTest(TestCase):
    def setUp(self):
        self.doc = Document.objects.create(
            title="Test Doc",
            summary="Test Summary",
            markdown="Content " * 5000, # ~40k chars
            metadata={}
        )

    @patch("openai.OpenAI")
    def test_embedding_includes_title_and_summary(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_client.embeddings.create.return_value.data = [SimpleNamespace(embedding=[0.1] * 1536)]
        
        self.doc.generate_embedding()
        
        call_args = mock_client.embeddings.create.call_args
        sent_text = call_args.kwargs['input']
        
        self.assertIn("Title: Test Doc", sent_text)
        self.assertIn("Summary: Test Summary", sent_text)
        self.assertIn("Content", sent_text)

    @patch("openai.OpenAI")
    def test_embedding_retries_on_context_length_error(self, mock_openai):
        from openai import BadRequestError
        
        mock_client = mock_openai.return_value
        # Mock response to raise error first, then succeed
        mock_response = SimpleNamespace(request=SimpleNamespace(), status_code=400, headers={}) # Needed for exception constructor if it inspects response
        
        error = BadRequestError("This model's maximum context length is 8192 tokens...", response=mock_response, body=None)
        
        # Setup side effect: Raise error twice, then return success
        mock_client.embeddings.create.side_effect = [
            error,
            error, 
            SimpleNamespace(data=[SimpleNamespace(embedding=[0.1] * 1536)])
        ]
        
        self.doc.generate_embedding()
        
        # Should have been called 3 times
        self.assertEqual(mock_client.embeddings.create.call_count, 3)
        
        # Check that input length decreased
        calls = mock_client.embeddings.create.call_args_list
        len1 = len(calls[0].kwargs['input'])
        len2 = len(calls[1].kwargs['input'])
        len3 = len(calls[2].kwargs['input'])
        
        self.assertLess(len2, len1)
        self.assertLess(len3, len2)



