from django.shortcuts import render


def main_bootstrap(request):
    """Render a simple Bootstrap-based search and chart page."""
    return render(request, "documents/main_bootstrap.html")
