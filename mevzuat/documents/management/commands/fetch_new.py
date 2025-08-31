from django.core.management.base import BaseCommand, CommandError

from ...models import DocumentType, Document
from scripts.mevzuat_scraper import fetch_documents


class Command(BaseCommand):
    """Fetch the latest documents for all active ``DocumentType`` instances."""

    help = "Fetch latest documents and create Document instances for active document types"

    def handle(self, *args, **options):
        doc_types = DocumentType.objects.filter(active=True)
        if not doc_types.exists():
            self.stdout.write(self.style.WARNING("No active document types found."))
            return

        for doc_type in doc_types:
            fetcher = doc_type._fetcher()
            params = getattr(fetcher, "request_params", None)
            if params is None:
                raise CommandError(
                    f"Fetcher '{doc_type.fetcher}' does not define request_params"
                )

            rows = fetch_documents(params)

            created = 0
            for row in rows:
                _, was_created = Document.objects.get_or_create(
                    type=doc_type,
                    metadata=row,
                )
                if was_created:
                    created += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"{doc_type.slug}: Processed {len(rows)} items – {created} new documents created."
                )
            )
