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
        "date",
        "created_at",
        "has_pdf",
        "in_vs",
        "has_md",
    )
    list_filter = (
        "type",
        "date",
        MevzuatTurFilter,
        MevzuatTertipFilter,
        HasPdfFilter,
        InVectorStoreFilter,
        HasMdFilter,
    )
    search_fields = ("metadata__mevzuat_no", "title")
    actions = (
        "fetch_document",
        "sync_with_vectorstore",
        "convert_to_markdown",
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

    def convert_to_markdown(self, request, queryset):
        ok = 0
        errors = []
        for obj in queryset:
            try:
                obj.convert_pdf_to_markdown(overwrite=False)
                ok += 1
            except Exception as exc:  # pragma: no cover - defensive
                errors.append((obj, exc))
        if ok:
            self.message_user(
                request,
                f"Successfully converted {ok} document(s).",
                level=messages.SUCCESS,
            )
        for obj, exc in errors:
            self.message_user(
                request,
                f"{obj.title} could not be converted: {exc}",
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
