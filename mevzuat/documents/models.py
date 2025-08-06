import uuid
from functools import cached_property
from django.core.exceptions import ValidationError

from pgvector.django import VectorField, L2Distance, HnswIndex, HalfVectorField
from django.db import models
from django.conf import settings
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
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    default_vector_store = models.ForeignKey(
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
        if self.fetcher not in _registry:
            raise ValidationError({"fetcher": "Unknown fetcher class"})

    @cached_property
    def document_count(self):
        return self.documents.count()


def document_upload_to(instance, filename):
    # Upload path for the original doc and its markdown version
    return f"docs/{instance.type.slug}/{instance.document_date.year}/{filename}"


class Document(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    type = models.ForeignKey(DocumentType, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')

    title = models.CharField(max_length=300)

    document = models.FileField(upload_to=document_upload_to, blank=True, null=True)
    markdown = models.FileField(upload_to=document_upload_to, blank=True, null=True)

    oai_file_id = models.CharField(max_length=100, blank=True, null=True)
    embedding = VectorField(dimensions=1536, blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

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
        return self._fetcher().build_original_url(self)

    def enrich_metadata(self, pdf_bytes=None):
        extra = self._fetcher().extract_metadata(self)
        merged = {**self.metadata, **(extra or {})}
        return merged

    def get_vectorstore_id(self):
        """Return the vectorstore id for this document type.

        Looks up ``settings.VECTORSTORES`` using the child class name.
        """
        try:
            return settings.VECTORSTORES[self.__class__.__name__]
        except KeyError as exc:
            raise KeyError(
                f"No vectorstore configured for {self.__class__.__name__}"
            ) from exc

    def get_metadata(self):
        raise NotImplementedError("Child class should implement get_metadata()")

    def get_document_upload_to(self, filename):
        raise NotImplementedError("Child class should implement get_document_upload_to()")
