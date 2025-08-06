from typing import Optional, Any
from datetime import date

from django.conf import settings
from django.db.models import Count, Min
from django.db.models.functions import ExtractYear
from ninja import Router, Schema
from openai import OpenAI

from .models import Document


router = Router()


class VectorStoreOut(Schema):
    """Schema representing an available vector store."""

    name: str
    id: str


class VectorSearchPayload(Schema):
    query: str
    limit: int = 10
    score_threshold: Optional[float] = None
    rewrite_query: bool = True


class DocumentOut(Schema):
    """Schema representing a document."""

    id: int
    name: str
    mevzuat_tur: int
    resmi_gazete_tarihi: Optional[date]

    class Config:
        from_attributes = True


@router.post("/vector-stores/{vs_id}/search")
def search_vector_store(request, vs_id: str, payload: VectorSearchPayload):
    """Query a vector store and return relevant results."""
    client = OpenAI()
    ranking_options = {}
    if payload.score_threshold is not None:
        ranking_options["score_threshold"] = payload.score_threshold
    response = client.vector_stores.search(
        vector_store_id=vs_id,
        query=payload.query,
        max_num_results=payload.limit,
        ranking_options=ranking_options or None,
        rewrite_query=payload.rewrite_query,
    )
    return response


@router.get("/vector-stores", response=list[VectorStoreOut])
def list_vector_stores(request):
    """Return the vector stores configured in settings."""

    return [
        {"name": name, "id": vs_id}
        for name, vs_id in settings.VECTORSTORES.items()
    ]


@router.get("/counts")
def document_counts(
    request,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    interval: str = "day",
) -> list[dict[str, Any]]:
    """Return document counts grouped by a time interval and type.

    If ``start_date`` is not provided, the earliest available publication date
    is used. ``end_date`` defaults to today. ``interval`` may be one of
    ``"day"``, ``"month"`` or ``"year"``.
    """

    from datetime import timedelta, datetime
    from django.db.models.functions import TruncDay, TruncMonth

    if end_date is None:
        end_date = date.today()
    if start_date is None:
        earliest = (
            Document.objects.exclude(resmi_gazete_tarihi__isnull=True)
            .aggregate(Min("resmi_gazete_tarihi"))
            .get("resmi_gazete_tarihi__min")
        )
        start_date = earliest or (end_date - timedelta(days=30))

    qs = (
        Document.objects.exclude(resmi_gazete_tarihi__isnull=True)
        .filter(resmi_gazete_tarihi__range=(start_date, end_date))
        .filter(mevzuat_tur__in=[1, 4, 19, 20, 21, 22])
    )

    if interval == "month":
        qs = qs.annotate(period=TruncMonth("resmi_gazete_tarihi"))
    elif interval == "year":
        qs = qs.annotate(period=ExtractYear("resmi_gazete_tarihi"))
    else:
        qs = qs.annotate(period=TruncDay("resmi_gazete_tarihi"))

    qs = (
        qs.values("period", "mevzuat_tur")
        .annotate(count=Count("id"))
        .order_by("period", "mevzuat_tur")
    )

    label_map = dict(Document._meta.get_field("mevzuat_tur").choices)
    result: dict[str, dict[str, int]] = {}
    for row in qs:
        period_val = row["period"]
        if isinstance(period_val, (date, datetime)):
            key = period_val.isoformat()
        else:
            key = str(period_val)
        label = label_map.get(row["mevzuat_tur"], str(row["mevzuat_tur"]))
        result.setdefault(key, {})[label] = row["count"]
    return [{"date": k, **counts} for k, counts in sorted(result.items())]


@router.get("/", response=list[DocumentOut])
def list_documents(
    request,
    mevzuat_tur: Optional[int] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """Return documents filtered by type and/or publication date."""

    qs = Document.objects.all()
    if mevzuat_tur is not None:
        qs = qs.filter(mevzuat_tur=mevzuat_tur)
    if year is not None:
        qs = qs.filter(resmi_gazete_tarihi__year=year)
    if month is not None:
        qs = qs.filter(resmi_gazete_tarihi__month=month)
    if date is not None:
        qs = qs.filter(resmi_gazete_tarihi=date)
    if start_date is not None and end_date is not None:
        qs = qs.filter(resmi_gazete_tarihi__range=(start_date, end_date))
    elif start_date is not None:
        qs = qs.filter(resmi_gazete_tarihi__gte=start_date)
    elif end_date is not None:
        qs = qs.filter(resmi_gazete_tarihi__lte=end_date)
    return qs
