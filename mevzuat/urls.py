from django.contrib import admin
from django.urls import path, re_path
from django.conf import settings
from django.views.static import serve as static_serve
from django.views.generic import RedirectView
from pathlib import Path
from ninja import NinjaAPI
from mevzuat.documents.api import router as documents_router


api = NinjaAPI()
api.add_router("/documents", documents_router)


urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", api.urls),
]


if settings.DEBUG:
    FRONTEND_OUT = Path(settings.BASE_DIR) / "frontend" / "out"

    # Serve Next.js assets under /_next/*
    urlpatterns += [
        re_path(r"^_next/(?P<path>.*)$",
                static_serve, {"document_root": FRONTEND_OUT / "_next"}),
    ]

    # Catch-all: serve exported HTML (index.html, other pages)
    urlpatterns += [
        re_path(r"^(?P<path>.*)$",
                static_serve, {"document_root": FRONTEND_OUT, "show_indexes": False}),
    ]
