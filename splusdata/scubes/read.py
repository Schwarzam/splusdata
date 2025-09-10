import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from argparse import Namespace
from copy import deepcopy as copy
from astropy.coordinates import SkyCoord
from astropy.visualization import make_lupton_rgb

class tupperware_none(Namespace):
    def __init__(self):
        pass

    def __getattr__(self, attr):
        r = self.__dict__.get(attr, None)
        return r
    
# create filters indexes list
def _parse_filters_tuple(f_tup, filters):
    if isinstance(f_tup, list):
        f_tup = tuple(f_tup)
    i_f = []
    if isinstance(f_tup, tuple):
        for f in f_tup:
            if isinstance(f, str):
                i_f.append(filters.index(f))
            else:
                i_f.append(f)
    else:
        if isinstance(f_tup, str):
            i_f.append(filters.index(f_tup))
        else:
            i_f.append(f_tup)
    return i_f

def make_RGB_tom(flux__byx,
        rgb=(7, 5, 9), rgb_f=(1, 1, 1), 
        pminmax=(5, 95), im_max=255, 
        # astropy.visualization.make_lupton_rgb() input vars
        minimum=(0, 0, 0), Q=0, stretch=10):
    # get filters index(es)
    pmin, pmax = pminmax
    RGB = []
    for f_tup in rgb:
        # get fluxes list
        if isinstance(f_tup, list):
            f_tup = tuple(f_tup)
        i_f = []
        if isinstance(f_tup, tuple):
            for f in f_tup:
                i_f.append(f)
        else:
            i_f.append(f_tup)
        C = copy(flux__byx[i_f, :, :]).sum(axis=0)
        # percentiles
        Cmin, Cmax = np.nanpercentile(C, pmin), np.nanpercentile(C, pmax)
        # calc color intensities
        RGB.append(im_max*(C - Cmin)/(Cmax - Cmin))
    R, G, B = RGB
    # filters factors
    fR, fG, fB = rgb_f
    # make RGB image
    return make_lupton_rgb(fR*R, fG*G, fB*B, Q=Q, minimum=minimum, stretch=stretch)

def get_distance(x, y, x0, y0, pa=0.0, ba=1.0):
    '''
    Return an image (:class:`numpy.ndarray`)
    of the distance from the center ``(x0, y0)`` in pixels,
    assuming a projected disk.

    Parameters
    ----------
    x : array
        X coordinates to get the pixel distances.

    y : array
        y coordinates to get the pixel distances.

    x0 : float
        X coordinate of the origin.

    y0 : float
        Y coordinate of the origin.

    pa : float, optional
        Position angle in radians, counter-clockwise relative
        to the positive X axis.

    ba : float, optional
        Ellipticity, defined as the ratio between the semiminor
        axis and the semimajor axis (:math:`b/a`).

    Returns
    -------
    pixel_distance : array
        Pixel distances.
    '''
    y = np.asarray(y) - y0
    x = np.asarray(x) - x0
    x2 = x**2
    y2 = y**2
    xy = x*y

    a_b = 1/ba
    cos_th = np.cos(pa)
    sin_th = np.sin(pa)

    A1 = cos_th**2 + a_b**2*sin_th**2
    A2 = -2*cos_th*sin_th*(a_b**2 - 1)
    A3 = sin_th**2 + a_b**2*cos_th* 2

    return np.sqrt(A1*x2 + A2*xy + A3*y2)

def get_image_distance(shape, x0, y0, pa=0.0, ba=1.0):
    '''
    Return an image (:class:`numpy.ndarray`)
    of the distance from the center ``(x0, y0)`` in pixels,
    assuming a projected disk.

    Parameters
    ----------
    shape : (float, float)
        Shape of the image to get the pixel distances.

    x0 : float
        X coordinate of the origin.

    y0 : float
        Y coordinate of the origin.

    pa : float, optional
        Position angle in radians, counter-clockwise relative
        to the positive X axis. Defaults to ``0.0``.

    ba : float, optional
        Ellipticity, defined as the ratio between the semiminor
        axis and the semimajor axis (:math:`b/a`). Defaults to ``1.0``.

    Returns
    -------
    pixel_distance : 2-D array
        Image containing the distances.

    See also
    --------
    :func:`get_distance`

    '''
    y, x = np.indices(shape)
    return get_distance(x, y, x0, y0, pa, ba)

def radial_profile(prop, bin_r, x0, y0, pa=0.0, ba=1.0, rad_scale=1.0, mask=None, mode='mean', return_npts=False):
    '''
    Calculate the radial profile of an N-D image.

    Parameters
    ----------
    prop : array
        Image of property to calculate the radial profile.

    bin_r : array
        Semimajor axis bin boundaries in units of ``rad_scale``.

    x0 : float
        X coordinate of the origin.

    y0 : float
        Y coordinate of the origin.

    pa : float, optional
        Position angle in radians, counter-clockwise relative
        to the positive X axis.

    ba : float, optional
        Ellipticity, defined as the ratio between the semiminor
        axis and the semimajor axis (:math:`b/a`).

    rad_scale : float, optional
        Scale of the bins, in pixels. Defaults to 1.0.

    mask : array, optional
        Mask containing the pixels to use in the radial profile.
        Must be bidimensional and have the same shape as the last
        two dimensions of ``prop``. Default: no mask.

    mode : string, optional
        One of:
            * ``'mean'``: Compute the mean inside the radial bins (default).
            * ``'median'``: Compute the median inside the radial bins.
            * ``'sum'``: Compute the sum inside the radial bins.
            * ``'var'``: Compute the variance inside the radial bins.
            * ``'std'``: Compute the standard deviation inside the radial bins.

    return_npts : bool, optional
        If set to ``True``, also return the number of points inside
        each bin. Defaults to ``False``.


    Returns
    -------
    radProf : [masked] array
        Array containing the radial profile as the last dimension.
        Note that ``radProf.shape[-1] == (len(bin_r) - 1)``
        If ``prop`` is a masked aray, this and ``npts`` will be
        a masked array as well.

    npts : [masked] array, optional
        The number of points inside each bin, only if ``return_npts``
        is set to ``True``.


    See also
    --------
    :func:`get_image_distance`
    '''
    def red(func, x, fill_value):
        if x.size == 0: return fill_value, fill_value
        if x.ndim == 1: return func(x), len(x)
        return func(x, axis=-1), x.shape[-1]

    imshape = prop.shape[-2:]
    nbins = len(bin_r) - 1
    new_shape = prop.shape[:-2] + (nbins,)
    r__yx = get_image_distance(imshape, x0, y0, pa, ba) / rad_scale
    if mask is None:
        mask = np.ones(imshape, dtype=bool)
    if mode == 'mean':
        reduce_func = np.mean
    elif mode == 'median':
        reduce_func = np.median
    elif mode == 'sum':
        reduce_func = np.sum
    elif mode == 'var':
        reduce_func = np.var
    elif mode == 'std':
        reduce_func = np.std
    else:
        raise ValueError('Invalid mode: %s' % mode)

    if isinstance(prop, np.ma.MaskedArray):
        n_bad = prop.mask.astype('int')
        max_bad = 1.0
        while n_bad.ndim > 2:
            max_bad *= n_bad.shape[0]
            n_bad = n_bad.sum(axis=0)
        mask = mask & (n_bad / max_bad < 0.5)
        prop_profile = np.ma.masked_all(new_shape)
        npts = np.ma.masked_all((nbins,))
        prop_profile.fill_value = prop.fill_value
        reduce_fill_value = np.ma.masked
    else:
        prop_profile = np.empty(new_shape)
        npts = np.empty((nbins,))
        reduce_fill_value = np.nan
    if mask.any():
        dist_flat = r__yx[mask]
        dist_idx = np.digitize(dist_flat, bin_r)
        prop_flat = prop[...,mask]
        for i in range(0, nbins):
            prop_profile[..., i], npts[i] = red(reduce_func, prop_flat[..., dist_idx == i+1], reduce_fill_value)

    if return_npts:
        return prop_profile, npts
    return prop_profile

class read_scube:
    def __init__(self, data):
        self._read_data(data)
        self._init()
           
    def _read_data(self, data):
        self._hdulist = fits.open(data) if isinstance(data, str) else data

    def _init_wcs(self):
        '''
        Initializes the World Coordinate System (WCS) from the data header.
        '''        
        self.wcs = WCS(self.data_header, naxis=2)

    def _init_centre(self):
        '''
        Calculates the central coordinates of the object in pixel space using WCS.
        '''        
        self.cent_coord = SkyCoord(self.ra, self.dec, unit=('deg', 'deg'), frame='icrs')
        self.x0, self.y0 = self.wcs.world_to_pixel(self.cent_coord)
        self.i_x0 = int(self.x0)
        self.i_y0 = int(self.y0)

    def _mag_values(self):
        '''
        Computes the magnitude per square arcsecond and corresponding errors from the flux values.
        '''        
        a = 1/(2.997925e18*3631.0e-23*self.pixscale**2)
        x = a*(self.flux__byx*self.pivot_wave[:, np.newaxis, np.newaxis]**2)
        self.mag_arcsec2__byx = -2.5*np.log10(x)
        self.emag_arcsec2__byx = (2.5*np.log10(np.exp(1)))*self.eflux__byx/self.flux__byx

    def _init(self):
        '''
        Initializes the class by setting WCS, central coordinates, and magnitude values.
        Also calculates the pixel distance from the central coordinates.
        '''        
        self._init_wcs()
        self._init_centre()
        self._mag_values()
        self.pa, self.ba = 0, 1
        self.set_ellipticity(self.pa, self.ba)
        #self.pixel_distance__yx = get_image_distance(self.weimask__yx.shape, x0=self.x0, y0=self.y0, pa=self.pa, ba=self.ba)

    def set_ellipticity(self, pa, ba):
        self.pa = pa
        self.ba = ba
        self.pixel_distance__yx = get_image_distance(self.weimask__yx.shape, x0=self.x0, y0=self.y0, pa=self.pa, ba=self.ba)

    def get_filter_i(self, filt):
        return self.filters.index(filt)

    def lRGB_image(
        self, rgb=('r', 'g', 'i'), rgb_f=(1, 1, 1), 
        pminmax=(5, 95), im_max=255, 
        # astropy.visualization.make_lupton_rgb() input vars
        minimum=(0, 0, 0), Q=0, stretch=3):
        '''
        Creates an RGB image from the data cube using specified filters.

        Parameters
        ----------
        rgb : tuple of str or tuple of int, optional
            Tuple specifying the filters to use for the red, green, and blue channels (default is ('rSDSS', 'gSDSS', 'iSDSS')).
        
        rgb_f : tuple of float, optional
            Scaling factors for the red, green, and blue channels (default is (1, 1, 1)).
        
        pminmax : tuple of int, optional
            Percentiles for scaling the RGB intensities (default is (5, 95)).
        
        im_max : int, optional
            Maximum intensity value for the RGB image (default is 255).
        
        minimum : tuple of float, optional
            Minimum values for scaling the RGB channels (default is (0, 0, 0)).
        
        Q : float, optional
            Parameter for controlling the contrast in the Lupton RGB scaling (default is 0).
        
        stretch : float, optional
            Stretch factor for enhancing the RGB intensities (default is 3).

        Returns
        -------
        np.ndarray
            3D array representing the RGB image with shape (height, width, 3).
        '''
        # check filters
        if len(rgb) != 3:
            return None

        # check factors
        if isinstance(rgb_f, tuple) or isinstance(rgb_f, list):
            N = len(rgb_f)
            if N != 3:
                if N == 1:
                    f = rgb_f[0]
                    rgb_f = (f, f, f)
                else:
                    # FAIL
                    return None
        else:
            rgb_f = (rgb_f, rgb_f, rgb_f)

        i_rgb = [_parse_filters_tuple(x, self.filters) for x in rgb]

        return make_RGB_tom(
            self.flux__byx, rgb=i_rgb, rgb_f=rgb_f, 
            pminmax=pminmax, im_max=im_max, 
            minimum=minimum, Q=Q, stretch=stretch
        )

    @property
    def weimask__byx(self):
        return np.broadcast_to(self.weimask__yx, (len(self.filters), self.size, self.size))

    @property
    def primary_header(self):
        return self._hdulist['PRIMARY'].header

    @property
    def data_header(self):
        return self._hdulist['DATA'].header

    @property
    def metadata(self):
        return self._hdulist['METADATA'].data
    
    @property
    def filters(self):
        return self.metadata['FILTER'].tolist()

    @property
    def central_wave(self):
        return self.metadata['CENTRALWAVE']

    @property
    def pivot_wave(self):
        return self.metadata['PIVOTWAVE']

    @property
    def psf_fwhm(self):
        return self.metadata['PSFFWHM']

    @property
    def tile(self):
        return self.primary_header.get('TILE', None)
    
    @property
    def galaxy(self):
        return self.primary_header.get('GALAXY', None)
    
    @property
    def size(self):
        return self.primary_header.get('SIZE', None)
       
    @property
    def ra(self):
        return self.primary_header.get('RA', None)
    
    @property
    def dec(self):
        return self.primary_header.get('DEC', None)

    @property
    def x0tile(self):
        return self.primary_header.get('X0TILE', None)

    @property
    def y0tile(self):
        return self.primary_header.get(['Y0TILE'], None)

    @property
    def pixscale(self):
        return self.data_header.get('PIXSCALE', 0.55)

    @property 
    def weimask__yx(self):
        return self._hdulist['WEIMASK'].data

    @property 
    def flux__byx(self):
        return self._hdulist['DATA'].data

    @property 
    def eflux__byx(self):
        return self._hdulist['ERRORS'].data
    
    @property
    def n_x(self):
        return self.data_header.get('NAXIS1', None)
    
    @property
    def n_y(self):
        return self.data_header.get('NAXIS2', None)
    
    @property
    def n_filters(self):
        return self.data_header['NAXIS3']
    
    @property
    def SN__byx(self):
        return self.flux__byx/self.eflux__byx

    @property
    def mag__byx(self):
        return self.mag_arcsec2__byx

    @property
    def emag__byx(self):
        return self.emag_arcsec2__byx