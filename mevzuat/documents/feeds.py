from django.contrib.syndication.views import Feed

from .models import Document


class LatestDocumentsFeed(Feed):
    """RSS feed showing recently added documents."""

    title = "Latest documents"
    link = "/rss/latest/"
    description = "Updates on the latest documents added to mevzuat.info"

    def items(self):
        return Document.objects.order_by("-created_at")[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        parts = []
        if item.type:
            parts.append(item.type.name)
        if item.date:
            parts.append(item.date.isoformat())
        return " | ".join(parts)

    def item_link(self, item):
        return item.original_document_url or "/"

    def item_pubdate(self, item):
        return item.created_at
