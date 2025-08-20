from django.contrib import admin
from django.urls import path, re_path
from django.conf import settings
from django.views.static import serve as static_serve
from pathlib import Path
from ninja import NinjaAPI
from mevzuat.documents.api import router as documents_router
from mevzuat.documents import views as documents_views


api = NinjaAPI()
api.add_router("/documents", documents_router)


urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", api.urls),
    path("", documents_views.main, name="home"),
    path("search/", documents_views.search, name="search"),
]

