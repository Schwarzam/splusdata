import numpy as np
import astropy.units as u
import astropy.constants as const

_light_speed = const.c
_flam_unit = (u.erg/(u.s*u.cm**2*u.AA))
_fnu_unit = (u.erg/(u.s*u.cm**2*u.Hz))
_ABmag_ZP = (3631*u.Jy).to(_fnu_unit)

def _3Dcalibflux_to_mag_arcsec2(input_flux, wavelenghts, pixscale, input_eflux=None):
    # fluxes (u.erg/(u.s*u.cm**2*u.AA))
    # pixscale u.arcsec/u.pix
    # wavelenght u.AA
    wavelenghts = np.expand_dims(wavelenghts, axis=(1, 2))*u.AA
    assert wavelenghts.ndim == input_flux.ndim, 'error wavelenght dimension'
    if input_eflux is not None:
        assert input_flux.ndim == input_eflux.ndim, 'error input flux and eflux dimension'   
    c = _light_speed.to(u.AA/u.s) # speed of light in AA/s
    factor = (wavelenghts**2/(c*_ABmag_ZP*pixscale**2))
    out_mag_arcsec2 = -2.5*np.log10(input_flux*factor)
    if input_eflux is not None:
        out_emag_arcsec2 = (2.5*np.log10(np.exp(1)))*input_eflux/input_flux
        return out_mag_arcsec2, out_mag_arcsec2
    return out_mag_arcsec2
    
def _data_to_zpcalibflux(data, weights, wavelenghts, zero_point, gain, flux_scale=None):
    # fluxes (u.erg/(u.s*u.cm**2*u.AA))
    # zero point (ABmag)
    # wavelenght u.AA
    # gain (e-/ADU)
    flux_scale = 1e19 if flux_scale is None else flux_scale
    wavelenghts = np.expand_dims(wavelenghts, axis=(1, 2))*u.AA   
    gain = np.expand_dims(gain, axis=(1, 2))
    c = _light_speed.to(u.AA/u.s)
    factor = c/wavelenghts**2
    zp_factor = np.power(10, -zero_point/2.5)
    f0nu = _ABmag_ZP/zp_factor
    if f0nu.ndim != data.ndim:
        f0nu = np.expand_dims(f0nu, axis=(1, 2))
    fnu = data*f0nu
    flam = flux_scale*(fnu*factor).to(_flam_unit)
    absdata = np.abs(data)
    abswei = np.abs(weights)
    dataerr = np.sqrt(1/abswei + absdata/gain)
    efnu = dataerr*f0nu
    eflam = flux_scale*(efnu*factor).to(_flam_unit)
    return flam, eflam

def _zpcalibdata_to_flux(zpcalibdata, weights, wavelenghts, zp_factor, gain, flux_scale=None):
    # fluxes (u.erg/(u.s*u.cm**2*u.AA))
    # wavelenght u.AA
    # gain (e-/ADU)
    flux_scale = 1e19 if flux_scale is None else flux_scale
    wavelenghts = np.expand_dims(wavelenghts, axis=(1, 2))*u.AA
    gain = np.expand_dims(gain, axis=(1, 2))
    c = _light_speed.to(u.AA/u.s)
    factor = c/wavelenghts**2
    calib_fnu = zpcalibdata*_ABmag_ZP
    calib_flam = flux_scale*(calib_fnu*factor).to(_flam_unit)
    absdata = np.abs(zpcalibdata/zp_factor)
    abswei = np.abs(weights)
    dataerr = np.sqrt(1/abswei + absdata/gain)
    f0nu = zp_factor*_ABmag_ZP
    efnu = dataerr*f0nu
    eflam = flux_scale*(efnu*factor).to(_flam_unit)
    return calib_flam, eflam
