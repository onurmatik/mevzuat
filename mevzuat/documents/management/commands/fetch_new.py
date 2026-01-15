from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from ...models import DocumentType, Document
from scripts.mevzuat_scraper import fetch_documents


class Command(BaseCommand):
    """Fetch and process the latest documents for all active ``DocumentType`` instances."""

    help = (
        "Fetch latest documents and process them (download, markdown, embeddings, "
        "summary, keywords, translation) for active document types"
    )

    def handle(self, *args, **options):
        doc_types = DocumentType.objects.filter(active=True)
        if not doc_types.exists():
            self.stdout.write(self.style.WARNING("No active document types found."))
            return

        created_doc_ids = []

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
                doc, was_created = Document.objects.get_or_create(
                    type=doc_type,
                    metadata=row,
                )
                if was_created:
                    created += 1
                    created_doc_ids.append(doc.pk)

            self.stdout.write(
                self.style.SUCCESS(
                    f"{doc_type.slug}: Processed {len(rows)} items – {created} new documents created."
                )
            )

        if not created_doc_ids:
            self.stdout.write(self.style.SUCCESS("No new documents created."))
            return

        new_docs = Document.objects.filter(pk__in=created_doc_ids)
        total_new = len(created_doc_ids)
        self.stdout.write(self.style.SUCCESS(f"Processing {total_new} new documents..."))

        self._download_documents(new_docs)
        self._convert_to_markdown(new_docs)
        self._summarize_documents(new_docs)
        self._extract_keywords(new_docs)
        self._generate_embeddings(new_docs)
        self._translate_documents(new_docs)

    def _download_documents(self, queryset):
        to_download = queryset.filter(Q(document__isnull=True) | Q(document=""))
        total = to_download.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No new documents to download."))
            return

        errors = 0
        for doc in to_download.iterator():
            try:
                doc.fetch_and_store_document()
            except Exception as exc:  # pragma: no cover - defensive
                errors += 1
                self.stderr.write(f"Download failed for document {doc.pk}: {exc}")

        downloaded = total - errors
        if downloaded:
            self.stdout.write(
                self.style.SUCCESS(f"Downloaded {downloaded}/{total} documents.")
            )
        if errors:
            self.stderr.write(
                self.style.ERROR(f"{errors} document(s) failed to download.")
            )

    def _convert_to_markdown(self, queryset):
        missing_markdown = Q(markdown__isnull=True) | Q(markdown="")
        missing_document = Q(document__isnull=True) | Q(document="")
        to_convert = queryset.filter(missing_markdown).exclude(missing_document)
        total = to_convert.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No new documents to convert to markdown."))
            return

        errors = 0
        for doc in to_convert.iterator():
            try:
                doc.convert_pdf_to_markdown(overwrite=False)
            except Exception as exc:  # pragma: no cover - defensive
                errors += 1
                failure_status = getattr(doc, "MARKDOWN_STATUS_FAILED", "failed")
                doc.markdown_status = failure_status
                doc.save(update_fields=["markdown_status"])
                self.stderr.write(
                    f"Markdown conversion failed for document {doc.pk}: {exc}"
                )

        converted = total - errors
        if converted:
            self.stdout.write(
                self.style.SUCCESS(f"Converted {converted}/{total} documents to markdown.")
            )
        if errors:
            self.stderr.write(
                self.style.ERROR(f"{errors} document(s) failed markdown conversion.")
            )

    def _generate_embeddings(self, queryset):
        missing_markdown = Q(markdown__isnull=True) | Q(markdown="")
        to_embed = queryset.filter(embedding__isnull=True).exclude(missing_markdown)
        total = to_embed.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No new documents need embeddings."))
            return

        errors = 0
        for doc in to_embed.iterator():
            try:
                doc.generate_embedding(overwrite=False)
            except Exception as exc:  # pragma: no cover - defensive
                errors += 1
                self.stderr.write(f"Embedding failed for document {doc.pk}: {exc}")

        embedded = total - errors
        if embedded:
            self.stdout.write(
                self.style.SUCCESS(f"Generated embeddings for {embedded}/{total} documents.")
            )
        if errors:
            self.stderr.write(
                self.style.ERROR(f"{errors} document(s) failed embedding generation.")
            )

    def _summarize_documents(self, queryset):
        missing_markdown = Q(markdown__isnull=True) | Q(markdown="")
        missing_summary = Q(summary__isnull=True) | Q(summary="")
        to_summarize = queryset.filter(missing_summary).exclude(missing_markdown)
        total = to_summarize.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No new documents need summaries."))
            return

        errors = 0
        for doc in to_summarize.iterator():
            try:
                doc.summarize(overwrite=False)
            except Exception as exc:  # pragma: no cover - defensive
                errors += 1
                self.stderr.write(f"Summary failed for document {doc.pk}: {exc}")

        summarized = total - errors
        if summarized:
            self.stdout.write(
                self.style.SUCCESS(f"Generated summaries for {summarized}/{total} documents.")
            )
        if errors:
            self.stderr.write(
                self.style.ERROR(f"{errors} document(s) failed summary generation.")
            )

    def _extract_keywords(self, queryset):
        missing_summary = Q(summary__isnull=True) | Q(summary="")
        missing_keywords = Q(keywords__isnull=True) | Q(keywords=[])
        to_extract = queryset.filter(missing_keywords).exclude(missing_summary)
        total = to_extract.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No new documents need keywords."))
            return

        errors = 0
        for doc in to_extract.iterator():
            try:
                doc.extract_keywords(overwrite=False)
            except Exception as exc:  # pragma: no cover - defensive
                errors += 1
                self.stderr.write(f"Keyword extraction failed for document {doc.pk}: {exc}")

        extracted = total - errors
        if extracted:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Generated keywords for {extracted}/{total} documents."
                )
            )
        if errors:
            self.stderr.write(
                self.style.ERROR(f"{errors} document(s) failed keyword extraction.")
            )

    def _translate_documents(self, queryset):
        missing_title = Q(title_en__isnull=True) | Q(title_en="")
        missing_summary_en = Q(summary_en__isnull=True) | Q(summary_en="")
        missing_keywords_en = Q(keywords_en__isnull=True) | Q(keywords_en=[])
        has_summary = Q(summary__isnull=False) & ~Q(summary="")
        has_keywords = Q(keywords__isnull=False) & ~Q(keywords=[])

        needs_title = missing_title
        needs_summary = has_summary & missing_summary_en
        needs_keywords = has_keywords & missing_keywords_en
        to_translate = queryset.filter(needs_title | needs_summary | needs_keywords)
        total = to_translate.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No new documents need translations."))
            return

        errors = 0
        for doc in to_translate.iterator():
            try:
                doc.translate(overwrite=False)
            except Exception as exc:  # pragma: no cover - defensive
                errors += 1
                self.stderr.write(f"Translation failed for document {doc.pk}: {exc}")

        translated = total - errors
        if translated:
            self.stdout.write(
                self.style.SUCCESS(f"Generated translations for {translated}/{total} documents.")
            )
        if errors:
            self.stderr.write(
                self.style.ERROR(f"{errors} document(s) failed translation.")
            )
