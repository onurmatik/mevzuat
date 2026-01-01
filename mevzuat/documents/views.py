from django.shortcuts import render, get_object_or_404

from .models import Document


def main(request):
    recent_documents = Document.objects.order_by("-date")[:5]
    return render(request, "home.html", {"recent_documents": recent_documents})


def search(request):
    return render(request, "search_results.html")


def document_detail(request, document_uuid):
    document = get_object_or_404(Document, uuid=document_uuid)
    return render(
        request,
        "document_detail.html",
        {
            "document": document,
        }
    )
