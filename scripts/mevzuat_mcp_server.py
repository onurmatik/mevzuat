#!/usr/bin/env python3
"""MCP server exposing Mevzuat documents."""

import asyncio
import json
import os
from urllib.parse import urlparse

from mcp.server import Server, stdio
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp import types
from pydantic import AnyUrl

# Configure Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mevzuat.settings")
import django

django.setup()

from mevzuat.documents.models import Document  # noqa: E402


server = Server("mevzuat")


@server.list_resources()
async def list_resources() -> list[types.Resource]:
    """Return all Document entries as MCP resources."""
    resources: list[types.Resource] = []
    for doc in Document.objects.all():
        uri = f"mevzuat://{doc.uuid}"
        mime = "text/markdown" if doc.markdown else "application/json"
        resources.append(
            types.Resource(uri=uri, description=doc.title, mimeType=mime)
        )
    return resources


@server.read_resource()
async def read_resource(uri: AnyUrl):
    """Return the content of the requested Document."""
    parsed = urlparse(str(uri))
    identifier = parsed.netloc or parsed.path.lstrip("/")
    doc = Document.objects.get(uuid=identifier)

    if doc.markdown:
        with open(doc.markdown.path, "r", encoding="utf-8") as f:
            content = f.read()
        return [ReadResourceContents(content=content, mime_type="text/markdown")]

    data = {
        "uuid": str(doc.uuid),
        "title": doc.title,
        "document_type": doc.type.name if doc.type else None,
        "date": doc.date.isoformat() if doc.date else None,
        "metadata": doc.metadata,
    }
    content = json.dumps(data, ensure_ascii=False)
    return [ReadResourceContents(content=content, mime_type="application/json")]


async def amain() -> None:
    init = server.create_initialization_options()
    async with stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, init)


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
