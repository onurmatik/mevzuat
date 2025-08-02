from django.contrib import admin, messages
from django.utils.html import format_html

from .models import Document, Mevzuat


class HasDocumentFilter(admin.SimpleListFilter):
    title = "Has document?"
    parameter_name = "has_document"

    def lookups(self, request, model_admin):
        return (("yes", "Yes"), ("no", "No"))

    def queryset(self, request, queryset):
        val = self.value()
        if val == "yes":
            return queryset.exclude(document="")
        if val == "no":
            return queryset.filter(document="")
        return queryset


@admin.register(Mevzuat)
class MevzuatAdmin(admin.ModelAdmin):
    list_display = (
        "mevzuat_no",
        "name_short",
        "mevzuat_tur",
        "resmi_gazete_tarihi",
        "pdf_link",
        "has_pdf",
        "has_md",
        "in_vs",
    )
    list_filter = (
        "mevzuat_tur",
        ("resmi_gazete_tarihi", admin.DateFieldListFilter),
    )
    search_fields = ("mevzuat_no", "name")
    ordering = ("-resmi_gazete_tarihi",)
    actions = (
        "fetch_selected_documents",
        "convert_selected_to_markdown",
        "upload_selected_to_vectorstore",
    )

    @admin.display(boolean=True, description="Has pdf?", ordering="document")
    def has_pdf(self, obj: Document) -> bool:
        return bool(obj.document)

    @admin.display(boolean=True, description="Has md?")
    def has_md(self, obj: Document) -> bool:
        return bool(obj.markdown)

    @admin.display(boolean=True, description="In VS?")
    def in_vs(self, obj: Document) -> bool:
        return bool(obj.oai_file_id)

    @admin.action(description="Fetch and attach PDF for selected Mevzuat")
    def fetch_selected_documents(self, request, queryset):
        ok, failed = 0, 0
        for obj in queryset:
            try:
                obj.fetch_and_store_document(overwrite=True)
                ok += 1
            except Exception:
                failed += 1

        if ok:
            self.message_user(
                request,
                f"Successfully fetched {ok} document(s).",
                level=messages.SUCCESS,
            )
        if failed:
            self.message_user(
                request,
                f"{failed} document(s) could not be fetched – see log.",
                level=messages.WARNING,
            )

    @admin.action(description="Convert stored PDF to Markdown for selected Mevzuat")
    def convert_selected_to_markdown(self, request, queryset):
        ok, failed = 0, 0
        for obj in queryset:
            try:
                obj.convert_pdf_to_markdown(overwrite=False)
                ok += 1
            except Exception:
                failed += 1
        if ok:
            self.message_user(
                request,
                f"Successfully converted {ok} document(s).",
                level=messages.SUCCESS,
            )
        if failed:
            self.message_user(
                request,
                f"{failed} document(s) could not be converted – see log.",
                level=messages.WARNING,
            )

    @admin.action(
        description="Upload document to OpenAI vector store for selected Mevzuat"
    )
    def upload_selected_to_vectorstore(self, request, queryset):
        ok, failed = 0, 0
        for obj in queryset:
            obj.upload_to_vectorstore()
        if ok:
            self.message_user(
                request,
                f"Successfully uploaded {ok} document(s).",
                level=messages.SUCCESS,
            )
        if failed:
            self.message_user(
                request,
                f"{failed} document(s) could not be uploaded – see log.",
                level=messages.WARNING,
            )

    readonly_fields = ("created_at", "pdf_link")

    def name_short(self, obj):
        """Trim long titles for the list view."""
        return (obj.name[:60] + "…") if len(obj.name) > 65 else obj.name

    name_short.short_description = "Title"

    def pdf_link(self, obj):
        """Clickable link to the original PDF (if resolvable)."""
        url = obj.original_document_url()
        return format_html('<a href="{}" target="_blank">PDF</a>', url)

    pdf_link.short_description = "Original PDF"
    pdf_link.allow_tags = True
