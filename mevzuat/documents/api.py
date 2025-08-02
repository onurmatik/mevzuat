from typing import Optional

from django.conf import settings
from ninja import Router, Schema
from openai import OpenAI


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
