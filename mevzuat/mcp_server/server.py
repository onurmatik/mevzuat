"""FastMCP server exposing document tools."""

from __future__ import annotations

from fastmcp.server import FastMCP

from .handlers import (
    document_counts,
    list_document_types,
    list_documents,
    search_documents,
)

server = FastMCP("mevzuat", stateless_http=True)

server.tool(list_document_types)
server.tool(document_counts)
server.tool(list_documents)
server.tool(search_documents)


def run() -> None:
    """Run the FastMCP server."""
    server.run()


app = server.http_app(path="/")
