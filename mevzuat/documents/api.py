from typing import Optional, Any, List
from uuid import UUID
from datetime import date

from django.utils import timezone
from django.db.models import Count, Min, IntegerField, DateField
from django.db.models.functions import ExtractYear, Cast, Coalesce, TruncDay, TruncMonth, TruncYear
from pydantic import Field
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.params import Query
from openai import OpenAI

from .models import Document, DocumentType, VectorStore

router = Router()


class VectorStoreOut(Schema):
    """Schema representing an available vector store."""

    uuid: UUID
    name: str
    description: Optional[str] = None


class VectorSearchPayload(Schema):
    query: str
    limit: int = 10
    score_threshold: Optional[float] = None
    rewrite_query: bool = True
    filters: Optional[dict] = None


class DocumentOut(Schema):
    """Schema representing a document."""

    id: int
    title: str
    type: int = Field(..., alias="type_id")   # FK → plain integer in the payload
    date: Optional[date]

    class Config:
        from_attributes = True
        populate_by_name = True


class DocumentTypeOut(Schema):
    """Schema representing a document type."""

    id: int
    label: str = Field(..., alias="name")

    class Config:
        from_attributes = True


@router.get("/search")
def search_documents(
    request,
    query: str = Query(..., description="Search query"),
    type: Optional[str] = Query(None, description="Document type slug"),
    date: Optional[date] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    score_threshold: Optional[float] = Query(None),
    limit: int = Query(10),
    offset: int = Query(0),
):
    """Search documents across all vector stores.

    ``query`` is required. Optional parameters allow filtering by document
    type and date ranges without exposing the underlying vector stores.
    """

    # determine vector stores to search
    if type:
        try:
            dt = (
                DocumentType.objects
                .select_related("vector_store")
                .get(slug=type, vector_store__isnull=False)
            )
        except DocumentType.DoesNotExist:
            raise HttpError(404, "Document type not found")
        vector_store_ids = [dt.vector_store.oai_vs_id]
    else:
        vector_store_ids = list(
            DocumentType.objects
            .filter(vector_store__isnull=False)
            .values_list("vector_store__oai_vs_id", flat=True)
            .distinct()
        )

        if not vector_store_ids:
            raise HttpError(404, "No vector stores configured")

    # build filter dictionary
    filters: list[dict[str, Any]] = []
    if type:
        filters.append({"type": "eq", "key": "type", "value": type})
    if date:
        filters.append({"type": "eq", "key": "date", "value": date.isoformat()})
    else:
        if start_date:
            filters.append({"type": "gte", "key": "date", "value": start_date.isoformat()})
        if end_date:
            filters.append({"type": "lte", "key": "date", "value": end_date.isoformat()})

    filter_obj: Optional[dict[str, Any]]
    if not filters:
        filter_obj = None
    elif len(filters) == 1:
        filter_obj = filters[0]
    else:
        filter_obj = {"type": "and", "filters": filters}

    client = OpenAI()
    ranking_options = {}
    if score_threshold is not None:
        ranking_options["score_threshold"] = score_threshold

    results: list[dict[str, Any]] = []
    fetch_count = offset + limit + 1
    for vs_id in vector_store_ids:
        search_kwargs = {
            "vector_store_id": vs_id,
            "query": query,
            "max_num_results": fetch_count,
            "ranking_options": ranking_options or None,
            "rewrite_query": True,
        }
        if filter_obj is not None:
            search_kwargs["filters"] = filter_obj
        response = client.vector_stores.search(**search_kwargs)

        for item in response.data:
            for c in item.content:
                results.append({
                    "text": c.text,
                    "type": c.type,
                    "filename": item.filename,
                    "score": item.score,
                    "attributes": item.attributes,
                })

    results.sort(key=lambda r: r.get("score", 0), reverse=True)
    page = results[offset:offset + limit]
    has_more = len(results) > offset + limit
    return {"data": page, "has_more": has_more}


@router.post("/vector-stores/{vs_uuid}/search")
def search_vector_store(
    request,
    vs_uuid: UUID,
    payload: VectorSearchPayload,
) -> Any:
    """
    Query a vector store **by its UUID** and return the relevant results from OpenAI.

    * ``vs_uuid`` – The UUID of the :class:`VectorStore` object.
      The view resolves this to the underlying ``oai_vs_id`` that OpenAI expects.
    * ``filters`` – Optional filter dictionary passed directly to OpenAI, allowing
      restriction of results by file attributes such as document type or date.
    """

    try:
        vs = VectorStore.objects.only("oai_vs_id").get(uuid=vs_uuid)
    except VectorStore.DoesNotExist:
        raise HttpError(404, "Vector store not found")

    client = OpenAI()

    ranking_options = {}
    if payload.score_threshold is not None:
        ranking_options["score_threshold"] = payload.score_threshold

    search_kwargs = {
        "vector_store_id": vs.oai_vs_id,
        "query": payload.query,
        "max_num_results": payload.limit,
        "ranking_options": ranking_options or None,
        "rewrite_query": payload.rewrite_query,
    }
    if payload.filters is not None:
        search_kwargs["filters"] = payload.filters

    response = client.vector_stores.search(**search_kwargs)

    return response

@router.get("/vector-stores", response=List[VectorStoreOut])
def list_vector_stores(request):
    """
    Return a list of all available vector stores sorted by name.

    The response is a list of objects with the following shape:

    ```json
    [
      {
        "uuid": "1f4b3d2e-e57b-4f33-9c5f-5fbad829e7f8",
        "name": "LegalDocs",
        "description": "Vector store holding legislation and case law"
      },
      ...
    ]
    ```
    """
    qs = (
        VectorStore.objects
        .values("uuid", "name", "description")
        .order_by("name")
    )

    # Convert QuerySet of dicts to list so Ninja can serialise it cleanly
    return list(qs)


@router.get("/types", response=List[DocumentTypeOut])
def list_document_types(request):
    """Return all available document types ordered by name."""
    return (
        DocumentType.objects
        .filter(vector_store__isnull=False)
        .only("id", "name")
        .order_by("name")
    )


@router.get("/counts")
def document_counts(
    request,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    interval: str = "day",
) -> list[dict[str, Any]]:
    """
    Return document counts grouped by a time interval and type.

    If ``start_date`` is not provided, the earliest available publication date
    (``Document.date``) is used. ``end_date`` defaults to today.
    ``interval`` may be one of ``"day"``, ``"month"`` or ``"year"``.
    """
    if interval not in {"day", "month", "year"}:
        raise HttpError(400, "``interval`` must be one of 'day', 'month' or 'year'")

    qs = Document.objects.all()

    # --- Default date boundaries ------------------------------------------------
    if start_date is None:
        first_ts = qs.order_by("date").values_list("date", flat=True).first()
        # If there are no documents yet, default to today so we don’t blow up later.
        start_date = first_ts if first_ts else timezone.now().date()

    if end_date is None:
        end_date = timezone.now().date()

    # initial cutoff
    qs = qs.filter(date__year__gte=2000)

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
        .values("period", "type__name")
        .annotate(count=Count("id"))
        .order_by("period", "type__name")
    )

    # --- Normalise output so it’s JSON-serialisable -----------------------------
    results: list[dict[str, Any]] = []
    for row in qs:
        period = row["period"]
        results.append(
            {
                "period": period.isoformat(),
                "type": row["type__name"] or "Unknown",
                "count": row["count"],
            }
        )

    return results


@router.get("/list", response=list[DocumentOut])
def list_documents(
    request,
    type: Optional[int] = Query(None, description="DocumentType ID"),
    year: Optional[int] = Query(None, ge=1900),
    month: Optional[int] = Query(None, ge=1, le=12),
    date: Optional[date] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
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
        qs = qs.filter(type_id=type)

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

    # order newest-first
    qs = qs.order_by("-date", "-id")

    return qs
