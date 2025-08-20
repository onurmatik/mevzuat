from django.shortcuts import render


def main(request):
    return render(request, "home.html")


def search(request):
    return render(request, "search_results.html")
