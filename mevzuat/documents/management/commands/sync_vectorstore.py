from django.core.management.base import BaseCommand
from django.db.models import Q

from ...models import Document


class Command(BaseCommand):
    """Synchronise documents with the vector store."""

    help = "Sync documents lacking a vector store file id"

    def handle(self, *args, **options):
        queryset = Document.objects.filter(type__active=True).filter(
            Q(oai_file_id__isnull=True) | Q(oai_file_id="")
        )

        total = queryset.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No documents to sync."))
            return

        for doc in queryset.iterator():
            doc.sync_with_vectorstore()
            self.stdout.write(f"Synced document {doc.pk}")

        self.stdout.write(self.style.SUCCESS(f"Synced {total} documents."))
