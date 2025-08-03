from typing import Optional, Any

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
