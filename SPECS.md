# Mevzuat.info Functional Specification

## Overview
Mevzuat.info is a Django-based service that collects Turkish legislation
documents from mevzuat.gov.tr, stores the original PDFs plus derived metadata,
and exposes search and discovery tools via web UI, REST APIs, RSS, and an MCP
server. It also integrates with OpenAI vector stores to support semantic search
and document retrieval.

## Goals
- Ingest and catalog official legislation documents with reliable metadata.
- Persist original PDFs and optional Markdown conversions.
- Provide search and discovery via UI, API, RSS, and MCP tools.
- Support semantic search via local embeddings.
- Offer admin workflows for bulk processing and data hygiene.

## Non-goals
- Full-text search stored locally in the database (search uses pgvector).
- Automated metadata enrichment beyond the source payload (fetcher metadata
  extraction is currently a stub).
- A dedicated frontend app (UI is server-rendered Django templates).

## Primary users and actors
- Public visitors: view recent documents, search, and read document details.
- API consumers: use JSON endpoints to list, count, and search documents.
- Admin users: manage document types and ingestion workflows.
- MCP clients: access the same data programmatically through tools.

## User-facing features
### Web UI
- Home page
  - Lists five most recent documents by date.
  - Shows a stacked bar chart of document counts by type and time range.
  - Exposes quick links to API and MCP docs.
- Search page
  - Keyword search backed by pgvector.
  - Filters by type and date range (predefined or custom).
  - Infinite scroll for results and sortable ordering (relevance or date).
  - Summary panel with result counts by type and month.
- Document detail page
  - Shows metadata (title, date, type, UUID, created time).
  - Links to the original PDF (if available).
  - Displays Markdown conversion when present.
- RSS
  - `/rss/latest/` exposes the 20 most recently created documents.

### Admin interface
- Manage `DocumentType` entries.
- Document list filters for:
  - Presence of PDF and Markdown

  - Markdown status (success, warning, failed, unset)
  - File size buckets
  - Mevzuat type and tertip from metadata
- Admin actions:
  - Fetch PDFs (overwrite existing)
  - Convert PDFs to Markdown (with or without forced OCR)
  - Check Markdown for glyph artifacts and flag warnings
  - Set missing file sizes


## API surface (Django Ninja)
Base path: `/api/documents`

- `GET /types`
  - Returns document types.
- `GET /counts`
  - Returns counts grouped by day, month, or year.
  - Filters by `start_date` and `end_date`.
- `GET /list`
  - Returns documents filtered by type and date criteria.
  - Date filters precedence: `date`, then `start_date`/`end_date`, then
    `year`/`month`.
- `GET /search`
  - Searches documents using similar embeddings.
  - Supports type and date filters.

## MCP server
FastMCP server (stateless HTTP) exposes the same data as tools:
- `types` -> list document types
- `counts` -> document counts by interval
- `list` -> list documents with filters
- `search` -> semantic search for documents

The MCP server is started via `python -m mevzuat.mcp_server` and requires
Django settings to be configured in the environment.

## Data model


### DocumentType
- `name`, `short_name`, `slug`, `description`.
- `active`: controls whether ingestion and sync include this type.

- `fetcher`: class name for the document fetcher.

### Document
- `uuid`: public identifier.
- `type`: FK to DocumentType.
- `title`: derived from `metadata.mevAdi` when present.
- `date`: derived from `metadata.resmiGazeteTarihi` (dd.mm.yyyy or dd/mm/yyyy).
- `document`: stored PDF file.
- `file_size`: size in bytes.
- `markdown`: Markdown conversion of the PDF.
- `markdown_status`: success, warning, failed, or unset.
- `oai_file_id`: OpenAI file id for the uploaded PDF (unused).
- `embedding`: pgvector field (currently unused in search).
- `metadata`: raw JSON payload from mevzuat.gov.tr.
- `created_at`: ingestion timestamp.

## Ingestion and processing pipeline
### Fetchers
Fetchers are registered by class name and referenced by `DocumentType.fetcher`.
They build PDF URLs and define request parameters for the mevzuat.gov.tr
datatable endpoint. Key fetchers include:
- `KanunFetcher`, `KHKFetcher`, `CBKararnameFetcher`, `CBKararFetcher`,
  `CBYonetmelikFetcher`, `CBGenelgeFetcher`, `YonetmelikFetcher`.

### End-to-end ingest
Management command: `fetch_new`
- For each active `DocumentType`, calls `scripts.mevzuat_scraper.fetch_documents`.
- Creates `Document` rows with raw metadata.
- For newly created documents:
  - Downloads and stores PDFs.
  - Converts PDFs to Markdown.
  - Generates embeddings.
  - Generates summaries.
  - Generates translations.

### Backfill and maintenance
Management command: `download_documents`
- Finds active documents without stored PDFs.
- Downloads PDFs based on fetcher URL patterns and stores them on disk/S3.
- Converts PDFs to Markdown after download.

Management command: `generate_embeddings`
- Generates embeddings for documents with Markdown content.

Admin actions and API endpoints
- Convert PDFs to Markdown (admin action and model method: `convert_pdf_to_markdown`).
- Summaries and translations (admin actions, and `POST /api/documents/{uuid}/summarize` / `translate`).



## Scripts and operations
- `scripts/mevzuat_scraper.py`: fetches first-page data with auto anti-forgery
  handling.
- `scripts/mevzuat_json_fetcher.py`: full dataset fetch that requires manual
  cookie and anti-forgery values.
- `scripts/mevzuat_fetcher.py`: bulk PDF downloader by code/order/no.
- `scripts/update_metadata.py`: restores original metadata for existing docs.
- `scripts/set_rds_local_ip.sh`: updates AWS security group for local DB access.

## Storage and deployment
- Database:
  - PostgreSQL via `RDS_HOST` (and `RDS_NAME`, `RDS_USER`, `RDS_PASSWORD`), or
  - SQLite for local development.
- File storage:
  - Local `MEDIA_ROOT` by default, or
  - S3 via `AWS_STORAGE_BUCKET_NAME` using django-storages.
- External services:
  - mevzuat.gov.tr for source metadata and PDFs.
  - OpenAI for embedding generation and translation.

## Error handling and edge cases
- If a PDF is missing or the URL is invalid, download fails with a request
  exception.

- Markdown conversion marks warnings when glyph artifacts are detected and will
  re-run with OCR if needed.
- Some scripts require manually refreshed cookies/tokens from the source site.
