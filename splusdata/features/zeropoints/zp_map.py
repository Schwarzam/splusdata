from scipy.interpolate import RegularGridInterpolator
import numpy as np

import numpy as np
import warnings
from scipy.interpolate import RegularGridInterpolator

def _reconstruct_centers_from_model(model, axis="ra", grid_len=None):
    """
    Rebuild centers to match the (possibly padded) grid length using the model's
    ra_min/ra_max/dec_min/dec_max, bins, and padding.

    The model saved edges with length `bins`, which yields B = bins-1 actual bins
    before padding. After padding, the grid dimension is B + 2*padding.
    Centers are midpoints of each (possibly padded) bin.

    Parameters
    ----------
    model : dict
    axis : str
        "ra" or "dec"
    grid_len : int
        Target number of centers (should equal grid.shape[dim])

    Returns
    -------
    np.ndarray
    """
    assert axis in ("ra", "dec")
    amin = model[f"{axis}_min"]
    amax = model[f"{axis}_max"]
    bins = int(model.get("bins", 15))
    padding = int(model.get("padding", 1))

    # B is the number of *actual* bins before padding (because edges length = bins)
    B = bins - 1
    if B <= 0:
        raise ValueError(f"Invalid bins in model: bins={bins}")

    # native bin width (pre-padding)
    dA = (amax - amin) / B

    # original centers (length B)
    centers_core = amin + (np.arange(B) + 0.5) * dA

    # padded centers: extend by `padding` bins on both sides at same spacing
    if padding > 0:
        left = centers_core[0] - dA * np.arange(padding, 0, -1)
        right = centers_core[-1] + dA * np.arange(1, padding + 1)
        centers = np.concatenate([left, centers_core, right])
    else:
        centers = centers_core

    if grid_len is not None and len(centers) != grid_len:
        # If still mismatched, resample linearly across the padded span as a last resort.
        warnings.warn(
            f"{axis.upper()} centers length ({len(centers)}) != grid axis length ({grid_len}). "
            "Resampling centers to match grid shape."
        )
        # Rebuild centers uniformly across the total span of the padded grid:
        total_span = (amax - amin) + 2 * padding * dA
        a_min_padded = amin - padding * dA
        centers = a_min_padded + (np.arange(grid_len) + 0.5) * (total_span / grid_len)

    return centers

def zp_at_coord(model, ra, dec, margin=0.1):
    """
    Get zero-point correction(s) for coordinate(s).

    Accepts:
      - ra:  float or array-like
      - dec: float or array-like

    Supports broadcasting:
      - scalar ra with array dec
      - array ra with scalar dec
      - array ra with array dec (same shape or broadcastable)

    Returns:
      - float if both inputs are scalar
      - np.ndarray otherwise

    Notes:
      - Keeps your original behavior: if ANY point is out of bounds (with margin)
        or interpolation yields NaN, it raises Exception (instead of partial fill).
    """
    global_median = float(model.get("global_median", 0.0))

    # If no grid info, fallback
    if not ("grid" in model and "ra_centers" in model and "dec_centers" in model):
        if np.isscalar(ra) and np.isscalar(dec):
            return global_median
        ra_arr = np.asarray(ra, dtype=float)
        dec_arr = np.asarray(dec, dtype=float)
        ra_b, dec_b = np.broadcast_arrays(ra_arr, dec_arr)
        return np.full(ra_b.shape, global_median, dtype=float)

    # Load saved arrays
    grid = np.asarray(model["grid"], dtype=float)
    ra_centers = np.asarray(model.get("ra_centers", []), dtype=float)
    dec_centers = np.asarray(model.get("dec_centers", []), dtype=float)

    # Rebuild centers if needed (mismatch / empty)
    need_rebuild = (
        ra_centers.size == 0 or
        dec_centers.size == 0 or
        grid.ndim != 2 or
        grid.shape[0] != ra_centers.size or
        grid.shape[1] != dec_centers.size
    )
    if need_rebuild:
        ra_centers = _reconstruct_centers_from_model(model, "ra", grid_len=grid.shape[0])
        dec_centers = _reconstruct_centers_from_model(model, "dec", grid_len=grid.shape[1])

    # Normalize inputs + broadcast
    ra_is_scalar = np.isscalar(ra)
    dec_is_scalar = np.isscalar(dec)

    ra_arr = np.asarray(ra, dtype=float)
    dec_arr = np.asarray(dec, dtype=float)
    ra_b, dec_b = np.broadcast_arrays(ra_arr, dec_arr)

    # Vectorized bounds check
    ra_min, ra_max = float(np.min(ra_centers)), float(np.max(ra_centers))
    dec_min, dec_max = float(np.min(dec_centers)), float(np.max(dec_centers))

    in_bounds = (
        (ra_b >= (ra_min - margin)) & (ra_b <= (ra_max + margin)) &
        (dec_b >= (dec_min - margin)) & (dec_b <= (dec_max + margin))
    )

    if not np.all(in_bounds):
        bad = np.argwhere(~in_bounds)
        i0 = tuple(bad[0])  # first offending index
        warnings.warn(
            f"Some coordinates are outside the grid range RA=[{ra_min:.3f}, {ra_max:.3f}] "
            f"Dec=[{dec_min:.3f}, {dec_max:.3f}] (margin={margin:.3f}). "
            f"Example at index {i0}: (RA={ra_b[i0]:.3f}, Dec={dec_b[i0]:.3f}). "
            "Falling back to global median (raising exception, per original behavior)."
        )
        raise Exception("Some coordinates are outside the grid range.")

    # Build interpolator once
    interpolator = RegularGridInterpolator(
        (ra_centers, dec_centers),
        grid,
        bounds_error=False,
        fill_value=np.nan,
    )

    # Interpolate all points
    pts = np.column_stack([ra_b.ravel(), dec_b.ravel()])  # (N, 2)
    zp = interpolator(pts).reshape(ra_b.shape)

    if np.any(np.isnan(zp)):
        bad = np.argwhere(np.isnan(zp))
        i0 = tuple(bad[0])
        warnings.warn(
            f"Interpolation failed (NaN) for some coordinates. "
            f"Example at index {i0}: (RA={ra_b[i0]:.3f}, Dec={dec_b[i0]:.3f}). "
            "Returning global median (raising exception, per original behavior)."
        )
        raise Exception("Interpolation failed (NaN) for some coordinates.")

    out = zp + global_median

    # Return scalar if scalar inputs
    if ra_is_scalar and dec_is_scalar:
        return float(out)

    return out
    """
    Vectorized zero-point correction lookup.

    Accepts:
      - ra: float or array-like
      - dec: float or array-like
    Supports broadcasting:
      - ra scalar + dec array
      - ra array + dec scalar
      - ra array + dec array (same shape or broadcastable)

    Returns:
      - float if both inputs are scalar (and return_scalar_if_scalar=True)
      - np.ndarray otherwise
    """
    global_median = float(model.get("global_median", 0.0))

    # If no grid, always fallback
    if not ("grid" in model and ("ra_centers" in model or True) and ("dec_centers" in model or True)):
        # keep original behavior: return global median only
        if np.isscalar(ra) and np.isscalar(dec) and return_scalar_if_scalar:
            return global_median
        ra_arr = np.asarray(ra, dtype=float)
        dec_arr = np.asarray(dec, dtype=float)
        ra_b, dec_b = np.broadcast_arrays(ra_arr, dec_arr)
        return np.full(ra_b.shape, global_median, dtype=float)

    # Load arrays
    grid = np.asarray(model["grid"], dtype=float)
    ra_centers = np.asarray(model.get("ra_centers", []), dtype=float)
    dec_centers = np.asarray(model.get("dec_centers", []), dtype=float)

    # Rebuild centers if needed
    need_rebuild = (
        ra_centers.size == 0 or
        dec_centers.size == 0 or
        grid.ndim != 2 or
        grid.shape[0] != ra_centers.size or
        grid.shape[1] != dec_centers.size
    )
    if need_rebuild:
        ra_centers = _reconstruct_centers_from_model(model, "ra", grid_len=grid.shape[0])
        dec_centers = _reconstruct_centers_from_model(model, "dec", grid_len=grid.shape[1])

    # Interpolator (build once)
    interpolator = RegularGridInterpolator(
        (ra_centers, dec_centers),
        grid,
        bounds_error=False,
        fill_value=np.nan,
    )

    # Normalize inputs to arrays + broadcast
    ra_is_scalar = np.isscalar(ra)
    dec_is_scalar = np.isscalar(dec)

    ra_arr = np.asarray(ra, dtype=float)
    dec_arr = np.asarray(dec, dtype=float)
    ra_b, dec_b = np.broadcast_arrays(ra_arr, dec_arr)

    # Bounds check (vectorized) with margin
    ra_min, ra_max = float(np.min(ra_centers)), float(np.max(ra_centers))
    dec_min, dec_max = float(np.min(dec_centers)), float(np.max(dec_centers))

    in_bounds = (
        (ra_b >= (ra_min - margin)) & (ra_b <= (ra_max + margin)) &
        (dec_b >= (dec_min - margin)) & (dec_b <= (dec_max + margin))
    )

    if not np.all(in_bounds):
        bad = np.argwhere(~in_bounds)
        i0 = tuple(bad[0])  # first offending index
        warnings.warn(
            f"Some coordinates are outside the grid range (margin={margin} deg). "
            f"Example at index {i0}: (RA={ra_b[i0]:.3f}, Dec={dec_b[i0]:.3f}) "
            f"outside RA=[{ra_min:.3f}, {ra_max:.3f}], Dec=[{dec_min:.3f}, {dec_max:.3f}]."
        )
        raise Exception("Some coordinates are outside the grid range.")

    # Evaluate interpolation for all points
    pts = np.column_stack([ra_b.ravel(), dec_b.ravel()])  # shape (N, 2)
    zp = interpolator(pts).reshape(ra_b.shape)

    if np.any(np.isnan(zp)):
        bad = np.argwhere(np.isnan(zp))
        i0 = tuple(bad[0])
        warnings.warn(
            f"Interpolation returned NaN for some points. "
            f"Example at index {i0}: (RA={ra_b[i0]:.3f}, Dec={dec_b[i0]:.3f})."
        )
        raise Exception("Interpolation failed (NaN) for some points.")

    zp = zp + global_median

    # Return float if scalar inputs
    if return_scalar_if_scalar and ra_is_scalar and dec_is_scalar:
        return float(zp)

    return zp