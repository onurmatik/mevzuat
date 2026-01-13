import logging
import string

from django.contrib import admin, messages
from django.db import connection
from django.db.models import Q, IntegerField, Value
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Coalesce
from .models import Document, DocumentType, FlaggedDocument

logger = logging.getLogger(__name__)


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'slug', 'active', 'fetcher', 'document_count')
    list_editable = ('fetcher', 'active')


@admin.register(FlaggedDocument)
class FlaggedDocumentAdmin(admin.ModelAdmin):
    list_display = ("document", "flagged_by", "flagged_at")
    list_filter = ("flagged_at", "flagged_by")
    search_fields = ("document__title", "flagged_by__username")


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


class HasEmbeddingFilter(admin.SimpleListFilter):
    title = "Has embedding?"
    parameter_name = "has_embedding"

    def lookups(self, request, model_admin):
        return (("yes", "Yes"), ("no", "No"))

    def queryset(self, request, queryset):
        val = self.value()
        if val == "yes":
            return queryset.exclude(embedding__isnull=True)
        if val == "no":
            return queryset.filter(embedding__isnull=True)
        return queryset


class HasKeywordsFilter(admin.SimpleListFilter):
    title = "Has keywords?"
    parameter_name = "has_keywords"

    def lookups(self, request, model_admin):
        return (("yes", "Yes"), ("no", "No"))

    def queryset(self, request, queryset):
        val = self.value()
        has_keywords = Q(keywords__isnull=False) & ~Q(keywords=[])
        has_keywords_en = Q(keywords_en__isnull=False) & ~Q(keywords_en=[])
        if val == "yes":
            return queryset.filter(has_keywords | has_keywords_en)
        if val == "no":
            return queryset.filter(~(has_keywords | has_keywords_en))
        return queryset




class TranslatedFilter(admin.SimpleListFilter):
    title = "Translated?"
    parameter_name = "is_translated"

    def lookups(self, request, model_admin):
        return (("yes", "Yes"), ("no", "No"))

    def queryset(self, request, queryset):
        val = self.value()
        if val == "yes":
            return queryset.exclude(title_en__isnull=True).exclude(title_en="")
        if val == "no":
            return queryset.filter(Q(title_en__isnull=True) | Q(title_en=""))
        return queryset


class SummarizedFilter(admin.SimpleListFilter):
    title = "Summarized?"
    parameter_name = "is_summarized"

    def lookups(self, request, model_admin):
        return (("yes", "Yes"), ("no", "No"))

    def queryset(self, request, queryset):
        val = self.value()
        if val == "yes":
            return queryset.exclude(summary__isnull=True).exclude(summary="")
        if val == "no":
            return queryset.filter(Q(summary__isnull=True) | Q(summary=""))
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
        "keywords_preview",
        "file_size",
        "md_length",
        "date",
        "created_at",
        "modified_at",
        "has_pdf",
        "has_md",
        "has_embedding",
        "markdown_status",
        "is_translated",
        "is_summarized",
    )
    list_filter = (
        "type",
        "date",
        "modified_at",
        MevzuatTurFilter,
        MevzuatTertipFilter,
        HasPdfFilter,
        HasMdFilter,
        HasEmbeddingFilter,
        HasKeywordsFilter,
        TranslatedFilter,
        SummarizedFilter,
        FileSizeFilter,
        MarkdownStatusFilter,
    )
    search_fields = ("uuid", "metadata__mevzuat_no", "title")
    actions = (
        "fetch_document",
        # "convert_to_markdown",
        "convert_to_markdown_force_ocr",
        "check_markdown_health",
        "mark_markdown_healthy",
        "set_file_sizes",
        "generate_embeddings",
        "summarize_documents",
        "extract_keywords",
        "translate_documents",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.GET.get("o"):
            return qs
        if connection.vendor != "postgresql":
            return qs.order_by("-date", "-id")

        mevzuat_no_text = KeyTextTransform("mevzuatNo", "metadata")
        mevzuat_no_num = Coalesce(
            Cast(mevzuat_no_text, IntegerField()),
            Value(0),
        )
        return qs.annotate(mevzuat_no_num=mevzuat_no_num).order_by(
            "-date",
            "-mevzuat_no_num",
            "-id",
        )

    def mevzuat_no(self, obj):
        return obj.metadata.get("mevzuatNo")

    def mevzuat_tertip(self, obj):
        return obj.metadata.get("mevzuatTertip")

    def mevzuat_tur(self, obj):
        return obj.metadata.get("mevzuatTur")

    def md_length(self, obj):
        return obj.markdown and len(obj.markdown) or '-'

    @admin.display(description="Keywords")
    def keywords_preview(self, obj: Document) -> str:
        def format_keywords(values):
            if not values:
                return ""
            items = [str(value).strip() for value in values if str(value).strip()]
            if not items:
                return ""
            limit = 5
            if len(items) > limit:
                return ", ".join(items[:limit]) + f" (+{len(items) - limit})"
            return ", ".join(items)

        primary = format_keywords(obj.keywords)
        # secondary = format_keywords(obj.keywords_en)
        secondary = None  # Show only TR keywords
        if primary and secondary:
            return f"{primary} / {secondary}"
        return primary or secondary or "-"

    @admin.display(boolean=True, description="Has pdf?", ordering="document")
    def has_pdf(self, obj: Document) -> bool:
        return bool(obj.document)

    @admin.display(boolean=True, description="Has md?")
    def has_md(self, obj: Document) -> bool:
        return bool(obj.markdown)

    @admin.display(boolean=True, description="Has embedding?")
    def has_embedding(self, obj: Document) -> bool:
        return obj.embedding is not None

    @admin.display(boolean=True, description="Translated?")
    def is_translated(self, obj: Document) -> bool:
        return bool(obj.title_en)

    @admin.display(boolean=True, description="Summarized?")
    def is_summarized(self, obj: Document) -> bool:
        return bool(obj.summary)

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
        reason_counts = {}
        for obj in queryset:
            if not obj.markdown:
                skipped += 1
                continue
            reasons = self._markdown_health_reasons(obj)
            if reasons:
                if obj.markdown_status != warning:
                    obj.markdown_status = warning
                    obj.save(update_fields=["markdown_status"])
                flagged += 1
                for reason in reasons:
                    reason_counts[reason] = reason_counts.get(reason, 0) + 1
        if flagged:
            reason_summary = ", ".join(
                f"{reason}={count}"
                for reason, count in sorted(
                    reason_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            )
            detail = f" Reasons: {reason_summary}." if reason_summary else ""
            self.message_user(
                request,
                f"Marked {flagged} document(s) for markdown review.{detail}",
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
                "Checked documents and found no markdown health issues.",
                level=messages.SUCCESS,
            )

    def mark_markdown_healthy(self, request, queryset):
        success_status = getattr(Document, "MARKDOWN_STATUS_SUCCESS", "success")
        updated = 0
        for obj in queryset:
            if obj.markdown_status != success_status:
                obj.markdown_status = success_status
                obj.save(update_fields=["markdown_status"])
                updated += 1
        if updated:
            self.message_user(
                request,
                f"Marked {updated} document(s) as markdown healthy.",
                level=messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                "Selected documents are already marked as healthy.",
                level=messages.INFO,
            )

    def _markdown_health_reasons(self, obj):
        text = obj.markdown or ""
        text_len = len(text)
        words = text.split()
        word_count = len(words)
        if word_count:
            avg_word_len = sum(len(word) for word in words) / word_count
            long_tokens = sum(1 for word in words if len(word) >= 30)
            long_token_ratio = long_tokens / word_count
        else:
            avg_word_len = 0
            long_token_ratio = 0

        non_ws = sum(1 for ch in text if not ch.isspace())
        alpha = sum(1 for ch in text if ch.isalpha())
        alpha_ratio = alpha / non_ws if non_ws else 0

        strip_chars = string.punctuation
        connector_chars = "-/."
        alpha_tokens = 0
        mixed_alnum_tokens = 0
        symbol_mixed_tokens = 0
        other_tokens = 0

        for token in words:
            cleaned = token.strip(strip_chars)
            if not cleaned:
                continue
            normalized = "".join(ch for ch in cleaned if ch not in connector_chars)
            if not normalized:
                continue
            has_alpha = any(ch.isalpha() for ch in normalized)
            has_digit = any(ch.isdigit() for ch in normalized)
            has_other = any(not ch.isalnum() for ch in normalized)
            if has_alpha and not has_digit and not has_other:
                alpha_tokens += 1
            elif has_alpha and has_digit:
                mixed_alnum_tokens += 1
            elif has_alpha and has_other:
                symbol_mixed_tokens += 1
            else:
                other_tokens += 1

        token_total = alpha_tokens + mixed_alnum_tokens + symbol_mixed_tokens + other_tokens
        if token_total:
            alpha_token_ratio = alpha_tokens / token_total
            mixed_alnum_ratio = mixed_alnum_tokens / token_total
            symbol_mixed_ratio = symbol_mixed_tokens / token_total
        else:
            alpha_token_ratio = 0
            mixed_alnum_ratio = 0
            symbol_mixed_ratio = 0

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        line_total = len(lines)
        noisy_lines = 0
        if line_total:
            for line in lines:
                non_ws_line = sum(1 for ch in line if not ch.isspace())
                alpha_line = sum(1 for ch in line if ch.isalpha())
                if non_ws_line >= 8 and alpha_line / non_ws_line < 0.3:
                    noisy_lines += 1
                elif non_ws_line <= 4 and alpha_line <= 1:
                    noisy_lines += 1

        pdf_size = obj.file_size
        if not pdf_size and obj.document:
            try:
                pdf_size = obj.document.size
            except Exception:  # pragma: no cover - defensive
                pdf_size = None

        reasons = []
        if obj.has_markdown_glyph_artifacts():
            reasons.append("glyph_artifacts")
        if text.count("\ufffd") >= 5:
            reasons.append("replacement_chars")
        if text_len < 200 and (pdf_size is None or pdf_size >= 30_000):
            reasons.append("too_short")
        if pdf_size and pdf_size >= 200_000 and text_len < 1000:
            reasons.append("short_for_pdf")
        if pdf_size and text_len and pdf_size >= 50_000:
            ratio = text_len / pdf_size
            if ratio < 0.003:
                reasons.append("low_md_pdf_ratio")
        if non_ws >= 1000 and alpha_ratio < 0.25:
            reasons.append("low_alpha_ratio")
        if word_count >= 50 and avg_word_len > 20:
            reasons.append("avg_word_len_high")
        if word_count >= 100 and long_token_ratio > 0.1:
            reasons.append("many_long_tokens")
        if token_total >= 50 and alpha_token_ratio < 0.45:
            reasons.append("low_alpha_token_ratio")
        if token_total >= 50 and mixed_alnum_ratio > 0.08:
            reasons.append("mixed_alnum_tokens")
        if token_total >= 50 and symbol_mixed_ratio > 0.04:
            reasons.append("alpha_symbol_tokens")
        if line_total >= 20 and noisy_lines / line_total > 0.3:
            reasons.append("noisy_lines")

        return reasons

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
                obj.generate_embedding(overwrite=True)
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

    def summarize_documents(self, request, queryset):
        """Generate summaries for selected documents."""
        ok = 0
        skipped = 0
        errors = []
        for obj in queryset:
            if not obj.markdown:
                skipped += 1
                continue
            try:
                logger.info("Summarizing document id=%s title=%s", obj.id, obj.title)
                obj.summarize(overwrite=True)
                ok += 1
            except Exception as exc:  # pragma: no cover - defensive
                errors.append((obj, exc))
        if ok:
            self.message_user(
                request,
                f"Successfully summarized {ok} document(s).",
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
                f"{obj.title} could not be summarized: {exc}",
                level=messages.ERROR,
            )

    def extract_keywords(self, request, queryset):
        """Extract keywords from summaries for selected documents."""
        ok = 0
        skipped = 0
        errors = []
        for obj in queryset:
            if not obj.summary and not obj.summary_en:
                skipped += 1
                continue
            try:
                obj.extract_keywords(overwrite=True)
                ok += 1
            except Exception as exc:  # pragma: no cover - defensive
                errors.append((obj, exc))
        if ok:
            self.message_user(
                request,
                f"Successfully extracted keywords for {ok} document(s).",
                level=messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} document(s) because no summary is available.",
                level=messages.WARNING,
            )
        for obj, exc in errors:
            self.message_user(
                request,
                f"{obj.title} could not extract keywords: {exc}",
                level=messages.ERROR,
            )

    def translate_documents(self, request, queryset):
        """Translate title and summary to English for selected documents."""
        ok = 0
        skipped = 0
        errors = []
        for obj in queryset:
            if not obj.title:
                skipped += 1
                continue
            try:
                logger.info("Translating document id=%s title=%s", obj.id, obj.title)
                obj.translate(overwrite=True)
                ok += 1
            except Exception as exc:  # pragma: no cover - defensive
                errors.append((obj, exc))
        if ok:
            self.message_user(
                request,
                f"Successfully translated {ok} document(s).",
                level=messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} document(s) because no title is available.",
                level=messages.WARNING,
            )
        for obj, exc in errors:
            self.message_user(
                request,
                f"{obj.title} could not be translated: {exc}",
                level=messages.ERROR,
            )
