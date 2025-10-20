import numpy as np
from astropy.wcs import WCS
from scipy.interpolate import RegularGridInterpolator
import datetime

import pandas as pd
from astropy.table import Table

from splusdata.features.zeropoints.zp_map import _reconstruct_centers_from_model as _reconstruct_centers
# ---------- helpers: robust interpolator from model (dict) ----------

def _build_zp_interpolator_from_model(model):
    """
    Returns callable f(ra, dec) -> zp (mag).
    Handles grid/centers off-by-one & orientation.
    Falls back to global median where interpolation is NaN/outside.
    """
    global_median = float(model.get("global_median", 0.0))
    grid = np.asarray(model.get("grid", []), dtype=float)
    if grid.ndim != 2:
        return lambda ra, dec: np.full_like(np.asarray(ra, dtype=float), global_median, dtype=float)

    ra_centers = np.asarray(model.get("ra_centers", []), dtype=float)
    dec_centers = np.asarray(model.get("dec_centers", []), dtype=float)

    # Ensure centers match grid shape; rebuild if needed
    if ra_centers.size != grid.shape[0]:
        ra_centers = _reconstruct_centers(model, "ra", grid.shape[0])
    if dec_centers.size != grid.shape[1]:
        dec_centers = _reconstruct_centers(model, "dec", grid.shape[1])

    # Try (ra, dec) with grid as-is
    try:
        interp_rd = RegularGridInterpolator(
            (ra_centers, dec_centers), grid,
            bounds_error=False, fill_value=np.nan
        )
        def f_rd(ra, dec):
            pts = np.column_stack([np.asarray(ra, float).ravel(),
                                   np.asarray(dec, float).ravel()])
            vals = interp_rd(pts).reshape(np.shape(ra))
            vals = np.where(np.isnan(vals), 0.0, vals)  # local deviation fallback = 0
            return global_median + vals
        _ = f_rd(np.mean(ra_centers), np.mean(dec_centers))  # sanity check
        return f_rd
    except Exception:
        pass

    # Fallback: (dec, ra) with transposed grid
    interp_dr = RegularGridInterpolator(
        (dec_centers, ra_centers), grid.T,
        bounds_error=False, fill_value=np.nan
    )
    def f_dr(ra, dec):
        pts = np.column_stack([np.asarray(dec, float).ravel(),
                               np.asarray(ra, float).ravel()])
        vals = interp_dr(pts).reshape(np.shape(ra))
        vals = np.where(np.isnan(vals), 0.0, vals)
        return global_median + vals
    return f_dr

# ---------- main: in-memory calibration from HDU & model (dict) ----------

def calibrate_hdu_with_zpmodel(hdu, model_dict, *, in_place=False, return_factor=False, safe_global_fallback=True):
    """
    Calibrate an already-open FITS HDU (PrimaryHDU or ImageHDU) in memory using a ZP model dict.

    Applies: flux_cal = flux * 10^(-ZP/2.5)

    Parameters
    ----------
    hdu : astropy.io.fits.PrimaryHDU | astropy.io.fits.ImageHDU
        HDU already in memory; must have .data and .header
    model_dict : dict
        Zero-point model (JSON already loaded into memory)
    in_place : bool
        If True, modifies hdu.data and header in place; else returns a calibrated copy
    return_factor : bool
        If True, also returns the multiplicative factor map used
    safe_global_fallback : bool
        If WCS is missing/invalid, use global median uniformly (else raise)

    Returns
    -------
    new_hdu_or_hdu, (optionally) factor_map
    """
    if hdu.data is None:
        raise ValueError("HDU has no data.")

    data = hdu.data
    header = hdu.header
    global_median = float(model_dict.get("global_median", 0.0))

    # Get WCS -> RA/Dec per pixel
    try:
        w = WCS(header)
        h, wpx = data.shape
        x = np.arange(wpx)
        y = np.arange(h)
        xx, yy = np.meshgrid(x, y)
        sky = w.pixel_to_world(xx, yy)
        ra = np.asarray(sky.ra.deg)
        dec = np.asarray(sky.dec.deg)
        zp_fn = _build_zp_interpolator_from_model(model_dict)
        zp_map = zp_fn(ra, dec)
    except Exception:
        if not safe_global_fallback:
            raise
        # no WCS: uniform correction
        zp_map = np.full_like(data, global_median, dtype=float)

    # Convert ZP (mag) -> multiplicative factor in flux space
    factor = np.power(10.0, -zp_map / 2.5, dtype=float)

    # Apply to finite pixels only
    calibrated = np.array(data, copy=True)
    mask = np.isfinite(calibrated)
    calibrated[mask] = calibrated[mask] * factor[mask]

    # Return in place or as a copy HDU
    if in_place:
        hdu.data = calibrated
        # annotate header
        hdu.header['ZPCALIB'] = True
        hdu.header['ZPCDATE'] = datetime.datetime.now().isoformat()
        hdu.header['ZPCMED']  = global_median
        return (hdu, factor) if return_factor else hdu
    else:
        from astropy.io.fits import ImageHDU
        new_hdu = ImageHDU(data=calibrated, header=header.copy())
        new_hdu.header['ZPCALIB'] = True
        new_hdu.header['ZPCDATE'] = datetime.datetime.now().isoformat()
        new_hdu.header['ZPCMED']  = global_median
        return (new_hdu, factor) if return_factor else new_hdu
    
def compute_zp_for_coords_array(
    ra: np.ndarray,
    dec: np.ndarray,
    model_dict: dict,
    *,
    safe_global_fallback: bool = False,
    out_dtype=np.float32,
) -> np.ndarray:
    """
    Compute zero points from RA and Dec arrays using a ZP model.

    Parameters
    ----------
    ra, dec : array-like
        RA and Dec in degrees. Must be same shape.
    model_dict : dict
        Zero-point model (JSON already loaded) with:
        - "grid" : 2D array of local deviations (mag)
        - "ra_centers", "dec_centers" (optional)
        - "global_median" : float
    safe_global_fallback : bool, default True
        If interpolation fails or returns NaN, fallback to global median.
        If False, raise.
    out_dtype : numpy dtype, default np.float32
        Output dtype for zp array.

    Returns
    -------
    zp : np.ndarray
        Array of zero points (mag) with the same shape as ra/dec.
    """
    ra = np.asarray(ra, dtype=float)
    dec = np.asarray(dec, dtype=float)

    if ra.shape != dec.shape:
        raise ValueError(f"ra and dec must have the same shape. Got {ra.shape} and {dec.shape}.")

    global_median = float(model_dict.get("global_median", 0.0))
    zp_fn = _build_zp_interpolator_from_model(model_dict)

    try:
        zp = zp_fn(ra, dec).astype(out_dtype, copy=False)
        if safe_global_fallback:
            bad = ~np.isfinite(zp)
            if bad.any():
                zp = zp.copy()
                zp[bad] = global_median
        else:
            if not np.all(np.isfinite(zp)):
                raise ValueError("ZP interpolation returned NaN/inf and safe fallback is disabled.")
    except Exception:
        if not safe_global_fallback:
            raise
        zp = np.full_like(ra, global_median, dtype=out_dtype)

    return zp