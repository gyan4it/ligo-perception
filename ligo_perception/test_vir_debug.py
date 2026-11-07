
from pathlib import Path
import sys
sys.path.insert(0, "tools")
from vir_builder import build_vir

vir = build_vir(
    bitmap_data={"file": str(Path("tests/fixtures/test_image.png")), "record": {}, "issues": []},
    pixel_data={"file": str(Path("tests/fixtures/test_image.png")), "metrics": {}, "issues": []},
    ocr_data={"file": str(Path("tests/fixtures/test_image.png")), "ocr": {}, "issues": []},
    asset_id="test-asset",
    project_profile="B01",
)
print("asset_id:", vir.get("asset_id"))
print("keys:", list(vir.keys()))

