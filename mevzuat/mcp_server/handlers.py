"""Handlers implementing document-related tools."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.db.models import Count
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from django.utils import timezone
from openai import OpenAI

from . import config  # noqa: F401  # Ensure Django setup
from ..documents.models import Document, DocumentType


def list_document_types() -> list[dict[str, Any]]:
    """Return all available document types ordered by name."""
    qs = (
        DocumentType.objects.filter(vector_store__isnull=False)
        .values("id", name="name")
        .order_by("name")
    )
    return list(qs)


def document_counts(
    start_date: date | None = None,
    end_date: date | None = None,
    interval: str = "day",
) -> list[dict[str, Any]]:
    """Return document counts grouped by a time interval and type."""
    if interval not in {"day", "month", "year"}:
        raise ValueError("interval must be one of 'day', 'month' or 'year'")

    qs = Document.objects.all()

    if start_date is None:
        first_ts = qs.order_by("date").values_list("date", flat=True).first()
        start_date = first_ts if first_ts else timezone.now().date()
    if end_date is None:
        end_date = timezone.now().date()

    qs = qs.filter(date__year__gte=2000)
    qs = qs.filter(date__gte=start_date, date__lte=end_date)

    truncator = {
        "day": TruncDay("date"),
        "month": TruncMonth("date"),
        "year": TruncYear("date"),
    }[interval]

    qs = (
        qs.annotate(period=truncator)
        .values("period", "type__name")
        .annotate(count=Count("id"))
        .order_by("period", "type__name")
    )

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


def list_documents(
    type: int | None = None,
    year: int | None = None,
    month: int | None = None,
    date: date | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    """Return documents filtered by type and/or their significant date."""
    if month and year is None:
        raise ValueError('"month" requires a "year" parameter')
    if start_date and end_date and start_date > end_date:
        raise ValueError('"start_date" cannot be after "end_date"')

    qs = Document.objects.all()
    if type is not None:
        qs = qs.filter(type_id=type)

    if date:
        qs = qs.filter(date=date)
    elif start_date or end_date:
        if start_date and end_date:
            qs = qs.filter(date__range=(start_date, end_date))
        elif start_date:
            qs = qs.filter(date__gte=start_date)
        else:
            qs = qs.filter(date__lte=end_date)
    elif year or month:
        qs = qs.filter(date__year=year)
        if month:
            qs = qs.filter(date__month=month)

    qs = qs.exclude(date__isnull=True).exclude(date__isnull=True)
    qs = qs.order_by("-date", "-id")

    return list(qs.values("id", "title", "type_id", "date"))


def search_documents(
    query: str,
    type: str | None = None,
    date: date | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    score_threshold: float | None = None,
    limit: int = 10,
    offset: int = 0,
    sort: str = "relevance",
) -> dict[str, Any]:
    """Search documents across all vector stores."""
    if type:
        try:
            dt = (
                DocumentType.objects.select_related("vector_store")
                .get(slug=type, vector_store__isnull=False)
            )
        except DocumentType.DoesNotExist:
            raise ValueError("Document type not found")
        vector_store_ids = [dt.vector_store.oai_vs_id]
    else:
        vector_store_ids = list(
            DocumentType.objects.filter(vector_store__isnull=False)
            .values_list("vector_store__oai_vs_id", flat=True)
            .distinct()
        )
        if not vector_store_ids:
            raise ValueError("No vector stores configured")

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

    filter_obj: dict[str, Any] | None
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
                results.append(
                    {
                        "text": c.text,
                        "type": c.type,
                        "filename": item.filename,
                        "score": item.score,
                        "attributes": item.attributes,
                    }
                )

    if sort == "date_desc":
        results.sort(
            key=lambda r: r.get("attributes", {}).get("date") or "",
            reverse=True,
        )
    else:
        results.sort(key=lambda r: r.get("score", 0), reverse=True)
    page = results[offset:offset + limit]
    has_more = len(results) > offset + limit
    return {"data": page, "has_more": has_more}


__all__ = [
    "list_document_types",
    "document_counts",
    "list_documents",
    "search_documents",
]
