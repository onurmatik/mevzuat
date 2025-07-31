from django.contrib import admin
from django.utils.html import format_html
from django.contrib import admin, messages

from .models import Mevzuat


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
        "mukerrer",
        "has_old_law",
        "pdf_link",
        "has_document",
    )
    list_filter = (
        "mevzuat_tur",
        "mukerrer",
        "has_old_law",
        ("kabul_tarih", admin.DateFieldListFilter),
        ("resmi_gazete_tarihi", admin.DateFieldListFilter),
    )
    search_fields = ("mevzuat_no", "name")
    ordering = ("-resmi_gazete_tarihi", "-kabul_tarih")
    actions = ("fetch_selected_documents",)

    @admin.display(boolean=True, description="Has document?", ordering="document")
    def has_document(self, obj: Mevzuat) -> bool:
        return bool(obj.document)

    @admin.action(description="Fetch and attach PDF for selected Mevzuat")
    def fetch_selected_documents(self, request, queryset):
        ok, failed = 0, 0
        for obj in queryset:
            obj.fetch_and_store_document(overwrite=False)

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
