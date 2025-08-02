from typing import Optional

from ninja import Router, Schema
from openai import OpenAI


router = Router()


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
