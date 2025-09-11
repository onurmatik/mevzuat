from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from mevzuat.documents.api import router as documents_router
from mevzuat.documents import views as documents_views
from mevzuat.documents.feeds import LatestDocumentsFeed


api = NinjaAPI()
api.add_router("/documents", documents_router)


urlpatterns = [
    path('mAdmin/', admin.site.urls),
    path("api/", api.urls),
    path("", documents_views.main, name="home"),
    path("search/", documents_views.search, name="search"),
    path("rss/latest/", LatestDocumentsFeed(), name="latest_documents_feed"),
]

admin.site.index_title = 'Welcome to the Mevzuat Administration'
admin.site.site_header = 'Mevzuat Administration'
admin.site.site_title = 'Mevzuat Administration'
