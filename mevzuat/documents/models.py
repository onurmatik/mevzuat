from datetime import datetime
import re
import uuid
from functools import cached_property

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from pgvector.django import VectorField, L2Distance, HnswIndex, HalfVectorField
from django.db import models
from slugify import slugify


class DocumentType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    short_name = models.CharField(max_length=100, unique=True, blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)

    active = models.BooleanField(default=True)

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

    embedding = VectorField(dimensions=1536, blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    summary = models.TextField(blank=True, null=True)
    summary_en = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        title = self.metadata.get('mevAdi')
        if title:
            self.title = title
        effective_date = self.metadata.get('resmiGazeteTarihi')
        if effective_date:
            self.date = parse_date(effective_date)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            update_fields = set(update_fields)
            update_fields.add("modified_at")
            kwargs["update_fields"] = update_fields
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            HnswIndex(
                name='topiccontent_embedding_hnsw',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_l2_ops']
            )
        ]

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

    def number(self):
        return self.metadata["mevzuatNo"]

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
        else:
            self.markdown_status = None
            self.save(update_fields=["markdown_status"])

        return markdown

    def generate_embedding(self, overwrite=False):
        """Generate embedding vector from document content using OpenAI.
        
        Uses text-embedding-3-small model (1536 dimensions) to create
        a vector representation of the document's markdown content.
        
        Includes title and summary in the embedded text, and retries with
        smaller chunks if the context length is exceeded.
        """
        if self.embedding is not None and not overwrite:
            return self.embedding
        
        if not self.markdown:
            # Fallback: if no markdown, at least try with title/summary
            if not self.title:
                raise ValueError("Document has no content to embed (no markdown or title)")
        
        from openai import OpenAI, BadRequestError
        client = OpenAI()
        
        full_text = f"{self.title}\n\n{self.markdown}"
        
        if not full_text.strip():
             raise ValueError("No content to embed")

        # Retry logic for context length
        # Start with a safe-ish upper bound. The model limit is 8191 tokens.
        # 32k chars is roughly 8k tokens (very rough approx).
        limit = 32000 
        
        while limit > 100:
            text = full_text[:limit]
            try:
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text,
                    dimensions=1536
                )
                self.embedding = response.data[0].embedding
                self.save(update_fields=["embedding"])
                return self.embedding
                
            except BadRequestError as e:
                # Check if it's a context length error
                err_str = str(e).lower()
                if "context_length_exceeded" in err_str or "maximum context length" in err_str:
                    # Reduce length by 20% and retry
                    limit = int(limit * 0.8)
                    continue
                # If it's another kind of BadRequest, re-raise
                raise
                
        raise ValueError("Could not generate embedding even with reduced context")

    def has_markdown_glyph_artifacts(self, *, threshold=None):
        """Return True if markdown resembles direct glyph dumps from PDFs."""
        if not self.markdown:
            return False
        threshold = threshold or self.GLYPH_ARTIFACT_THRESHOLD
        matches = self.GLYPH_ARTIFACT_PATTERN.findall(self.markdown)
        return len(matches) >= threshold

    def summarize(self, overwrite=False):
        """Generate a summary for the document using OpenAI.
        
        Uses GPT-4o to create a concise summary of the document content.
        """
        if self.summary and not overwrite:
            return self.summary
        
        if not self.markdown:
            raise ValueError("Document has no markdown content to summarize")
        
        from openai import OpenAI
        client = OpenAI()
        
        completion = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that summarizes legal documents. "
                               "Provide a practical impact summary in Turkish. "
                               "Write a neutral, factual statement with no added context. "
                               "Exclude all formal and administrative details "
                               "(such as dates, numbers, signatures, authorities, and legal references). "
                               "Do not use any markdown formatting; just plain sentences. "
                },
                {
                    "role": "user",
                    "content": self.markdown[:20000],
                },
            ],
        )
        
        self.summary = completion.choices[0].message.content
        self.save(update_fields=["summary"])
        return self.summary

    def translate(self, overwrite=False):
        """Translate title and summary from Turkish to English using OpenAI.
        
        Stores translations in title_en and summary_en fields.
        """
        if not overwrite and self.title_en:
            return {"title_en": self.title_en, "summary_en": self.summary_en}
        
        if not self.title:
            raise ValueError("Document has no title to translate")
        
        from openai import OpenAI
        client = OpenAI()
        
        # Build the translation prompt
        texts_to_translate = []
        if self.title:
            texts_to_translate.append(f"Title: {self.title}")
        if self.summary:
            texts_to_translate.append(f"Summary: {self.summary}")
        
        prompt = "Translate the following Turkish legal document metadata to English. Keep the format exactly as provided (Title: and Summary: labels).\n\n" + "\n\n".join(texts_to_translate)
        
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional translator specializing in Turkish legal documents. Translate accurately to English while preserving legal terminology.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )
        
        response_text = completion.choices[0].message.content
        
        # Parse the response
        lines = response_text.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.lower().startswith("title:"):
                self.title_en = line[6:].strip()
            elif line.lower().startswith("summary:"):
                self.summary_en = line[8:].strip()
        
        # Save updated translations
        update_fields = []
        if self.title_en:
            update_fields.append("title_en")
        if self.summary_en:
            update_fields.append("summary_en")
        
        if update_fields:
            self.save(update_fields=update_fields)
        
        return {"title_en": self.title_en, "summary_en": self.summary_en}


class FlaggedDocument(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    flagged_by = models.ForeignKey(User, on_delete=models.CASCADE)
    flagged_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document.title} {self.flagged_by} {self.flagged_at}"


class SearchQueryEmbedding(models.Model):
    query = models.TextField()
    normalized_query = models.TextField(unique=True)
    embedding = VectorField(dimensions=1536)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.query
