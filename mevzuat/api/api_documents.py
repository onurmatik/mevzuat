from typing import Optional, Any, List
from uuid import UUID
from datetime import date as dt_date
import re

from django.utils import timezone
from django.db import IntegrityError
from django.db.models import Count, IntegerField, Value
from django.db.models.functions import Cast, Coalesce, TruncDay, TruncMonth, TruncYear
from django.db.models.fields.json import KeyTextTransform
from django.shortcuts import get_object_or_404
from pydantic import Field
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.params import Query
from openai import OpenAI

from mevzuat.documents.models import Document, DocumentType, FlaggedDocument, SearchQueryEmbedding
from ninja.security import django_auth

router = Router()
QUERY_NORMALIZE_RE = re.compile(r"\s+")


def normalize_query(query: str) -> str:
    return QUERY_NORMALIZE_RE.sub(" ", query).strip()


def resolve_query_embedding(query: Optional[str]) -> tuple[Optional[str], Optional[list[float]]]:
    if not query:
        return None, None
    normalized_query = normalize_query(query)
    if not normalized_query:
        return None, None
    cached_query = (
        SearchQueryEmbedding.objects
        .filter(normalized_query=normalized_query)
        .only("embedding")
        .first()
    )
    if cached_query and cached_query.embedding is not None:
        return normalized_query, cached_query.embedding
    client = OpenAI()
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=normalized_query,
        dimensions=1536
    )
    query_embedding = response.data[0].embedding
    try:
        SearchQueryEmbedding.objects.create(
            query=normalized_query,
            normalized_query=normalized_query,
            embedding=query_embedding,
        )
    except IntegrityError:
        existing_query = (
            SearchQueryEmbedding.objects
            .filter(normalized_query=normalized_query)
            .only("embedding")
            .first()
        )
        if existing_query and existing_query.embedding is not None:
            query_embedding = existing_query.embedding
        else:
            SearchQueryEmbedding.objects.filter(normalized_query=normalized_query).update(
                query=normalized_query,
                embedding=query_embedding,
            )
    return normalized_query, query_embedding


def resolve_related_embedding(related_doc: Optional[Document]) -> Optional[list[float]]:
    if not related_doc:
        return None
    if related_doc.embedding is not None:
        return related_doc.embedding
    seed_text = " ".join(part for part in [related_doc.title, related_doc.summary] if part)
    if not seed_text.strip():
        raise HttpError(400, "Related document has no content to embed")
    client = OpenAI()
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=seed_text,
        dimensions=1536
    )
    return response.data[0].embedding


@router.post("/{uuid}/flag", auth=django_auth)
def flag_document(request, uuid: UUID):
    if not request.user.is_authenticated:
        return 401, {"success": False, "message": "Unauthorized"}
    
    doc = get_object_or_404(Document, uuid=uuid)
    FlaggedDocument.objects.get_or_create(
        document=doc,
        flagged_by=request.user
    )
    return {"success": True}


class DocumentOut(Schema):
    """Schema representing a document."""

    id: int
    uuid: UUID
    title: str
    content: Optional[str] = None
    summary: Optional[str] = None
    number: Optional[str] = None
    date: Optional[dt_date] = None
    type: str = Field(..., alias="type.slug")

    class Config:
        from_attributes = True
        populate_by_name = True

    @staticmethod
    def resolve_content(obj):
        return obj.markdown

    @staticmethod
    def resolve_summary(obj):
        return obj.summary

    @staticmethod
    def resolve_number(obj):
        return obj.number()

    @staticmethod
    def resolve_type(obj):
        return obj.type.slug if obj.type else None


class DocumentTypeOut(Schema):
    """Schema representing a document type."""

    id: int
    label: str = Field(..., alias="name")

    class Config:
        from_attributes = True


@router.get("/search")
def search_documents(
    request,
    query: Optional[str] = Query(None, description="Search query"),
    related_to: Optional[UUID] = Query(None, description="Related document UUID"),
    type: Optional[str] = Query(None, description="Document type slug"),
    start_date: Optional[dt_date] = Query(None),
    end_date: Optional[dt_date] = Query(None),
    limit: int = Query(10),
    offset: int = Query(0),
):
    """Search documents using local pgvector similarity search.

    ``query`` is optional if ``related_to`` is supplied. The query is converted to an embedding vector
    and compared against document embeddings using cosine similarity.
    Optional parameters allow filtering by document type and date ranges.
    """
    from pgvector.django import CosineDistance

    related_doc = None
    if related_to:
        related_doc = get_object_or_404(Document, uuid=related_to)

    _, query_embedding = resolve_query_embedding(query)
    related_embedding = resolve_related_embedding(related_doc)

    if query_embedding is not None and related_embedding is not None:
        query_embedding = [
            (left + right) / 2.0
            for left, right in zip(query_embedding, related_embedding)
        ]
    elif related_embedding is not None:
        query_embedding = related_embedding

    if query_embedding is None:
        raise HttpError(400, "Search requires a query or related_to parameter")

    # Build queryset with filters - only include documents with embeddings
    qs = Document.objects.exclude(embedding__isnull=True).select_related("type")
    if related_doc:
        qs = qs.exclude(uuid=related_doc.uuid)

    if type:
        if type.isdigit():
            qs = qs.filter(type_id=int(type))
        else:
            qs = qs.filter(type__slug=type)
    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)

    # Order by cosine similarity (lower distance = more similar)
    qs = qs.annotate(
        distance=CosineDistance("embedding", query_embedding)
    ).order_by("distance")

    # Get total count before pagination
    total_count = qs.count()

    # Paginate results
    results = list(qs[offset:offset + limit])
    has_more = total_count > offset + limit

    return {
        "data": [
            {
                "id": doc.id,
                "uuid": str(doc.uuid),
                "title": doc.title,
                "type": doc.type.slug if doc.type else "unknown",
                "date": doc.date.isoformat() if doc.date else None,
                "score": round(1 - doc.distance, 4) if doc.distance else 0,
                "attributes": {
                    "id": doc.id,
                    "uuid": str(doc.uuid),
                    "title": doc.title,
                    "number": (
                        doc.metadata.get("mevzuatNo")
                        or doc.metadata.get("MevzuatNo")
                        or doc.metadata.get("mevzuat_no")
                    ),
                    "summary": doc.summary,
                    "date": doc.date.isoformat() if doc.date else None,
                }
            }
            for doc in results
        ],
        "has_more": has_more
    }


@router.get("/types", response=List[DocumentTypeOut])
def list_document_types(request):
    """Return all available document types ordered by name."""
    return (
        DocumentType.objects
        .only("id", "name")
        .order_by("name")
    )


@router.get("/counts")
def document_counts(
    request,
    query: Optional[str] = Query(None, description="Search query"),
    related_to: Optional[UUID] = Query(None, description="Related document UUID"),
    type: Optional[str] = Query(None, description="Document type slug"),
    start_date: Optional[dt_date] = None,
    end_date: Optional[dt_date] = None,
    interval: str = "day",
    min_score: float = Query(0.5, ge=-1, le=1),
) -> list[dict[str, Any]]:
    """
    Return document counts grouped by a time interval and type.

    If ``start_date`` is not provided, the earliest available publication date
    (``Document.date``) is used. ``end_date`` defaults to today.
    ``interval`` may be one of ``"day"``, ``"month"`` or ``"year"``.
    """
    from django.core.cache import cache
    from pgvector.django import CosineDistance

    if interval not in {"day", "month", "year"}:
        raise HttpError(400, "``interval`` must be one of 'day', 'month' or 'year'")

    related_doc = None
    if related_to:
        related_doc = get_object_or_404(Document, uuid=related_to)

    normalized_query = normalize_query(query) if query else None
    if normalized_query == "":
        normalized_query = None

    # Build cache key from parameters
    cache_key = (
        f"doc_counts:{interval}:{start_date}:{end_date}:"
        f"{normalized_query}:{related_to}:{type}:{min_score}"
    )
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    query_embedding = None
    if normalized_query:
        _, query_embedding = resolve_query_embedding(query)
    related_embedding = resolve_related_embedding(related_doc)

    if query_embedding is not None and related_embedding is not None:
        query_embedding = [
            (left + right) / 2.0
            for left, right in zip(query_embedding, related_embedding)
        ]
    elif related_embedding is not None:
        query_embedding = related_embedding

    qs = Document.objects.all()
    if type:
        if type.isdigit():
            qs = qs.filter(type_id=int(type))
        else:
            qs = qs.filter(type__slug=type)
    if query_embedding is not None:
        qs = qs.exclude(embedding__isnull=True)
        if related_doc:
            qs = qs.exclude(uuid=related_doc.uuid)
        qs = qs.annotate(distance=CosineDistance("embedding", query_embedding))
        qs = qs.filter(distance__lte=1 - min_score)

    # --- Default date boundaries ------------------------------------------------
    if start_date is None:
        first_ts = (
            qs.exclude(date__isnull=True)
            .order_by("date")
            .values_list("date", flat=True)
            .first()
        )
        # If there are no documents yet, default to today so we don't blow up later.
        start_date = first_ts if first_ts else timezone.now().date()

    if end_date is None:
        end_date = timezone.now().date()

    qs = qs.filter(date__gte=start_date, date__lte=end_date)

    # --- Pick the appropriate truncation function ------------------------------
    truncator = {
        "day": TruncDay("date"),
        "month": TruncMonth("date"),
        "year": TruncYear("date"),
    }[interval]

    # --- Aggregate counts -------------------------------------------------------
    qs = (
        qs.annotate(period=truncator)
        .values("period", "type__slug")
        .annotate(count=Count("id"))
        .order_by("period", "type__slug")
    )

    # --- Normalise output so it's JSON-serialisable -----------------------------
    results: list[dict[str, Any]] = []
    for row in qs:
        period = row["period"]
        results.append(
            {
                "period": period.isoformat(),
                "type": row["type__slug"] or "unknown",
                "count": row["count"],
            }
        )

    # Cache for 1 hour (3600 seconds)
    cache.set(cache_key, results, 3600)

    return results


@router.get("/list", response=list[DocumentOut])
def list_documents(
    request,
    type: Optional[str] = Query(None, description="DocumentType ID or slug"),
    year: Optional[int] = Query(None, ge=1900),
    month: Optional[int] = Query(None, ge=1, le=12),
    date: Optional[dt_date] = Query(None),
    start_date: Optional[dt_date] = Query(None),
    end_date: Optional[dt_date] = Query(None),
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0),
):
    """
    Return documents filtered by type and/or their significant date.

    **Query-param precedence**

    1. ``date``
    2. ``start_date`` / ``end_date`` (range, inclusive)
    3. ``year`` + ``month``

    * If *only* ``year`` is supplied, all months in that year are returned.
    * Supplying ``month`` without ``year`` yields *400*.
    """
    # --- quick validations -------------------------------------------------
    if month and year is None:
        raise HttpError(400, '"month" requires a "year" parameter')

    if start_date and end_date and start_date > end_date:
        raise HttpError(400, '"start_date" cannot be after "end_date"')

    # --- build the base queryset ------------------------------------------
    qs = Document.objects.all()

    if type is not None:
        if type.isdigit():
            qs = qs.filter(type_id=int(type))
        else:
            qs = qs.filter(type__slug=type)

    # --- apply date filtering by precedence --------------------------------
    if date:
        qs = qs.filter(date=date)

    elif start_date or end_date:
        if start_date and end_date:
            qs = qs.filter(date__range=(start_date, end_date))
        elif start_date:
            qs = qs.filter(date__gte=start_date)
        else:  # end_date only
            qs = qs.filter(date__lte=end_date)

    elif year or month:
        # here month is either None or has a matching year (validated above)
        qs = qs.filter(date__year=year)
        if month:
            qs = qs.filter(date__month=month)

    # exclude null dates and types
    qs = qs.exclude(date__isnull=True).exclude(date__isnull=True)

    mevzuat_no_num = Coalesce(
        Cast(KeyTextTransform("mevzuatNo", "metadata"), IntegerField()),
        Value(0),
    )
    qs = qs.annotate(mevzuat_no_num=mevzuat_no_num).order_by(
        "-date",
        "-mevzuat_no_num",
        "-id",
    )

    # Hard limit of 100 if user asks for more, default 10
    limit = min(limit, 100)
    
    return qs[offset : offset + limit]


@router.get("/{document_uuid}", response=DocumentOut)
def get_document(request, document_uuid: UUID):
    """
    Retrieve a single document by UUID.
    """
    return get_object_or_404(Document, uuid=document_uuid)


@router.post("/{document_uuid}/summarize")
def summarize_document(request, document_uuid: UUID):
    """
    Generate a summary for the document using AI.
    """
    doc = get_object_or_404(Document, uuid=document_uuid)

    try:
        summary = doc.summarize()
        return {"summary": summary}
    except ValueError as e:
        raise HttpError(400, str(e))
    except Exception as e:
        raise HttpError(500, f"Error generating summary: {str(e)}")


@router.post("/{document_uuid}/translate")
def translate_document(request, document_uuid: UUID):
    """
    Translate the document's title and summary from Turkish to English using AI.
    """
    doc = get_object_or_404(Document, uuid=document_uuid)

    try:
        result = doc.translate()
        return result
    except ValueError as e:
        raise HttpError(400, str(e))
    except Exception as e:
        raise HttpError(500, f"Error translating document: {str(e)}")
