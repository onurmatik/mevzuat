from datetime import date
import requests

from django.core.management.base import BaseCommand, CommandError

from ...models import Document, DocumentType


class Command(BaseCommand):
    """Fetch the next document for a given document type."""

    help = "Fetch a new document for the provided document type slug"

    def add_arguments(self, parser):
        parser.add_argument("slug", help="DocumentType slug")
        parser.add_argument(
            "--max-offset",
            type=int,
            default=10,
            help="How many sequential IDs to try when looking for the next document",
        )

    def handle(self, *args, **options):
        slug = options["slug"]
        max_offset = options["max_offset"]

        try:
            doc_type = DocumentType.objects.get(slug=slug)
        except DocumentType.DoesNotExist as exc:
            raise CommandError(f"Document type not found: {slug}") from exc

        fetcher = doc_type._fetcher()
        last_doc = doc_type.last_document()
        if not last_doc:
            raise CommandError("No existing document found for this type")

        default_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.mevzuat.gov.tr/",
            "Connection": "keep-alive",
        }

        found_offset = None
        for offset in range(1, max_offset + 1):
            url = fetcher.build_next_document_url(offset=offset)
            try:
                resp = requests.head(url, headers=default_headers)
                resp.raise_for_status()
            except requests.HTTPError as exc:
                if exc.response is not None and exc.response.status_code == 404:
                    # Document not found, try the next offset
                    continue
                raise
            except requests.RequestException as exc:
                raise CommandError(f"Failed to request {url}") from exc
            else:
                found_offset = offset
                break

        if found_offset is None:
            self.stdout.write(self.style.WARNING("No new document found"))
            return

        new_no = int(last_doc.metadata["mevzuat_no"]) + found_offset
        metadata = {
            "mevzuat_tur": last_doc.metadata["mevzuat_tur"],
            "mevzuat_tertib": last_doc.metadata["mevzuat_tertib"],
            "mevzuat_no": new_no,
            "resmi_gazete_tarihi": date.today().isoformat(),
        }

        title = f"{doc_type.name} {new_no}"
        doc = Document.objects.create(type=doc_type, title=title, metadata=metadata)
        doc.fetch_and_store_document()

        self.stdout.write(self.style.SUCCESS(f"Fetched document {doc.uuid}"))
