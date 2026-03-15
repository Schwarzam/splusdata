import pandas as pd
from functools import lru_cache
from astropy.coordinates import SkyCoord
import astropy.units as u

from splusdata.vars import DR_POINTINGS

# uses your DR_POINTINGS exactly as given


@lru_cache(maxsize=None)
def _load_dr(dr: str):
    """Load and normalize a DR table once; results are cached."""
    info = DR_POINTINGS[dr]
    df = pd.read_csv(info["link"])
    # keep only needed cols with consistent names
    df = df.rename(
        columns={
            info["ra_col"]: "ra",
            info["dec_col"]: "dec",
            info["field_col"]: "field",
        }
    )[["ra", "dec", "field"]].copy()
    # make sure ra/dec are numeric; drop bad rows
    df["ra"] = pd.to_numeric(df["ra"], errors="coerce")
    df["dec"] = pd.to_numeric(df["dec"], errors="coerce")
    df = df.dropna(subset=["ra", "dec"])
    return df.reset_index(drop=True)


def find_pointing(ra, dec, radius=1 * u.degree):
    """
    Return the first DR (by dr_order) whose field center lies within `radius`.
    Output: {'dr': 'dr4', 'field': '...', 'distance': <Quantity ...>}
    """
    target = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")
    radius = radius if isinstance(radius, u.Quantity) else radius * u.arcmin

    for dr in DR_POINTINGS.keys():
        df = _load_dr(dr)
        coords = SkyCoord(df["ra"].values * u.deg, df["dec"].values * u.deg)
        sep = target.separation(coords)
        idx = int(sep.argmin())
        if sep[idx] <= radius:
            return {"dr": dr, "field": df["field"].iloc[idx], "distance": sep[idx]}
    return None


# optional helpers:
def warm_cache(dr_order=("dr4", "dr5", "dr6")):
    """Preload all DR tables into cache (optional)."""
    for dr in dr_order:
        _ = _load_dr(dr)


def clear_cache():
    """Clear cached tables if you need to refresh."""
    _load_dr.cache_clear()
