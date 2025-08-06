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

from mevzuat.documents.models import Mevzuat  # noqa: E402


server = Server("mevzuat")


@server.list_resources()
async def list_resources() -> list[types.Resource]:
    """Return all Mevzuat entries as MCP resources."""
    resources: list[types.Resource] = []
    for doc in Mevzuat.objects.all():
        uri = f"mevzuat://{doc.uuid}"
        resources.append(
            types.Resource(uri=uri, description=doc.name, mimeType="application/json")
        )
    return resources


@server.read_resource()
async def read_resource(uri: AnyUrl):
    """Return a JSON description of the requested Mevzuat record."""
    parsed = urlparse(str(uri))
    identifier = parsed.netloc or parsed.path.lstrip("/")
    doc = Mevzuat.objects.get(uuid=identifier)
    data = {
        "uuid": str(doc.uuid),
        "name": doc.name,
        "mevzuat_no": doc.mevzuat_no,
        "mevzuat_tur": doc.mevzuat_tur,
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
