import numpy as np
from scipy.ndimage import median_filter

def get_iso_sky(refmag__yx, flux__lyx, isophotal_limit=25, isophotal_medsize=10, stars_mask=None, n_sigma=3, n_iter=5, clip_neg=False):
    '''
    Estimate the sky flux by masking stars and clipping outliers in the flux data.

    Parameters
    ----------
    refmag__yx : np.ndarray
        2D array of reference magnitudes used for creating the isophotal mask.
    
    flux__lyx : np.ndarray
        3D array of flux values, where the first axis corresponds to different layers (e.g., different filters or exposures) 
        and the last two axes correspond to spatial dimensions (y, x).
    
    isophotal_limit : float, optional
        The threshold value for the reference magnitude used to mask sky pixels (default is 25).
    
    isophotal_medsize : int, optional
        Size of the window used for the median filter when smoothing the mask (default is 10).
    
    stars_mask : np.ndarray, optional
        2D boolean array where 1 indicates a star, and 0 means no star (default is None).
    
    n_sigma : float, optional
        The threshold number of standard deviations to use for clipping outliers in sky flux values (default is 3).
    
    n_iter : int, optional
        The number of iterations to perform for sigma clipping to remove outliers (default is 5).
    
    clip_neg : bool, optional
        If True, clip both negative and positive outliers. If False, only clip positive outliers (default is False).

    Returns
    -------
    sky : dict
        Dictionary containing the following fields:
        
        - 'isophotal_limit' : float
            The isophotal limit used for the sky mask.
        
        - 'isophotal_medsize' : int
            The median filter window size used to smooth the sky mask.
        
        - 'flux__lyx' : np.ma.MaskedArray
            The 3D array of sky flux values with outliers masked.
        
        - 'mask__yx' : np.ndarray
            2D boolean array where `True` indicates sky pixels, `False` indicates non-sky pixels.
        
        - 'mean__l' : np.ndarray
            1D array of mean sky flux values for each layer.
        
        - 'median__l' : np.ndarray
            1D array of median sky flux values for each layer.
        
        - 'std__l' : np.ndarray
            1D array of standard deviation of sky flux values for each layer.

    Notes
    -----
    The sky mask is created by masking pixels where the reference magnitude is below a certain threshold and applying 
    a median filter to smooth the mask. The function then iteratively clips outliers in the flux data using sigma clipping.
    Sky flux values for each layer (e.g., different filters or exposures) are stored in a masked array to exclude outliers.
    '''
    # from: https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.median_filter.html
    # size gives the shape that is taken from the input array, 
    # at every element position, to define the input to the filter 
    # function
    stars_mask = np.zeros_like(refmag__yx) if stars_mask is None else stars_mask

    sky_pixels__yx = refmag__yx > isophotal_limit 
    sky_pixels__yx = median_filter(sky_pixels__yx, size=isophotal_medsize)
    sky_pixels__yx = (stars_mask == 0) & sky_pixels__yx
    
    # clipping sky fluxes for outliers
    sky_flux__lyx = np.ma.zeros(flux__lyx.shape)

    for i in range(sky_flux__lyx.shape[0]):
        sky_flux__yx = np.ma.masked_array(flux__lyx[i], mask=~sky_pixels__yx)
        n = n_iter
        while n > 0:
            _med = np.ma.median(sky_flux__yx)
            _sig = np.ma.std(sky_flux__yx)
            outliers = (sky_flux__yx - _med) > n_sigma*_sig
            if clip_neg:
                outliers = np.abs(sky_flux__yx - _med) > n_sigma*_sig
            sky_flux__yx[outliers] = np.ma.masked
            n -= 1
        sky_flux__lyx[i] = sky_flux__yx

    sky = {}
    sky['isophotal_limit'] = isophotal_limit
    sky['isophotal_medsize'] = isophotal_medsize
    sky['flux__lyx'] = sky_flux__lyx
    sky['mask__yx'] = (sky_flux__lyx.mask.sum(axis=0) == 0)
    sky['mean__l'] = np.ma.mean(flux__lyx[:, sky['mask__yx']], axis=1)
    sky['median__l'] = np.ma.median(flux__lyx[:, sky['mask__yx']], axis=1)
    sky['std__l'] = np.ma.std(flux__lyx[:, sky['mask__yx']], axis=1)

    return sky, sky_pixels__yx