from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from mevzuat.api.api_documents import router as documents_router
from mevzuat.api.api_auth import router as auth_router
from mevzuat.documents.feeds import LatestDocumentsFeed


api = NinjaAPI()
api.add_router("/auth", auth_router)
api.add_router("/documents", documents_router)


urlpatterns = [
    path('mAdmin/', admin.site.urls),
    path("api/", api.urls),
    path("rss/latest/", LatestDocumentsFeed(), name="latest_documents_feed"),
]

admin.site.index_title = 'Welcome to the Mevzuat Administration'
admin.site.site_header = 'Mevzuat Administration'
admin.site.site_title = 'Mevzuat Administration'
