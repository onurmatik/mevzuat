from django.core.management.base import BaseCommand, CommandError

from ...models import DocumentType, Document
from scripts.mevzuat_scraper import fetch_documents


class Command(BaseCommand):
    """Fetch the latest documents for a given ``DocumentType``."""

    help = "Fetch latest documents and create Document instances if missing"

    def add_arguments(self, parser):
        parser.add_argument("slug", help="Slug of the DocumentType")

    def handle(self, *args, **options):
        slug = options["slug"]
        try:
            doc_type = DocumentType.objects.get(slug=slug)
        except DocumentType.DoesNotExist:
            raise CommandError(f"DocumentType with slug '{slug}' not found")

        fetcher = doc_type._fetcher()
        params = getattr(fetcher, "request_params", None)
        if params is None:
            raise CommandError(f"Fetcher '{doc_type.fetcher}' does not define request_params")

        rows = fetch_documents(params)

        created = 0
        for row in rows:
            title = (
                row.get("title")
                or row.get("baslik")
                or row.get("mevzuat_basligi")
                or ""
            )

            lookup = {
                "type": doc_type,
                "metadata__mevzuat_tur": row.get("mevzuat_tur"),
                "metadata__mevzuat_tertib": row.get("mevzuat_tertib"),
                "metadata__mevzuat_no": row.get("mevzuat_no"),
            }
            defaults = {"title": title, "metadata": row}

            _, was_created = Document.objects.get_or_create(
                defaults=defaults, **lookup
            )
            if was_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {len(rows)} items – {created} new documents created."
            )
        )
