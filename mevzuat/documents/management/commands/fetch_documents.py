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
            self.stdout.write(self.style.SUCCESS("No documents to fetch."))
            return

        for doc in queryset.iterator():
            doc.fetch_and_store_document()
            self.stdout.write(f"Fetched document {doc.pk}")

        self.stdout.write(self.style.SUCCESS(f"Fetched {total} documents."))
