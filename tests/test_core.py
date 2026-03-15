import io

from PIL import Image

import pytest

from splusdata.core import open_image, save_image, Core, SplusdataError


def make_png_bytes(size=(8, 8), color=(255, 0, 0)):
    im = Image.new("RGB", size, color)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def test_open_image_and_save_image(tmp_path):
    data = make_png_bytes((16, 16))
    im = open_image(data)
    assert isinstance(im, Image.Image)
    assert im.size == (16, 16)

    out = tmp_path / "out.png"
    save_image(data, str(out))
    assert out.exists()


class FakeClient:
    def __init__(self):
        self._collections = [
            {"id": 1, "name": "dr4", "patterns": {"": ""}},
            {"id": 2, "name": "dr6", "patterns": {"": ""}},
        ]

    def get_collections(self):
        return self._collections

    def list_files(self, collection_id, filter_str=None, filter_name=None, **kwargs):
        # Return a few fake files with filenames that allow testing include/exclude
        files = [
            {"id": 10, "filename": f"{filter_str}_a.fz", "file_type": "fz"},
            {"id": 11, "filename": f"{filter_str}_b.fz", "file_type": "fz"},
            {"id": 12, "filename": f"{filter_str}_c.txt", "file_type": "txt"},
        ]
        return files

    def download_file(self, file_id, output_path=None, timeout=None, **kwargs):
        # Return a tiny fits-like header bytes for tests (not used in these tests)
        return b"FAKEBYTES"


def make_core_with_fake_client():
    # Create Core instance without calling __init__ to avoid prompts / network
    core = Core.__new__(Core)
    core.client = FakeClient()
    core.collections = []
    core.verbose = 0
    return core


def test_get_collection_id_by_pattern_found():
    core = make_core_with_fake_client()
    col = core.get_collection_id_by_pattern("dr4")
    assert col["name"] == "dr4"


def test_get_collection_id_by_pattern_not_found_raises():
    core = make_core_with_fake_client()
    with pytest.raises(SplusdataError):
        core.get_collection_id_by_pattern("no-such-dr")


def test_get_file_metadata_basic():
    core = make_core_with_fake_client()
    # Add a pattern to the dr4 collection so pattern check passes
    core.client._collections[0]["patterns"] = {"": ""}
    # Should return one of the fake files
    res = core.get_file_metadata("SPLUS-0001", "R", pattern="", data_release="dr4")
    assert isinstance(res, dict)
    assert "filename" in res
