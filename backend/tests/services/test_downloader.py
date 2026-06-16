# backend/tests/services/test_downloader.py
from unittest.mock import patch

from app.services.usda import downloader


FAKE_HTML = """
<html><body>
  <a href="https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_json_2024-04-26.zip">Foundation JSON new</a>
  <a href="https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_json_2023-03-30.zip">Foundation JSON old</a>
  <a href="https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_csv_2024-04-26.zip">Foundation CSV</a>
  <a href="/fdc-datasets/FoodData_Central_sr_legacy_food_json_2018-04-28.zip">SR Legacy JSON (relative)</a>
</body></html>
"""


class _FakeResp:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


def test_fetch_dataset_urls_prefers_latest_json():
    with patch.object(downloader.httpx, "get", return_value=_FakeResp(FAKE_HTML)):
        urls = downloader.fetch_dataset_urls()

    # foundation：两个 JSON（2024/2023）+ 一个 CSV（2024），应选最新 JSON 2024
    assert "foundation" in urls
    assert "2024-04-26" in urls["foundation"]
    assert "json" in urls["foundation"].lower()

    # sr_legacy：相对路径被拼成绝对 URL
    assert "sr_legacy" in urls
    assert urls["sr_legacy"].startswith("https://fdc.nal.usda.gov/")
    assert "2018-04-28" in urls["sr_legacy"]
