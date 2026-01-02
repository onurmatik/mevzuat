from django.contrib import admin, messages
from django.db.models import Q
from .models import Document, VectorStore, DocumentType


@admin.register(VectorStore)
class VectorStoreAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'name')


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'slug', 'active', 'fetcher', 'document_count', 'vector_store')
    list_editable = ('fetcher', 'active')


class HasPdfFilter(admin.SimpleListFilter):
    title = "Has pdf?"
    parameter_name = "has_pdf"

    def lookups(self, request, model_admin):
        return (("yes", "Yes"), ("no", "No"))

    def queryset(self, request, queryset):
        val = self.value()
        if val == "yes":
            return queryset.exclude(document="").exclude(document__isnull=True)
        if val == "no":
            return queryset.filter(Q(document="") | Q(document__isnull=True))
        return queryset


class HasMdFilter(admin.SimpleListFilter):
    title = "Has md?"
    parameter_name = "has_md"

    def lookups(self, request, model_admin):
        return (("yes", "Yes"), ("no", "No"))

    def queryset(self, request, queryset):
        val = self.value()
        if val == "yes":
            return queryset.exclude(markdown="").exclude(markdown__isnull=True)
        if val == "no":
            return queryset.filter(Q(markdown="") | Q(markdown__isnull=True))
        return queryset


class FileSizeFilter(admin.SimpleListFilter):
    title = "File size"
    parameter_name = "file_size_bucket"

    ONE_MB = 1024 * 1024

    def lookups(self, request, model_admin):
        return (
            ("lt1", "< 1MB"),
            ("1to5", "1–5MB"),
            ("5to10", "5–10MB"),
            ("10to20", "10–20MB"),
            ("gt20", "> 20MB"),
            ("unknown", "Unknown / unset"),
        )

    def queryset(self, request, queryset):
        val = self.value()
        if val == "lt1":
            return queryset.filter(file_size__lt=self.ONE_MB)
        if val == "1to5":
            return queryset.filter(file_size__gte=self.ONE_MB, file_size__lt=5 * self.ONE_MB)
        if val == "5to10":
            return queryset.filter(file_size__gte=5 * self.ONE_MB, file_size__lt=10 * self.ONE_MB)
        if val == "10to20":
            return queryset.filter(file_size__gte=10 * self.ONE_MB, file_size__lt=20 * self.ONE_MB)
        if val == "gt20":
            return queryset.filter(file_size__gte=20 * self.ONE_MB)
        if val == "unknown":
            return queryset.filter(file_size__isnull=True)
        return queryset


class MarkdownStatusFilter(admin.SimpleListFilter):
    title = "Markdown status"
    parameter_name = "markdown_status"

    def lookups(self, request, model_admin):
        choices = getattr(Document, "MARKDOWN_STATUS_CHOICES", ())
        return list(choices) + [("unset", "Unset")]

    def queryset(self, request, queryset):
        val = self.value()
        if val == "unset":
            return queryset.filter(Q(markdown_status="") | Q(markdown_status__isnull=True))
        if val == "null":
            return queryset.filter(markdown_status__isnull=True)
        if val:
            return queryset.filter(markdown_status=val)
        return queryset


class InVectorStoreFilter(admin.SimpleListFilter):
    title = "In vector store?"
    parameter_name = "in_vs"

    def lookups(self, request, model_admin):
        return (("yes", "Yes"), ("no", "No"))

    def queryset(self, request, queryset):
        val = self.value()
        if val == "yes":
            return queryset.exclude(oai_file_id="").exclude(oai_file_id__isnull=True)
        if val == "no":
            return queryset.filter(Q(oai_file_id="") | Q(oai_file_id__isnull=True))
        return queryset


class MevzuatTurFilter(admin.SimpleListFilter):
    title = "Mevzuat tur"
    parameter_name = "mevzuat_tur"

    def lookups(self, request, model_admin):
        values = (
            Document.objects.values_list("metadata__mevzuat_tur", flat=True)
            .distinct()
            .order_by("metadata__mevzuat_tur")
        )
        return [(v, str(v)) for v in values if v not in (None, "")]

    def queryset(self, request, queryset):
        val = self.value()
        if val:
            return queryset.filter(metadata__mevzuat_tur=int(val))
        return queryset


class MevzuatTertipFilter(admin.SimpleListFilter):
    title = "Mevzuat tertip"
    parameter_name = "mevzuat_tertip"

    def lookups(self, request, model_admin):
        values = (
            Document.objects.values_list("metadata__mevzuat_tertip", flat=True)
            .distinct()
            .order_by("metadata__mevzuat_tertip")
        )
        return [(v, str(v)) for v in values if v not in (None, "")]

    def queryset(self, request, queryset):
        val = self.value()
        if val:
            return queryset.filter(metadata__mevzuat_tertip=int(val))
        return queryset


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "mevzuat_tur",
        "mevzuat_tertip",
        "mevzuat_no",
        "type",
        "file_size",
        "date",
        "created_at",
        "has_pdf",
        "in_vs",
        "has_md",
        "markdown_status",
    )
    list_filter = (
        "type",
        "date",
        MevzuatTurFilter,
        MevzuatTertipFilter,
        HasPdfFilter,
        InVectorStoreFilter,
        HasMdFilter,
        FileSizeFilter,
        MarkdownStatusFilter,
    )
    search_fields = ("uuid", "metadata__mevzuat_no", "title")
    actions = (
        "fetch_document",
        "sync_with_vectorstore",
        "convert_to_markdown",
        "convert_to_markdown_force_ocr",
        "check_markdown_health",
        "set_file_sizes",
        "generate_embeddings",
    )

    def mevzuat_no(self, obj):
        return obj.metadata.get("mevzuatNo")

    def mevzuat_tertip(self, obj):
        return obj.metadata.get("mevzuatTertip")

    def mevzuat_tur(self, obj):
        return obj.metadata.get("mevzuatTur")

    @admin.display(boolean=True, description="Has pdf?", ordering="document")
    def has_pdf(self, obj: Document) -> bool:
        return bool(obj.document)

    @admin.display(boolean=True, description="Has md?")
    def has_md(self, obj: Document) -> bool:
        return bool(obj.markdown)

    @admin.display(boolean=True, description="In VS?")
    def in_vs(self, obj: Document) -> bool:
        return bool(obj.oai_file_id)

    def fetch_document(self, request, queryset):
        ok = 0
        errors = []
        for obj in queryset:
            try:
                obj.fetch_and_store_document(overwrite=True)
                ok += 1
            except Exception as exc:  # pragma: no cover - defensive
                errors.append((obj, exc))

        if ok:
            self.message_user(
                request,
                f"Successfully fetched {ok} document(s).",
                level=messages.SUCCESS,
            )
        for obj, exc in errors:
            self.message_user(
                request,
                f"{obj.title} could not be fetched: {exc}",
                level=messages.ERROR,
            )

    def _convert_documents_to_markdown(
            self,
            request,
            queryset,
            *,
            overwrite: bool,
            force_ocr: bool,
            success_text: str,
    ):
        ok = 0
        errors = []
        for obj in queryset:
            try:
                obj.convert_pdf_to_markdown(overwrite=overwrite, force_ocr=force_ocr)
                ok += 1
            except Exception as exc:  # pragma: no cover - defensive
                failure_status = getattr(obj, "MARKDOWN_STATUS_FAILED", "failed")
                obj.markdown_status = failure_status
                obj.save(update_fields=["markdown_status"])
                errors.append((obj, exc))
        if ok:
            self.message_user(
                request,
                success_text.format(count=ok),
                level=messages.SUCCESS,
            )
        for obj, exc in errors:
            self.message_user(
                request,
                f"{obj.title} could not be converted: {exc}",
                level=messages.ERROR,
            )

    def convert_to_markdown(self, request, queryset):
        self._convert_documents_to_markdown(
            request,
            queryset,
            overwrite=False,
            force_ocr=False,
            success_text="Successfully converted {count} document(s).",
        )

    def convert_to_markdown_force_ocr(self, request, queryset):
        self._convert_documents_to_markdown(
            request,
            queryset,
            overwrite=True,
            force_ocr=True,
            success_text="Successfully re-converted {count} document(s) with OCR.",
        )

    def check_markdown_health(self, request, queryset):
        flagged = 0
        skipped = 0
        warning = getattr(Document, "MARKDOWN_STATUS_WARNING", "warning")
        for obj in queryset:
            if not obj.markdown:
                skipped += 1
                continue
            if obj.has_markdown_glyph_artifacts():
                if obj.markdown_status != warning:
                    obj.markdown_status = warning
                    obj.save(update_fields=["markdown_status"])
                flagged += 1
        if flagged:
            self.message_user(
                request,
                f"Marked {flagged} document(s) for markdown review due to glyph artifacts.",
                level=messages.WARNING,
            )
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} document(s) because no markdown is stored.",
                level=messages.INFO,
            )
        if not flagged and not skipped:
            self.message_user(
                request,
                "Checked documents and found no glyph artifacts in markdown.",
                level=messages.SUCCESS,
            )

    def set_file_sizes(self, request, queryset):
        """Populate missing file_size for selected documents."""
        updated = 0
        missing = 0
        errors = []
        for obj in queryset:
            if not obj.document:
                missing += 1
                continue
            if obj.file_size:
                continue
            try:
                obj.file_size = obj.document.size
                obj.save(update_fields=["file_size"])
                updated += 1
            except Exception as exc:  # pragma: no cover - defensive
                errors.append((obj, exc))

        if updated:
            self.message_user(
                request,
                f"Updated file size for {updated} document(s).",
                level=messages.SUCCESS,
            )
        if missing:
            self.message_user(
                request,
                f"{missing} document(s) skipped because no PDF is stored.",
                level=messages.WARNING,
            )
        for obj, exc in errors:
            self.message_user(
                request,
                f"{obj.title} could not update size: {exc}",
                level=messages.ERROR,
            )

    def sync_with_vectorstore(self, request, queryset):
        ok = 0
        errors = []
        for obj in queryset:
            try:
                obj.sync_with_vectorstore()
                ok += 1
            except Exception as exc:  # pragma: no cover - defensive
                errors.append((obj, exc))
        if ok:
            self.message_user(
                request,
                f"Successfully synced {ok} document(s).",
                level=messages.SUCCESS,
            )
        for obj, exc in errors:
            self.message_user(
                request,
                f"{obj.title} could not be synced: {exc}",
                level=messages.ERROR,
            )

    def generate_embeddings(self, request, queryset):
        """Generate embeddings for selected documents."""
        ok = 0
        skipped = 0
        errors = []
        for obj in queryset:
            if not obj.markdown:
                skipped += 1
                continue
            try:
                obj.generate_embedding()
                ok += 1
            except Exception as exc:  # pragma: no cover - defensive
                errors.append((obj, exc))
        if ok:
            self.message_user(
                request,
                f"Successfully generated embeddings for {ok} document(s).",
                level=messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} document(s) because no markdown is stored.",
                level=messages.WARNING,
            )
        for obj, exc in errors:
            self.message_user(
                request,
                f"{obj.title} could not generate embedding: {exc}",
                level=messages.ERROR,
            )
