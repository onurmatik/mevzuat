from datetime import date
import shutil
import tempfile

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from .models import Mevzuat


class DocumentListAPITest(TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.tempdir)
        self.override.enable()

        Mevzuat.objects.create(
            name="Law 1",
            mevzuat_tur=1,
            mevzuat_no="1",
            mevzuat_tertib=1,
            document=ContentFile(b"a", name="law1.pdf"),
            resmi_gazete_tarihi=date(2020, 1, 1),
        )
        Mevzuat.objects.create(
            name="Law 2",
            mevzuat_tur=2,
            mevzuat_no="2",
            mevzuat_tertib=1,
            document=ContentFile(b"b", name="law2.pdf"),
            resmi_gazete_tarihi=date(2021, 1, 1),
        )
        Mevzuat.objects.create(
            name="Law 3",
            mevzuat_tur=1,
            mevzuat_no="3",
            mevzuat_tertib=1,
            document=ContentFile(b"c", name="law3.pdf"),
            resmi_gazete_tarihi=date(2021, 5, 5),
        )

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.tempdir)

    def test_filter_by_mevzuat_tur(self):
        response = self.client.get("/api/documents/", {"mevzuat_tur": 1})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertTrue(all(item["mevzuat_tur"] == 1 for item in data))

    def test_filter_by_year(self):
        response = self.client.get("/api/documents/", {"year": 2021})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertTrue(all(item["resmi_gazete_tarihi"].startswith("2021") for item in data))

    def test_filter_by_both(self):
        response = self.client.get("/api/documents/", {"mevzuat_tur": 1, "year": 2021})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["mevzuat_tur"], 1)
        self.assertTrue(data[0]["resmi_gazete_tarihi"].startswith("2021"))

    def test_filter_by_month(self):
        response = self.client.get("/api/documents/", {"month": 1})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertTrue(all(item["resmi_gazete_tarihi"][5:7] == "01" for item in data))

    def test_filter_by_date(self):
        response = self.client.get("/api/documents/", {"date": "2021-05-05"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["resmi_gazete_tarihi"], "2021-05-05")

    def test_filter_by_date_range(self):
        params = {"start_date": "2020-01-01", "end_date": "2021-04-30"}
        response = self.client.get("/api/documents/", params)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertTrue(all("2020-01-01" <= item["resmi_gazete_tarihi"] <= "2021-04-30" for item in data))
