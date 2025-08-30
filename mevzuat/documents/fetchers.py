import abc
import os
from typing import Type
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
    def get_last_document(self) -> "Document": ...

    @abc.abstractmethod
    def fetch_and_store_document(
            self,
            doc: "Document",
            *,
            overwrite: bool = False,
            timeout: int = 30
    ) -> models.FileField: ...

    def convert_pdf_to_markdown(self, doc: "Document", *, overwrite: bool = False) -> "models.FileField":
        """Convert the stored PDF into Markdown and persist it.

        Parameters
        ----------
        overwrite : bool, default False
            If ``False`` and ``self.markdown`` already exists, do nothing.

        Returns
        -------
        django.db.models.fields.files.FieldFile
            The stored ``markdown`` field.

        Raises
        ------
        ValueError
            If ``self.document`` is empty.
        """

        from docling.document_converter import DocumentConverter

        if doc.markdown and not overwrite:
            return doc.markdown

        if not doc.document:
            raise ValueError("No document available to convert")

        converter = DocumentConverter()
        result = converter.convert(doc.document.path)
        markdown_text = result.document.export_to_markdown()

        filename = f"{doc.uuid}.md"

        with transaction.atomic():
            doc.markdown.save(filename, ContentFile(markdown_text), save=False)
            doc.save(update_fields=["markdown"])

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
        attributes.update(doc.metadata)

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

        uploaded_file = client.files.create(
            file=file_tuple, purpose="user_data"
        )

        doc.oai_file_id = uploaded_file.id
        doc.save(update_fields=["oai_file_id"])

        # Attach the uploaded file to the vector store
        client.vector_stores.files.create(
            vector_store_id=vector_store_id,
            file_id=uploaded_file.id,
            attributes=attributes,
        )

        return uploaded_file.id


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

    def get_last_document(self):
        """Return the document with the highest ``mevzuat_tertib`` and ``mevzuat_no`` for the ``mevzuat_tur``."""
        from .models import Document
        return (
            Document.objects
            .filter(metadata__mevzuat_tur=self.mevzuat_tur)
            .annotate(
                mevzuat_tertib=F("metadata__mevzuat_tertib"),
                mevzuat_no=F("metadata__mevzuat_no"),
            )
            .order_by("-mevzuat_tertib", "-mevzuat_no")
            .first()
        )

    def build_document_url(self, doc):
        uri = f"{doc.metadata['mevzuat_tur']}.{doc.metadata['mevzuat_tertib']}.{doc.metadata['mevzuat_no']}.pdf"
        return f"https://www.mevzuat.gov.tr/MevzuatMetin/{uri}"

    def build_next_document_url(self, offset=1):
        doc = self.get_last_document()
        uri = f"{doc.metadata['mevzuat_tur']}.{doc.metadata['mevzuat_tertib']}.{doc.metadata['mevzuat_no'] + offset}.pdf"
        return f"https://www.mevzuat.gov.tr/MevzuatMetin/{uri}"

    def get_document_date(self, doc):
        return datetime.strptime(doc.metadata['resmi_gazete_tarihi'], '%Y-%m-%d').date()

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

        # Save inside a transaction so the DB row and the file write stay in sync
        with transaction.atomic():
            doc.document.save(filename, ContentFile(response.content), save=False)
            doc.save(update_fields=["document"])

        return doc.document

    def extract_metadata(self, doc):
        pass


@register
class KanunFetcher(MevzuatFetcher):
    mevzuat_tur = 1


@register
class KHKFetcher(MevzuatFetcher):
    mevzuat_tur = 4


@register
class CBKararnameFetcher(MevzuatFetcher):
    mevzuat_tur = 19


@register
class CBKararFetcher(MevzuatFetcher):
    mevzuat_tur = 20


@register
class CBYonetmelikFetcher(MevzuatFetcher):
    mevzuat_tur = 21


@register
class CBGenelgeFetcher(MevzuatFetcher):
    mevzuat_tur = 22

    def build_document_url(self, doc):
        uri = f"CumhurbaskanligiGenelgeleri/{doc.metadata['resmi_gazete_tarihi'].strftime('%Y%m%d')}-{doc.metadata['mevzuat_no']}.pdf"
        return f"https://www.mevzuat.gov.tr/MevzuatMetin/{uri}"


@register
class YonetmelikFetcher(MevzuatFetcher):
    # For mevzuat_tur;
    #  - 7: Kurum Yönetmeliği
    #  - 8: Kurum Yönetmeliği (Üniversite)
    #  - 9: Tebliğ

    def build_document_url(self, doc):
        uri = f"yonetmelik/{doc.metadata['mevzuat_tur']}.{doc.metadata['mevzuat_tertib']}.{doc.metadata['mevzuat_no']}.pdf"
        return f"https://www.mevzuat.gov.tr/MevzuatMetin/{uri}"
