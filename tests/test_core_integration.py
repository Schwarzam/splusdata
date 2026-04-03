import os

import pytest
import numpy as np

from splusdata.core import Core
from splusdata import SplusdataError


pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def core_client():
    username = os.getenv("SPLUS_USERNAME")
    password = os.getenv("SPLUS_PASSWORD")
    server_ip = os.getenv("SPLUS_SERVER_IP", "https://splus.cloud")

    if not (username and password):
        pytest.skip("SPLUS_USERNAME/SPLUS_PASSWORD não configurados")

    return Core(username=username, password=password, SERVER_IP=server_ip)


@pytest.mark.skipif(
    not (os.getenv("SPLUS_USERNAME") and os.getenv("SPLUS_PASSWORD")),
    reason="SPLUS_USERNAME/SPLUS_PASSWORD are not configured",
)
def test_check_available_images_releases_real_api(core_client):
    releases = core_client.check_available_images_releases()

    assert isinstance(releases, list)
    assert len(releases) > 0


def test_full_field_fits_image(core_client):
    """Integration test that hits the real S-PLUS API via adss client."""
    hdu_list = core_client.field_frame(field="SPLUS-n01s10", band="R", data_release="dr4")
    print(hdu_list.info())

    w_hdu_list = core_client.field_frame("SPLUS-n01s10", "R", weight=True, data_release="dr4")
    print(w_hdu_list.info())
   
    assert hdu_list is not None 
    assert len(hdu_list) > 0
    assert w_hdu_list is not None
    assert len(w_hdu_list) > 0



def test_create_fits_stamp_by_coordinates(core_client):
    stamp = core_client.stamp(
        ra=10.1234, 
        dec=-2.3456, 
        size=300, 
        band="I", 
        size_unit="pixels", 
        data_release="dr4"
    )
    data = stamp[1].data
    assert data is not None


def test_create_fits_stamp_by_field_or_object(core_client):
    stamp = core_client.stamp(
        ra=10.1234, 
        dec=-2.3456, 
        size=20, 
        band="F660",
        field_name="SPLUS-n01s10", 
        size_unit="arcsec", 
        data_release="dr4"
    )
    data = stamp[1].data
    assert data is not None


def test_lupton_rgb_image(core_client):
    rgb = core_client.lupton_rgb(
        ra=10.1234, dec=-2.3456, size=600,
        R="I", G="R", B="G",
        Q=8, stretch=3,
        data_release="dr4"
    )
    rgb.save("rgb_lupton.png")
    
    assert rgb is not None

def test_trilogy_rgb_image(core_client):
    tri = core_client.trilogy_image(
        ra=10.1234, dec=-2.3456, size=600,
        R=["R","I","F861","Z"], G=["G","F515","F660"], B=["U","F378","F395","F410","F430"],
        noiselum=0.15, satpercent=0.15, colorsatfac=2,
        data_release="dr4"
    )
    tri.save("rgb_trilogy.png")
    
    assert tri is not None



def test_run_query(core_client):
    query = "SELECT TOP 5 * FROM splus_dr4.field_metadata"
    result = core_client.run_query(query)
    
    assert result is not None
    assert len(result) == 5


def test_zero_points_dr6(core_client):
    ras = np.random.uniform(150, 150.5, 10000)
    decs = np.random.uniform(-24, -23.5, 10000)

    zps = conn.get_zp(field="HYDRA-0011", band="R", ra=ras, dec=decs)
    
    assert zps is not None
    

def test_create_and_save_calibrated_cutout(core_client):
    calib_hdu = conn.calibrated_stamp(
        ra=10.1234, dec=-2.3456, size=300, band="R",
        outfile="calibrated_stamp_R.fits",
        data_release="dr6"
    )
    assert calib_hdu is not None
    assert os.path.exists("calibrated_stamp_R.fits")


def test_error_handling(core_client):
    try:
        hdu = conn.field_frame("SPLUS-nXXsYY", "R", data_release="dr4")
    except SplusdataError as e:
        assert "not found" in str(e)
    else:
        assert False, "Expected SplusdataError was not raised"
