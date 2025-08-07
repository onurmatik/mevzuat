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


class DocumentOut(Schema):
    """Schema representing a document."""

    id: int
    title: str
    type: int = Field(..., alias="type_id")   # FK → plain integer in the payload
    date: Optional[date]

    class Config:
        from_attributes = True
        populate_by_name = True


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
    """

    try:
        vs = VectorStore.objects.only("oai_vs_id").get(uuid=vs_uuid)
    except VectorStore.DoesNotExist:
        raise HttpError(404, "Vector store not found")

    client = OpenAI()

    ranking_options = {}
    if payload.score_threshold is not None:
        ranking_options["score_threshold"] = payload.score_threshold

    response = client.vector_stores.search(
        vector_store_id=vs.oai_vs_id,          # use the OpenAI-side ID
        query=payload.query,
        max_num_results=payload.limit,
        ranking_options=ranking_options or None,
        rewrite_query=payload.rewrite_query,
    )

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
    (``Document.created_at``) is used. ``end_date`` defaults to today.
    ``interval`` may be one of ``"day"``, ``"month"`` or ``"year"``.
    """
    if interval not in {"day", "month", "year"}:
        raise HttpError(400, "``interval`` must be one of 'day', 'month' or 'year'")

    qs = Document.objects.all()

    # --- Default date boundaries ------------------------------------------------
    if start_date is None:
        first_ts = qs.order_by("created_at").values_list("created_at", flat=True).first()
        # If there are no documents yet, default to today so we don’t blow up later.
        start_date = first_ts.date() if first_ts else timezone.now().date()

    if end_date is None:
        end_date = timezone.now().date()

    qs = qs.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)

    # --- Pick the appropriate truncation function ------------------------------
    truncator = {
        "day": TruncDay("created_at"),
        "month": TruncMonth("created_at"),
        "year": TruncYear("created_at"),
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
        period = row["period"].date()  # strip time component
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
