import uuid
import os
from urllib.parse import urlparse
import requests

from django.db import models
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from pgvector.django import VectorField, L2Distance, HnswIndex, HalfVectorField


def document_upload_to(instance, filename):
    """
    Calls the concrete model’s get_document_upload_to().
    Needs to be importable so Django can serialize it in migrations.
    """
    return instance.get_document_upload_to(filename)


class Document(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    document = models.FileField(upload_to=document_upload_to)
    markdown = models.FileField(upload_to=document_upload_to)
    oai_id = models.CharField(max_length=100, blank=True, null=True)
    embedding = VectorField(dimensions=1536, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        indexes = [
            HnswIndex(
                name='topiccontent_embedding_hnsw',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_l2_ops']
            )
        ]

    def fetch_and_store_document(self, *, overwrite: bool = False, timeout: int = 30) -> "models.FileField":
        """
        Download the PDF at ``self.original_document_url()`` and save it into
        ``self.document``.

        Parameters
        ----------
        overwrite : bool, default False
            If ``False`` and ``self.document`` already exists, do nothing.
        timeout : int, default 30
            Seconds to wait for the HTTP response.

        Returns
        -------
        django.db.models.fields.files.FieldFile
            The stored ``document`` field (convenient to access ``.url``, ``.path``).

        Raises
        ------
        requests.RequestException
            On any network / HTTP error. Callers can catch and handle.
        """
        # Skip unless we need to fetch (honouring the overwrite flag)
        if self.document and not overwrite:
            return self.document

        pdf_url = self.original_document_url()
        if not pdf_url:
            raise ValueError("original_document_url() returned an empty URL")

        default_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.mevzuat.gov.tr/",
            "Connection": "keep-alive",
        }

        response = requests.get(pdf_url, headers=default_headers, timeout=timeout)
        response.raise_for_status()  # will raise if status ≥ 400

        # Derive a sensible filename, e.g. '1.5.7557.pdf'
        filename = os.path.basename(urlparse(pdf_url).path) or f"{self.uuid}.pdf"
        relative_path = self.get_document_upload_to(filename)

        # Save inside a transaction so the DB row and the file write stay in sync
        with transaction.atomic():
            self.document.save(relative_path, ContentFile(response.content), save=False)
            self.save(update_fields=["document"])

        return self.document

    def get_metadata(self):
        raise NotImplementedError("Child class should implement get_metadata()")

    def get_document_upload_to(self, filename):
        raise NotImplementedError("Child class should implement get_document_upload_to()")


class Mevzuat(Document):
    """
    Documents from mevzuat.gov.tr
    """
    name = models.CharField(max_length=600)
    mevzuat_tur = models.PositiveSmallIntegerField(
        choices=(
            (1, "Kanun"),
            (19, "Cumhurbaşkanlığı Kararnamesi"),
            (21, "Cumhurbaşkanlığı Yönetmeliği"),
            (20, "Cumhurbaşkanı Kararı"),
            (22, "Cumhurbaşkanlığı Genelgesi"),
            (4, "KHK"),
            (2, "Tüzük"),
            (17, "İç Tüzük"),
            (6, "Tüzük (?)"),
            (7, "Kurum Yönetmeliği"),
            (8, "Kurum Yönetmeliği (Üniversite)"),
            (9, "Tebliğ"),
        )
    )
    mevzuat_no = models.CharField(max_length=16)
    mevzuat_tertib = models.PositiveSmallIntegerField()

    kabul_tarih = models.DateField(null=True, blank=True)
    resmi_gazete_tarihi = models.DateField(null=True, blank=True)
    resmi_gazete_sayisi = models.CharField(max_length=16, null=True, blank=True)

    nitelik = models.CharField(max_length=120, null=True, blank=True)
    mukerrer = models.BooleanField(
        default=False,
        help_text=_("Whether this is a duplicate issue.")
    )
    tuzuk_mevzuat_tur = models.PositiveSmallIntegerField(default=0)
    has_old_law = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("mevzuat_tur", "mevzuat_tertib", "mevzuat_no", "resmi_gazete_tarihi"),
                name="uniq_mevzuat_tur_tertip_no",
            )
        ]

    def get_document_upload_to(self, filename):
        return f"mevzuat/{self.mevzuat_tur:02d}/{filename}"

    def original_document_url(self):
        if self.mevzuat_tur == 22:
            uri = f"CumhurbaskanligiGenelgeleri/{self.resmi_gazete_tarihi.strftime('%Y%m%d')}-{self.mevzuat_no}.pdf"
        elif self.mevzuat_tur in [7, 8, 9]:
            uri = f"yonetmelik/{self.mevzuat_tur}.{self.mevzuat_tertib}.{self.mevzuat_no}.pdf"
        else:
            uri = f"{self.mevzuat_tur}.{self.mevzuat_tertib}.{self.mevzuat_no}.pdf"
        return f"https://www.mevzuat.gov.tr/MevzuatMetin/{uri}"
