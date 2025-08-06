from typing import Optional, Any
from datetime import date

from django.conf import settings
from django.db.models import Count, Min, IntegerField, DateField
from django.db.models.functions import ExtractYear, Cast, TruncDay, TruncMonth
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
    title: str
    mevzuat_tur: int
    document_date: Optional[date]

    class Config:
        from_attributes = True


# Mapping of ``mevzuat_tur`` integer codes to their human readable labels.
# These values were previously defined on the old ``Mevzuat`` model as
# ``choices`` and are now represented here explicitly so the API continues to
# return labelled data after the model refactor.
MEVZUAT_TUR_LABELS: dict[int, str] = {
    1: "Kanun",
    4: "KHK",
    19: "Cumhurbaşkanlığı Kararnamesi",
    20: "Cumhurbaşkanı Kararı",
    21: "Cumhurbaşkanlığı Yönetmeliği",
    22: "Cumhurbaşkanlığı Genelgesi",
}


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

    if end_date is None:
        end_date = date.today()
    if start_date is None:
        earliest = (
            Document.objects.exclude(metadata__resmi_gazete_tarihi__isnull=True)
            .annotate(rg_date=Cast("metadata__resmi_gazete_tarihi", DateField()))
            .aggregate(Min("rg_date"))
            .get("rg_date__min")
        )
        start_date = earliest or (end_date - timedelta(days=30))

    qs = (
        Document.objects.exclude(metadata__resmi_gazete_tarihi__isnull=True)
        .annotate(
            mevzuat_tur=Cast("metadata__mevzuat_tur", IntegerField()),
            rg_date=Cast("metadata__resmi_gazete_tarihi", DateField()),
        )
        .filter(rg_date__range=(start_date, end_date))
        .filter(mevzuat_tur__in=MEVZUAT_TUR_LABELS.keys())
    )

    if interval == "month":
        qs = qs.annotate(period=TruncMonth("rg_date"))
    elif interval == "year":
        qs = qs.annotate(period=ExtractYear("rg_date"))
    else:
        qs = qs.annotate(period=TruncDay("rg_date"))

    qs = (
        qs.values("period", "mevzuat_tur")
        .annotate(count=Count("id"))
        .order_by("period", "mevzuat_tur")
    )

    result: dict[str, dict[str, int]] = {}
    for row in qs:
        period_val = row["period"]
        if isinstance(period_val, (date, datetime)):
            key = period_val.isoformat()
        else:
            key = str(period_val)
        label = MEVZUAT_TUR_LABELS.get(row["mevzuat_tur"], str(row["mevzuat_tur"]))
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

    qs = Document.objects.annotate(
        mevzuat_tur=Cast("metadata__mevzuat_tur", IntegerField()),
        document_date=Cast("metadata__resmi_gazete_tarihi", DateField()),
    )
    if mevzuat_tur is not None:
        qs = qs.filter(mevzuat_tur=mevzuat_tur)
    if year is not None:
        qs = qs.filter(document_date__year=year)
    if month is not None:
        qs = qs.filter(document_date__month=month)
    if date is not None:
        qs = qs.filter(document_date=date)
    if start_date is not None and end_date is not None:
        qs = qs.filter(document_date__range=(start_date, end_date))
    elif start_date is not None:
        qs = qs.filter(document_date__gte=start_date)
    elif end_date is not None:
        qs = qs.filter(document_date__lte=end_date)
    return qs
