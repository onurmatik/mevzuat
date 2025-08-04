from typing import Optional, Any
from datetime import date

from django.conf import settings
from django.db.models import Count
from django.db.models.functions import ExtractYear
from ninja import Router, Schema
from openai import OpenAI

from .models import Mevzuat


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


class MevzuatOut(Schema):
    """Schema representing a mevzuat document."""

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
def document_counts(request) -> list[dict[str, Any]]:
    """Return document counts grouped by year and type."""

    qs = (
        Mevzuat.objects.exclude(resmi_gazete_tarihi__isnull=True)
        .filter(resmi_gazete_tarihi__year__gte=2000)
        .filter(mevzuat_tur__in=[1, 4, 19, 20, 21, 22])
        .annotate(year=ExtractYear("resmi_gazete_tarihi"))
        .values("year", "mevzuat_tur")
        .annotate(count=Count("id"))
        .order_by("year", "mevzuat_tur")
    )
    label_map = dict(Mevzuat._meta.get_field("mevzuat_tur").choices)
    result: dict[int, dict[str, int]] = {}
    for row in qs:
        year = row["year"]
        label = label_map.get(row["mevzuat_tur"], str(row["mevzuat_tur"]))
        result.setdefault(year, {})[label] = row["count"]
    return [
        {"year": year, **counts} for year, counts in sorted(result.items())
    ]


@router.get("/list", response=list[MevzuatOut])
def list_documents(request, mevzuat_tur: Optional[int] = None, year: Optional[int] = None):
    """Return documents filtered by type and/or publication year."""

    qs = Mevzuat.objects.all()
    if mevzuat_tur is not None:
        qs = qs.filter(mevzuat_tur=mevzuat_tur)
    if year is not None:
        qs = qs.filter(resmi_gazete_tarihi__year=year)
    return qs
