import warnings
import numpy as np
from os import makedirs
import astropy.units as u
from tqdm.auto import tqdm
from astropy.io import fits
from astropy.wcs import WCS
from astropy.table import Table
from splusdata.core import Core
import astropy.constants as const
from os.path import join, exists
from astropy.wcs import FITSFixedWarning
from astropy.io.fits.verify import VerifyWarning

from splusdata.scubes.read import read_scube
from splusdata.vars import BANDS, BANDWAVEINFO, get_band_info
from splusdata.features.io import print_level, convert_coord_to_degrees

__scubes_author__ = 'Eduardo A. D. Lacerda <dhubax@gmail.com>'
__scubes_version__ = '0.1.idr6-beta'

def _getval_array(pathlist, key, ext):
    return np.array([fits.getval(img, key, ext) for img in pathlist])

def _getdata_array(pathlist, ext):
    return np.array([fits.getdata(img, ext=ext) for img in pathlist])

def _getheader_array(pathlist, ext):
    return np.array([fits.getheader(img, ext=ext) for img in pathlist])

def _getval_array_mem(hdull, key, ext):
    return np.array([hdul[ext].header.get(key) for hdul in hdull])

def _getdata_array_mem(hdull, ext):
    return np.array([hdul[ext].data for hdul in hdull])

def _getheader_array_mem(hdull, ext):
    return np.array([hdul[ext].header for hdul in hdull])

def _get_band_info_array(prop):
    return np.array([get_band_info(band)[prop] for band in BANDS])

class SCubes:
    def __init__(self, ra, dec, field, size=None, username=None, password=None, verbose=1):
        # ignore some warnings without verbosity
        warnings.simplefilter('ignore', category=VerifyWarning)
        warnings.simplefilter('ignore', category=FITSFixedWarning)

        self.conn = Core(username, password, verbose=verbose)
        self.field = field
        self.verbose = verbose
        self.mem = False

        self.cubepath = None
        self._stamp_config(ra, dec, size)

    def _stamp_config(self, ra, dec, size):
        self.ra, self.dec = convert_coord_to_degrees(ra, dec)
        self.size = size

    def _getval(self, obj, key, ext):
        return _getval_array_mem(obj, key, ext) if self.mem else _getval_array(obj, key, ext)

    def _getdata(self, obj, ext):
        return _getdata_array_mem(obj, ext) if self.mem else _getdata_array(obj, ext)

    def _getheader(self, obj, ext):
        return _getheader_array_mem(obj, ext) if self.mem else _getheader_array(obj, ext)

    def _download_calibrated_stamps(self, objname, force=False):
        images = []
        wimages = []
        _kw_args = dict(ra=self.ra, dec=self.dec, size=self.size, field_name=self.field)
        for b in tqdm(BANDS, desc=f'{objname} @ {self.field} - Downloading', leave=True, position=0):
            b = b.upper().replace('J0', 'F')
            kw_args = _kw_args.copy()
            kw_args.update(band=b, weight=False)          
            if self.mem:
                x = self.conn.calibrated_stamp(**kw_args)
                images.append(x)
            else:
                filename = f'{objname}_{self.field}_{b}_{self.size}x{self.size}_swp.fits.fz'
                kw_args.update(outfile=join(self.outpath, filename))
                _ = self.conn.calibrated_stamp(**kw_args)
                images.append(kw_args['outfile'])
            # wei
            kw_args['weight'] = True
            if self.mem:
                wimages.append(self.conn.calibrated_stamp(**kw_args))
            else:
                kw_args['outfile'] = join(self.outpath, filename.replace('swp', 'swpweight'))
                _ = self.conn.calibrated_stamp(**kw_args)
                wimages.append(kw_args['outfile'])
        self.images = images
        self.wimages = wimages

    def _photospectra(self, flam_scale=None, ext=1):
        flam_scale = 1e-19 if flam_scale is None else flam_scale
        _c = const.c
        scale = (1/flam_scale)
        Jy2fnu = 3631e-23

        self.wl__b = _get_band_info_array('pivot_wave')*u.Angstrom

        self.flam_unit = u.erg / u.s / u.cm / u.cm / u.AA
        self.fnu_unit = u.erg / u.s / u.cm / u.cm / u.Hz

        # flux
        calib_data__byx = self._getdata(self.images, ext)
        fnu__byx = calib_data__byx*Jy2fnu*self.fnu_unit
        flam__byx = scale*(fnu__byx*_c/self.wl__b[:, None, None]**2).to(self.flam_unit)

        # error in flux
        zp_factor__byx = self._getdata(self.images, 2)
        absdata__byx = np.abs(calib_data__byx/zp_factor__byx)
        gain__b = self._getval(self.images, 'GAIN', ext)
        gain__byx = gain__b[:, None, None]
        weidata__byx = self._getdata(self.wimages, ext)
        absweidata__byx = np.abs(self._getdata(self.wimages, ext))
        dataerr__byx = np.sqrt(1/absweidata__byx + absdata__byx/gain__byx)
        f0__byx = zp_factor__byx*Jy2fnu
        efnu__byx = dataerr__byx*f0__byx*self.fnu_unit
        eflam__byx = scale*(efnu__byx*_c/self.wl__b[:, None, None]**2).to(self.flam_unit)

        self.flam__byx = flam__byx
        self.eflam__byx = eflam__byx
        self.weidata__byx = weidata__byx
        self.absweidata__byx = absweidata__byx

    def _stamp_WCS_to_cube_header(self, header):
        '''
        Convert WCS information from stamp to cube header.

        Parameters
        ----------
        header : :class:`~astropy.io.fits.Header`
            FITS header containing WCS information.

        Returns
        -------
        :class:`~astropy.io.fits.Header`
            Cube header with updated WCS information.
        '''
        w = WCS(header)
        nw = WCS(naxis=3)
        nw.wcs.cdelt = [w.wcs.cdelt[0], w.wcs.cdelt[1], 1]
        nw.wcs.crval = [w.wcs.crval[0], w.wcs.crval[1], 0]
        nw.wcs.crpix = [w.wcs.crpix[0], w.wcs.crpix[1], 0]
        nw.wcs.ctype = [w.wcs.ctype[0], w.wcs.ctype[1], '']
        try:
            nw.wcs.pc[:2, :2] = w.wcs.get_pc()
        except:
            pass
        return nw.to_header()
    
    def _weights_mask_hdu(self):
        # WEIGHTS MASK HDU
        w__byx = self.weidata__byx
        wmask__byx = np.where(w__byx < 0, 1, 0)
        wmask__yx = wmask__byx.sum(axis=0)
        wmask_hdu = fits.ImageHDU(wmask__yx)
        wmask_hdu.header['EXTNAME'] = ('WEIMASK', 'Sum of negative weight pixels (from 1 to 12)')
        return wmask_hdu
    
    def _metadata_hdu(self, ext=1):
        # METADATA HDU
        tab = [BANDS]
        tab.append(_get_band_info_array('central_wave'))
        tab.append(_get_band_info_array('pivot_wave'))
        # PSFFWHM
        psffwhm__b = []
        for img in self.images:
            if self.mem:
                hdr = img[ext].header
            else:
                hdr = fits.getheader(img, ext=ext)
            key = [k for k in hdr.keys() if 'FWHMMEAN' in k]
            if len(key) == 1:
                psffwhm__b.append(hdr.get(key[0]))
        tab.append(psffwhm__b)
        tab = Table(tab, names=['FILTER', 'CENTWAVE', 'PIVOTWAVE', 'PSFFWHM'])
        return fits.BinTableHDU(tab, name='METADATA')

    def _create_cube_hdulist(self, objname, ext=1, overwrite=False):
        cube_prim_hdu = fits.PrimaryHDU()
        cube_prim_hdu.header['TILE'] = self.field
        cube_prim_hdu.header['OBJECT'] = objname
        cube_prim_hdu.header['SIZE'] = (self.size, 'Side of the stamp in pixels')
        cube_prim_hdu.header['RA'] = self.ra
        cube_prim_hdu.header['DEC'] = self.dec
        hdr = self.images[0][ext].header if self.mem else fits.getheader(self.images[0], ext=ext)
        cube_prim_hdu.header.update(self._stamp_WCS_to_cube_header(hdr))
        for key in ['X0TILE', 'X01TILE', 'Y0TILE', 'Y01TILE']:
            cube_prim_hdu.header[key] = hdr.get(key)
        # DATA HDU
        flam_hdu = fits.ImageHDU(self.flam__byx.value, cube_prim_hdu.header)
        flam_hdu.header['EXTNAME'] = ('DATA', 'Name of the extension')       
        # ERRORS HDU
        eflam_hdu = fits.ImageHDU(self.eflam__byx.value, cube_prim_hdu.header)
        eflam_hdu.header['EXTNAME'] = ('ERRORS', 'Name of the extension')
        hdul = [cube_prim_hdu, flam_hdu, eflam_hdu]
        # INFO TO HEADERS
        for hdu in hdul[1:]:
            hdu.header['BSCALE'] = (self.flam_scale, 'Linear factor in scaling equation')
            hdu.header['BZERO'] = (0, 'Zero point in scaling equation') 
            hdu.header['BUNIT'] = (f'{self.flam_unit}', 'Physical units of the array values')
        hdul.append(self._weights_mask_hdu())
        hdul.append(self._metadata_hdu(ext))
        print_level(f'writting cube {self.cubepath}', 1, self.verbose)
        fits.HDUList(hdul).writeto(self.cubepath, overwrite=overwrite)
        print_level(f'Cube successfully created!', 1, self.verbose)    
        return fits.open(self.cubepath)

    def create_cube(self, flam_scale=None, objname=None, outpath=None, force=False, data_ext=1, return_scube=False, force_mem=False):
        self.flam_scale = 1e-19 if flam_scale is None else flam_scale
        self.objname = 'myobj' if objname is None else objname
        self.outpath = '.' if outpath is None else outpath
        mkcube = True
        
        try: 
            makedirs(self.outpath)
        except FileExistsError:
            print_level(f'{self.outpath}: directory already exists', 1, self.verbose)    

        self.cubepath = join(self.outpath, f'{self.objname}_cube.fits')

        if exists(self.cubepath) and not force:
            mkcube = False
            print_level(f'{self.cubepath}: cube already exists', 1, self.verbose)
       
        if not self.mem and force_mem:
            self.mem = True
        
        cube = None
        if mkcube:
            self._download_calibrated_stamps(objname, force=force)
            self._photospectra(flam_scale, ext=data_ext)

            cube = self._create_cube_hdulist(objname, ext=data_ext, overwrite=force)

            if return_scube:
                return read_scube(cube)
        return cube