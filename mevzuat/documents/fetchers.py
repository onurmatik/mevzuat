import abc
import os
import tempfile
from typing import Optional, Type
from datetime import datetime
import requests
from django.core.files.base import ContentFile
from django.db import transaction, models
from django.db.models import F


class BaseDocFetcher(abc.ABC):
    """Common interface for every fetcher."""
    @abc.abstractmethod
    def build_document_url(self, doc) -> str: ...

    @abc.abstractmethod
    def extract_metadata(self, doc) -> dict: ...

    @abc.abstractmethod
    def fetch_and_store_document(
            self,
            doc: "Document",
            *,
            overwrite: bool = False,
            timeout: int = 30
    ) -> models.FileField: ...

    def convert_pdf_to_markdown(
            self,
            doc: "Document",
            *,
            overwrite: bool = False,
            force_ocr: bool = False,
    ) -> str:
        """Convert the stored PDF into Markdown and persist it.

        Parameters
        ----------
        overwrite : bool, default False
            If ``False`` and ``self.markdown`` already exists, do nothing.
        force_ocr : bool, default False
            If ``True`` the conversion pipeline runs OCR on every page even when
            embedded text exists. Useful when PDFs have poor text layers.

        Returns
        -------
        str
            The stored ``markdown`` text.

        Raises
        ------
        ValueError
            If ``self.document`` is empty.
        """

        from docling.document_converter import DocumentConverter

        success_status = getattr(doc, "MARKDOWN_STATUS_SUCCESS", "success")
        if doc.markdown and not overwrite:
            if not doc.markdown_status:
                doc.markdown_status = success_status
                doc.save(update_fields=["markdown_status"])
            return doc.markdown

        if not doc.document:
            raise ValueError("No document available to convert")

        converter_kwargs = {}
        if force_ocr:
            from docling.datamodel.base_models import InputFormat
            from docling.document_converter import PdfFormatOption
            from docling.datamodel.pipeline_options import OcrAutoOptions
            from docling.pipeline.standard_pdf_pipeline import ThreadedPdfPipelineOptions

            pipeline_options = ThreadedPdfPipelineOptions(
                ocr_options=OcrAutoOptions(
                    force_full_page_ocr=True,
                    lang=["tur"],
                )
            )
            converter_kwargs["format_options"] = {
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }

        converter = DocumentConverter(**converter_kwargs)
        doc.document.open("rb")
        try:
            pdf_bytes = doc.document.read()
        finally:
            doc.document.close()

        file_size_updated = False
        if getattr(doc, "file_size", None) is None:
            doc.file_size = len(pdf_bytes)
            file_size_updated = True

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        result = None
        try:
            result = converter.convert(tmp_path)
            markdown_text = result.document.export_to_markdown()
        finally:
            # Ensure temp file is removed and PDF resources are freed even if conversion fails
            os.remove(tmp_path)
            self._cleanup_conversion(result)

        with transaction.atomic():
            doc.markdown = markdown_text
            doc.markdown_status = success_status
            fields = ["markdown", "markdown_status"]
            if file_size_updated:
                fields.append("file_size")
            doc.save(update_fields=fields)

        return doc.markdown

    def sync_with_vectorstore(self, doc):
        """Synchronise the document with the configured OpenAI vector store.

        If the document was never uploaded before a new OpenAI file is
        created and attached to the vector store. When the document already
        has an ``oai_file_id`` only its attributes are updated.

        Returns
        -------
        str
            The OpenAI file id associated with the document.

        Raises
        ------
        ValueError
            If ``self.document`` is empty.
        """
        if not doc.document:
            raise ValueError("No document available to upload")

        # Import lazily so openai is only required when this method is used.
        from openai import OpenAI

        client = OpenAI()

        # Build the attributes
        attributes = {
            "title": doc.title[:250],
            "date": doc.date.strftime("%Y-%m-%d"),
            "type": doc.type.slug,
        }

        vector_store_id = doc.get_vectorstore_id()

        if doc.oai_file_id:
            # Update only the attributes on the existing file
            client.vector_stores.files.update(
                vector_store_id=vector_store_id,
                file_id=doc.oai_file_id,
                attributes=attributes,
            )
            return doc.oai_file_id

        # Upload the file to OpenAI first.  Avoid using ``.path`` because
        # remote storage backends (e.g. S3) do not provide an absolute path.
        doc.document.open("rb")
        try:
            file_tuple = (os.path.basename(doc.document.name), doc.document.read())
        finally:
            doc.document.close()

        file_size_updated = False
        if getattr(doc, "file_size", None) is None:
            doc.file_size = len(file_tuple[1])
            file_size_updated = True

        uploaded_file = client.files.create(
            file=file_tuple, purpose="user_data"
        )

        doc.oai_file_id = uploaded_file.id
        fields = ["oai_file_id"]
        if file_size_updated:
            fields.append("file_size")
        doc.save(update_fields=fields)

        # Attach the uploaded file to the vector store
        client.vector_stores.files.create(
            vector_store_id=vector_store_id,
            file_id=uploaded_file.id,
            attributes=attributes,
        )

        return uploaded_file.id

    def _cleanup_conversion(self, result: Optional[object]) -> None:
        """Release docling/pypdfium resources eagerly to avoid shutdown warnings."""
        if result is None:
            return

        for page in getattr(result, "pages", []) or []:
            backend = getattr(page, "_backend", None)
            if backend is not None:
                try:
                    backend.unload()
                except Exception:
                    pass
                else:
                    page._backend = None

        input_obj = getattr(result, "input", None)
        input_backend = getattr(input_obj, "_backend", None)
        if input_backend is not None and getattr(input_backend, "_pdoc", None):
            try:
                input_backend.unload()
            except Exception:
                pass
            else:
                input_obj._backend = None


_registry: dict[str, BaseDocFetcher] = {}


def register(cls: Type[BaseDocFetcher]) -> Type[BaseDocFetcher]:
    """Decorator: instantiate the class and store it by its *class name*."""
    if not issubclass(cls, BaseDocFetcher):
        raise TypeError(f"{cls} does not subclass BaseDocFetcher")

    key = cls.__name__                 # e.g. "MevzuatFetcher"
    if key in _registry:
        raise RuntimeError(f"Fetcher {key!r} already registered")
    _registry[key] = cls()

    return cls


def get(name: str) -> BaseDocFetcher:
    try:
        return _registry[name]
    except KeyError:
        raise KeyError(f"Fetcher not found: {name}") from None


@register
class MevzuatFetcher(BaseDocFetcher):
    mevzuat_tur = 1  # Defaults to Kanun; child classes override

    def build_document_url(self, doc):
        uri = f"{doc.metadata['mevzuatTur']}.{doc.metadata['mevzuatTertip']}.{doc.metadata['mevzuatNo']}.pdf"
        return f"https://www.mevzuat.gov.tr/MevzuatMetin/{uri}"

    def get_document_date(self, doc):
        return datetime.strptime(doc.metadata['resmiGazeteTarihi'], '%d.%m.%Y').date()

    def fetch_and_store_document(self, doc, *, overwrite: bool = False, timeout: int = 30) -> "models.FileField":
        """
        Download the PDF at ``self.build_document_url()`` and save it into
        ``self.document``.

        Parameters
        ----------
        overwrite : bool, default False
            If ``False`` and ``self.document`` already exists, do nothing.
        timeout : int, default 30
            Seconds to wait for the HTTP response.

        Returns
        -------
        django.db.models.fields.files.FieldFile
            The stored ``document`` field (convenient to access ``.url``, ``.path``).

        Raises
        ------
        requests.RequestException
            On any network / HTTP error. Callers can catch and handle.
        """

        # Skip unless we need to fetch (honouring the overwrite flag)
        if doc.document and not overwrite:
            return doc.document

        pdf_url = self.build_document_url(doc)
        if not pdf_url:
            raise ValueError("build_document_url() returned an empty URL")

        default_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.mevzuat.gov.tr/",
            "Connection": "keep-alive",
        }

        response = requests.get(pdf_url, headers=default_headers, timeout=timeout)
        response.raise_for_status()  # will raise if status ≥ 400

        filename = f"{doc.uuid}.pdf"
        file_size = len(response.content)

        # Save inside a transaction so the DB row and the file write stay in sync
        with transaction.atomic():
            doc.document.save(filename, ContentFile(response.content), save=False)
            doc.file_size = file_size
            doc.save(update_fields=["document", "file_size"])

        return doc.document

    def extract_metadata(self, doc):
        pass


@register
class KanunFetcher(MevzuatFetcher):
    mevzuat_tur = 1
    request_params = {
        "MevzuatTur": "Kanun",
        "YonetmelikMevzuatTur": "OsmanliKanunu",
        "AranacakIfade": "",
        "AranacakYer": "2",
        "MevzuatNo": "",
        "BaslangicTarihi": "",
        "BitisTarihi": "",
    }


@register
class KHKFetcher(MevzuatFetcher):
    mevzuat_tur = 4
    request_params = {
        "MevzuatTur": "KHK",
        "YonetmelikMevzuatTur": "OsmanliKanunu",
        "AranacakIfade": "",
        "AranacakYer": "2",
        "MevzuatNo": "",
        "BaslangicTarihi": "",
        "BitisTarihi": "",
    }


@register
class CBKararnameFetcher(MevzuatFetcher):
    mevzuat_tur = 19
    request_params = {
        "MevzuatTur": "CumhurbaskaniKararnameleri",
        "YonetmelikMevzuatTur": "OsmanliKanunu",
        "AranacakIfade": "",
        "AranacakYer": "2",
        "MevzuatNo": "",
        "BaslangicTarihi": "",
        "BitisTarihi": "",
    }


@register
class CBKararFetcher(MevzuatFetcher):
    mevzuat_tur = 20
    request_params = {
        "MevzuatTur": "CumhurbaskaniKararlari",
        "YonetmelikMevzuatTur": "OsmanliKanunu",
        "AranacakIfade": "",
        "AranacakYer": "2",
        "MevzuatNo": "",
        "BaslangicTarihi": "",
        "BitisTarihi": "",
    }


@register
class CBYonetmelikFetcher(MevzuatFetcher):
    request_params = {
        "MevzuatTur": "CumhurbaskanligiVeBakanlarKuruluYonetmelik",
        "YonetmelikMevzuatTur": "CumhurbaskanligiVeBakanlarKuruluYonetmelik",
        "AranacakIfade": "",
        "AranacakYer": "2",
        "MevzuatNo": "",
        "BaslangicTarihi": "",
        "BitisTarihi": "",
    }
    mevzuat_tur = 21


@register
class CBGenelgeFetcher(MevzuatFetcher):
    mevzuat_tur = 22
    request_params = {
        "MevzuatTur": "CumhurbaskanligiGenelgeleri",
        "YonetmelikMevzuatTur": "OsmanliKanunu",
        "AranacakIfade": "",
        "AranacakYer": "Baslik",
        "MevzuatNo": "",
        "BaslangicTarihi": "",
        "BitisTarihi": "",
    }

    def build_document_url(self, doc):
        uri = f"CumhurbaskanligiGenelgeleri/{doc.date.strftime('%Y%m%d')}-{doc.metadata['mevzuatNo']}.pdf"
        return f"https://www.mevzuat.gov.tr/MevzuatMetin/{uri}"

    def get_document_date(self, doc):
        return datetime.strptime(doc.metadata['resmiGazeteTarihi'], '%d/%m/%Y').date()


@register
class YonetmelikFetcher(MevzuatFetcher):
    # For mevzuat_tur;
    #  - 7: Kurum Yönetmeliği
    #  - 8: Kurum Yönetmeliği (Üniversite)
    #  - 9: Tebliğ

    def build_document_url(self, doc):
        uri = f"yonetmelik/{doc.metadata['mevzuat_tur']}.{doc.metadata['mevzuat_tertib']}.{doc.metadata['mevzuat_no']}.pdf"
        return f"https://www.mevzuat.gov.tr/MevzuatMetin/{uri}"
