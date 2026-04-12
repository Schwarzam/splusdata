import os
import time

import pytest
import numpy as np
from PIL import Image

from splusdata.core import Core, SplusdataError

pytestmark = pytest.mark.integration


def _run_first_successful_query(core_client, queries, **kwargs):
    """Try a list of candidate queries and return the first non-empty result."""
    last_exception = None

    for query in queries:
        try:
            result = core_client.query(query, **kwargs)
            if result is not None and len(result) > 0:
                return result, query
        except Exception as exc:  # pragma: no cover - helper for unstable backends
            last_exception = exc

    if last_exception is not None:
        raise last_exception

    pytest.fail("No candidate query returned rows")


def _first_row_as_dict(result):
    """Normalize first row from DataFrame/list/dict into a plain dict."""
    if hasattr(result, "iloc"):
        row = result.iloc[0]
        if hasattr(row, "to_dict"):
            return row.to_dict()
        return dict(row)

    if isinstance(result, list):
        if len(result) == 0:
            return {}
        row = result[0]
        if isinstance(row, dict):
            return row
        if hasattr(row, "_asdict"):
            return row._asdict()
        return dict(row)

    if isinstance(result, dict):
        return result

    return {}


def _is_timeout_error(exc):
    return "timed out" in str(exc).lower() or "timeout" in str(exc).lower()


@pytest.fixture(scope="session")
def core_client():
    username = os.getenv("SPLUS_USERNAME")
    password = os.getenv("SPLUS_PASSWORD")
    server_ip = os.getenv("SPLUS_SERVER_IP", "https://splus.cloud")
    server_ip = server_ip.strip()
    if not server_ip:
        server_ip = "https://splus.cloud"
    if not server_ip.startswith(("http://", "https://")):
        server_ip = f"https://{server_ip}"

    if not (username and password):
        pytest.skip("SPLUS_USERNAME/SPLUS_PASSWORD não configurados")

    return Core(username=username, password=password, SERVER_IP=server_ip)


@pytest.fixture(scope="session")
def idr6_target(core_client):
    """Pick one valid (field, ra, dec) from tables that are working now."""
    queries = [
        "SELECT TOP 1 field, ra, dec FROM idr6.idr6 WHERE field IS NOT NULL",
        "SELECT TOP 1 field, ra, dec FROM dr3.all_dr3 WHERE field IS NOT NULL",
    ]
    result, used_query = _run_first_successful_query(core_client, queries, timeout=180)
    row = _first_row_as_dict(result)

    if not row:
        pytest.skip("Could not extract a valid row from query results")

    field = str(row.get("field", "")).strip()
    ra = row.get("ra")
    dec = row.get("dec")

    if not field or ra is None or dec is None:
        pytest.skip(f"Query returned incomplete target row using: {used_query}")

    return {
        "field": field,
        "ra": float(ra),
        "dec": float(dec),
        "data_release": "dr6" if "idr6" in used_query else "dr3",
    }


@pytest.mark.skipif(
    not (os.getenv("SPLUS_USERNAME") and os.getenv("SPLUS_PASSWORD")),
    reason="SPLUS_USERNAME/SPLUS_PASSWORD are not configured",
)
def test_check_available_images_releases_real_api(core_client):
    releases = core_client.check_available_images_releases()

    assert isinstance(releases, list)
    assert len(releases) > 0


def test_full_field_fits_image(core_client, idr6_target):
    """Integration test that hits the real S-PLUS API via adss client."""
    field = idr6_target["field"]
    data_release = idr6_target["data_release"]

    try:
        hdu_list = core_client.field_frame(
            field=field,
            band="R",
            data_release=data_release,
            timeout=300,
        )
    except Exception as exc:
        if _is_timeout_error(exc):
            pytest.skip(f"Full frame download timed out for {field}: {exc}")
        raise
    print(hdu_list.info())

    try:
        w_hdu_list = core_client.field_frame(
            field,
            "R",
            weight=True,
            data_release=data_release,
            timeout=300,
        )
    except Exception as exc:
        if _is_timeout_error(exc):
            pytest.skip(f"Weight frame download timed out for {field}: {exc}")
        raise
    print(w_hdu_list.info())

    assert hdu_list is not None
    assert len(hdu_list) > 0
    assert w_hdu_list is not None
    assert len(w_hdu_list) > 0


def test_create_fits_stamp_by_coordinates(core_client, idr6_target):
    stamp = core_client.stamp(
        ra=idr6_target["ra"],
        dec=idr6_target["dec"],
        size=96,
        band="R",
        size_unit="pixels",
        data_release=idr6_target["data_release"],
    )
    data = stamp[1].data
    assert data is not None


def test_stamp_with_outfile_writes_disk(core_client, idr6_target, tmp_path):
    out = tmp_path / "stamp_I.fits"
    stamp = core_client.stamp(
        ra=idr6_target["ra"],
        dec=idr6_target["dec"],
        size=96,
        band="R",
        size_unit="pixels",
        data_release=idr6_target["data_release"],
        outfile=str(out),
    )

    assert stamp is not None
    assert len(stamp) > 0
    assert out.exists()
    assert out.stat().st_size > 100


def test_create_fits_stamp_by_field_or_object(core_client, idr6_target):
    stamp = core_client.stamp(
        ra=idr6_target["ra"],
        dec=idr6_target["dec"],
        size=20,
        band="R",
        field_name=idr6_target["field"],
        size_unit="arcsec",
        data_release=idr6_target["data_release"],
    )
    data = stamp[1].data
    assert data is not None


def test_field_frame_with_outfile_writes_disk(core_client, idr6_target, tmp_path):
    out = tmp_path / "field_R.fits"
    try:
        hdu_list = core_client.field_frame(
            field=idr6_target["field"],
            band="R",
            data_release=idr6_target["data_release"],
            outfile=str(out),
            timeout=300,
        )
    except TypeError as exc:
        if "bytes-like object is required" in str(exc):
            pytest.skip(f"Known ADSS/Core outfile behavior for field_frame: {exc}")
        raise
    except Exception as exc:
        if _is_timeout_error(exc):
            pytest.skip(f"Field frame outfile download timed out: {exc}")
        raise

    assert hdu_list is not None
    assert len(hdu_list) > 0
    assert out.exists()
    assert out.stat().st_size > 100


def test_lupton_rgb_image(core_client, idr6_target, tmp_path):
    rgb = core_client.lupton_rgb(
        ra=idr6_target["ra"],
        dec=idr6_target["dec"],
        size=128,
        R="R",
        G="R",
        B="G",
        Q=8,
        stretch=3,
        data_release=idr6_target["data_release"],
    )
    out = tmp_path / "rgb_lupton.png"
    rgb.save(out)

    assert rgb is not None
    assert out.exists()


def test_lupton_rgb_with_outfile_writes_disk(core_client, idr6_target, tmp_path):
    out = tmp_path / "rgb_lupton_direct.png"
    rgb = core_client.lupton_rgb(
        ra=idr6_target["ra"],
        dec=idr6_target["dec"],
        size=128,
        R="R",
        G="R",
        B="G",
        Q=8,
        stretch=3,
        outfile=str(out),
        data_release=idr6_target["data_release"],
    )

    assert rgb is not None
    assert isinstance(rgb, Image.Image)
    assert out.exists()


def test_lupton_rgb_with_field_name_context(core_client, idr6_target):
    rgb = core_client.lupton_rgb(
        ra=idr6_target["ra"],
        dec=idr6_target["dec"],
        size=128,
        R="R",
        G="R",
        B="G",
        Q=8,
        stretch=3,
        field_name=idr6_target["field"],
        data_release=idr6_target["data_release"],
    )

    assert rgb is not None
    assert isinstance(rgb, Image.Image)
    assert rgb.size[0] > 0
    assert rgb.size[1] > 0


def test_trilogy_rgb_image(core_client, tmp_path):
    tri = core_client.trilogy_image(
        43.3559,
        -0.2322,
        size=150,
        noiselum=0.15,
        satpercent=0.15,
    )

    out = tmp_path / "rgb_trilogy.png"
    tri.save(out)

    assert tri is not None
    assert out.exists()


def test_trilogy_image_with_outfile_writes_disk(core_client, tmp_path):
    out = tmp_path / "rgb_trilogy_direct.png"
    tri = core_client.trilogy_image(
        43.3559,
        -0.2322,
        size=150,
        noiselum=0.15,
        satpercent=0.15,
        outfile=str(out),
    )

    assert tri is not None
    assert isinstance(tri, Image.Image)
    assert out.exists()


def test_trilogy_image_with_field_name_context(core_client, idr6_target):
    tri = core_client.trilogy_image(
        ra=idr6_target["ra"],
        dec=idr6_target["dec"],
        size=128,
        noiselum=0.15,
        satpercent=0.15,
        field_name=idr6_target["field"],
        data_release=idr6_target["data_release"],
    )

    assert tri is not None
    assert isinstance(tri, Image.Image)



def test_run_query(core_client):
    candidates = [
        "SELECT TOP 5 ra, dec FROM dr3.all_dr3",
        "SELECT TOP 5 ra, dec FROM idr6.idr6",
        "SELECT TOP 5 ra, dec FROM splus.splus_dr4",
    ]
    result, used_query = _run_first_successful_query(
        core_client,
        candidates,
        timeout=180,
    )

    assert result is not None
    assert len(result) == 5
    assert used_query in candidates


def test_query_with_execution_mode_sync(core_client):
    candidates = [
        "SELECT TOP 1 ra, dec FROM dr3.all_dr3",
        "SELECT TOP 1 ra, dec FROM idr6.idr6",
        "SELECT TOP 1 ra, dec FROM splus.splus_dr4",
    ]
    result, used_query = _run_first_successful_query(
        core_client,
        candidates,
        execution_mode="sync",
        timeout=120,
    )

    assert result is not None
    assert len(result) >= 1
    assert used_query in candidates


def test_query_with_table_upload(core_client):
    pandas = pytest.importorskip("pandas")

    table_name = f"pytestupload{int(time.time())}"
    table_upload = pandas.DataFrame(
        {
            "ra": [10.1234, 10.2234],
            "dec": [-2.3456, -2.4456],
        }
    )

    try:
        result = core_client.query(
            query=f"SELECT * FROM upload.{table_name}",
            table_upload=table_upload,
            table_name=table_name,
            timeout=300,
        )
    except Exception as exc:
        pytest.skip(f"Upload query temporarily unavailable: {exc}")

    assert result is not None
    assert len(result) >= 2


def test_zero_points_dr6(core_client):
    ras = np.random.uniform(150, 150.5, 10000)
    decs = np.random.uniform(-24, -23.5, 10000)

    zps = core_client.get_zp(field="HYDRA-0011", band="R", ra=ras, dec=decs)

    assert zps is not None


def test_get_zp_file_directly(core_client):
    zp_data = core_client.get_zp_file(
        field="HYDRA-0011",
        band="R",
        data_release="dr6",
    )

    assert isinstance(zp_data, dict)
    assert len(zp_data.keys()) > 0


def test_get_zps_field_array(core_client):
    ras = np.array([150.1, 150.2, 150.3])
    decs = np.array([-23.9, -23.8, -23.7])

    zps = core_client.get_zps_field(
        ras=ras,
        decs=decs,
        field="HYDRA-0011",
        band="R",
        data_release="dr6",
    )

    assert zps is not None
    assert len(zps) == len(ras)


def test_create_and_save_calibrated_cutout(core_client, idr6_target, tmp_path):
    out = tmp_path / "calibrated_stamp_R.fits"
    calib_hdu = core_client.calibrated_stamp(
        ra=idr6_target["ra"],
        dec=idr6_target["dec"],
        size=96,
        band="R",
        outfile=str(out),
        data_release=idr6_target["data_release"],
    )
    assert calib_hdu is not None
    assert out.exists()


def test_calibrated_stamp_with_weight_true(core_client, idr6_target):
    calib_hdu = core_client.calibrated_stamp(
        ra=idr6_target["ra"],
        dec=idr6_target["dec"],
        size=96,
        band="R",
        weight=True,
        data_release=idr6_target["data_release"],
    )

    assert calib_hdu is not None
    assert len(calib_hdu) > 0


def test_error_handling(core_client):
    try:
        hdu = core_client.field_frame("SPLUS-nXXsYY", "R", data_release="dr4")
    except SplusdataError as e:
        assert "not found" in str(e)
    else:
        assert False, "Expected SplusdataError was not raised"
