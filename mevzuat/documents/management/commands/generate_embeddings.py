"""
Management command to generate embeddings for documents.

Usage:
    python manage.py generate_embeddings [--limit N] [--batch-size N] [--overwrite]
"""
from django.core.management.base import BaseCommand
from mevzuat.documents.models import Document


class Command(BaseCommand):
    help = "Generate embeddings for documents that don't have them yet"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of documents to process",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=10,
            help="Number of documents to process before printing progress",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Regenerate embeddings even for documents that already have them",
        )
        parser.add_argument(
            "--type",
            type=str,
            default=None,
            help="Only process documents of this type (slug)",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        batch_size = options["batch_size"]
        overwrite = options["overwrite"]
        doc_type = options["type"]

        # Build queryset
        qs = Document.objects.filter(markdown__isnull=False).exclude(markdown="")

        if not overwrite:
            qs = qs.filter(embedding__isnull=True)

        if doc_type:
            qs = qs.filter(type__slug=doc_type)

        qs = qs.order_by("-date", "-id")

        if limit:
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write(f"Found {total} documents to process")

        if total == 0:
            self.stdout.write(self.style.SUCCESS("No documents need embedding generation"))
            return

        processed = 0
        errors = 0

        for doc in qs.iterator():
            try:
                doc.generate_embedding(overwrite=overwrite)
                processed += 1

                if processed % batch_size == 0:
                    self.stdout.write(f"Processed {processed}/{total} documents...")

            except Exception as e:
                errors += 1
                self.stderr.write(
                    self.style.ERROR(f"Error processing document {doc.id}: {e}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Processed {processed} documents with {errors} errors."
            )
        )
