from django.shortcuts import render

from .models import Document


def main(request):
    recent_documents = Document.objects.order_by("-created_at")[:5]
    return render(request, "home.html", {"recent_documents": recent_documents})


def search(request):
    return render(request, "search_results.html")
