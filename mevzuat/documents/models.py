from datetime import datetime
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

    def last_document(self):
        return self._fetcher().get_last_document()

    def next_document_url(self, offset=1):
        return self._fetcher().build_next_document_url(offset)


def document_upload_to(instance, filename):
    # Upload path for the original doc and its markdown version
    return f"{instance.type.slug}/{instance.document_date.year}/{filename}"


class Document(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    type = models.ForeignKey(DocumentType, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')

    title = models.CharField(max_length=1000)
    date = models.DateField(blank=True, null=True)  # The significant date for the doc; e.g.: effective date, pub date, etc.

    document = models.FileField(upload_to=document_upload_to, blank=True, null=True)
    markdown = models.FileField(upload_to=document_upload_to, blank=True, null=True)

    oai_file_id = models.CharField(max_length=100, blank=True, null=True)
    embedding = VectorField(dimensions=1536, blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.date = datetime.strptime(self.metadata['resmi_gazete_tarihi'], '%Y-%m-%d').date()
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

    def convert_pdf_to_markdown(self, overwrite=False):
        return self._fetcher().convert_pdf_to_markdown(self, overwrite=overwrite)

    def sync_with_vectorstore(self):
        """Synchronise this document with the configured vector store."""
        return self._fetcher().sync_with_vectorstore(self)
