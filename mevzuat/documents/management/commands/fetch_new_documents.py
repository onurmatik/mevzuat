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

        found_offset = None
        for offset in range(1, max_offset + 1):
            url = fetcher.build_next_document_url(offset=offset)
            try:
                resp = requests.head(url, timeout=15)
                if resp.status_code == 200:
                    found_offset = offset
                    break
            except requests.RequestException:
                # If the request fails, try the next offset
                continue

        if found_offset is None:
            self.stdout.write(self.style.WARNING("No new document found"))
            return

        new_no = last_doc.metadata["mevzuat_no"] + found_offset
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
