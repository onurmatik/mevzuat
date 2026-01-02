from django.core.management.base import BaseCommand
from django.db.models import Q

from ...models import Document


class Command(BaseCommand):
    """Fetch and store missing document files for active document types."""

    help = "Fetch missing document files for active document types"

    def handle(self, *args, **options):
        queryset = Document.objects.filter(type__active=True).filter(
            Q(document__isnull=True) | Q(document="")
        )

        total = queryset.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No documents to download."))
            return

        for doc in queryset.iterator():
            doc.fetch_and_store_document()
            self.stdout.write(f"Downloaded document {doc.pk}")
            try:
                doc.convert_pdf_to_markdown(overwrite=False)
            except Exception as exc:  # pragma: no cover - defensive
                failure_status = getattr(doc, "MARKDOWN_STATUS_FAILED", "failed")
                doc.markdown_status = failure_status
                doc.save(update_fields=["markdown_status"])
                self.stderr.write(
                    f"Markdown conversion failed for document {doc.pk}: {exc}"
                )

        self.stdout.write(self.style.SUCCESS(f"Downloaded {total} documents."))
