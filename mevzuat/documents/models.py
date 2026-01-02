from datetime import datetime
import re
import uuid
from functools import cached_property
from django.core.exceptions import ValidationError

from pgvector.django import VectorField, L2Distance, HnswIndex, HalfVectorField
from django.db import models
from slugify import slugify


class VectorStore(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    name = models.CharField(max_length=100, unique=True)
    oai_vs_id = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class DocumentType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    short_name = models.CharField(max_length=100, unique=True, blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)

    active = models.BooleanField(default=True)

    vector_store = models.ForeignKey(
        VectorStore, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    fetcher = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def clean(self):
        from .fetchers import _registry
        if self.fetcher and self.fetcher not in _registry:
            raise ValidationError({"fetcher": "Unknown fetcher class"})

    @cached_property
    def document_count(self):
        return self.documents.count()

    def _fetcher(self):
        from .fetchers import get
        return get(self.fetcher)


def document_upload_to(instance, filename):
    # Upload path for the original doc and its markdown version
    return f"{instance.type.slug}/{instance.document_date.year}/{filename}"


def parse_date(effective_date: str):
    for fmt in ("%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(effective_date, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Date {effective_date!r} is not in an accepted format")


class Document(models.Model):
    MARKDOWN_STATUS_SUCCESS = "success"
    MARKDOWN_STATUS_WARNING = "warning"
    MARKDOWN_STATUS_FAILED = "failed"
    MARKDOWN_STATUS_CHOICES = (
        (MARKDOWN_STATUS_SUCCESS, "Success"),
        (MARKDOWN_STATUS_WARNING, "Warning"),
        (MARKDOWN_STATUS_FAILED, "Failed"),
    )
    GLYPH_ARTIFACT_PATTERN = re.compile(r"GLYPH(?:<|&lt;)", re.IGNORECASE)
    GLYPH_ARTIFACT_THRESHOLD = 5

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    type = models.ForeignKey(DocumentType, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')

    title = models.CharField(max_length=1000)
    title_en = models.CharField(max_length=1000, blank=True, null=True)
    date = models.DateField(blank=True, null=True)  # The significant date for the doc; e.g.: effective date, pub date, etc.

    document = models.FileField(upload_to=document_upload_to, blank=True, null=True)
    file_size = models.BigIntegerField(blank=True, null=True)
    markdown = models.TextField(blank=True, null=True)
    markdown_status = models.CharField(max_length=20, choices=MARKDOWN_STATUS_CHOICES, blank=True, null=True)

    oai_file_id = models.CharField(max_length=100, blank=True, null=True)
    embedding = VectorField(dimensions=1536, blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    summary = models.TextField(blank=True, null=True)
    summary_en = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        title = self.metadata.get('mevAdi')
        if title:
            self.title = title
        effective_date = self.metadata.get('resmiGazeteTarihi')
        if effective_date:
            self.date = parse_date(effective_date)
        super().save(*args, **kwargs)

    class Meta:
        """
        indexes = [
            HnswIndex(
                name='topiccontent_embedding_hnsw',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_l2_ops']
            )
        ]
        """

    def _fetcher(self):
        from .fetchers import get
        return get(self.type.fetcher)

    @cached_property
    def document_date(self):
        return self._fetcher().get_document_date(self)

    @cached_property
    def original_document_url(self):
        return self._fetcher().build_document_url(self)

    def enrich_metadata(self, pdf_bytes=None):
        extra = self._fetcher().extract_metadata(self)
        merged = {**self.metadata, **(extra or {})}
        return merged

    def get_vectorstore_id(self):
        # Returns the default vectorstore id for this document type.
        if not self.type:
            raise ValidationError("Document type is not set")
        elif not self.type.vector_store:
            raise ValidationError(f"No vectorstore configured for document type {self.type}")
        return self.type.vector_store.oai_vs_id

    def fetch_and_store_document(self, overwrite=False):
        return self._fetcher().fetch_and_store_document(self, overwrite=overwrite)

    def convert_pdf_to_markdown(self, overwrite=False, *, force_ocr=True):
        markdown = self._fetcher().convert_pdf_to_markdown(
            self,
            overwrite=overwrite,
            force_ocr=force_ocr,
        )

        if self.has_markdown_glyph_artifacts():
            warning_status = getattr(self, "MARKDOWN_STATUS_WARNING", "warning")
            if force_ocr:
                if self.markdown_status != warning_status:
                    self.markdown_status = warning_status
                    self.save(update_fields=["markdown_status"])
                return self.markdown
            return self.convert_pdf_to_markdown(
                overwrite=True,
                force_ocr=True,
            )

        return markdown

    def generate_embedding(self, overwrite=False):
        """Generate embedding vector from document content using OpenAI.
        
        Uses text-embedding-3-small model (1536 dimensions) to create
        a vector representation of the document's markdown content.
        """
        if self.embedding is not None and not overwrite:
            return self.embedding
        
        if not self.markdown:
            raise ValueError("Document has no markdown content to embed")
        
        from openai import OpenAI
        client = OpenAI()
        
        # Use first ~8000 tokens of content (model limit is 8191)
        # Assuming ~4 chars per token, use first 32k chars
        text = self.markdown[:32000]
        
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            dimensions=1536
        )
        
        self.embedding = response.data[0].embedding
        self.save(update_fields=["embedding"])
        return self.embedding

    def has_markdown_glyph_artifacts(self, *, threshold=None):
        """Return True if markdown resembles direct glyph dumps from PDFs."""
        if not self.markdown:
            return False
        threshold = threshold or self.GLYPH_ARTIFACT_THRESHOLD
        matches = self.GLYPH_ARTIFACT_PATTERN.findall(self.markdown)
        return len(matches) >= threshold
