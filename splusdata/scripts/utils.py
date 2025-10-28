import sys
import numpy as np
from os import getcwd
from os.path import join
from astropy.io import fits

from splusdata.features.io import print_level
from splusdata.scripts.args import create_parser
from splusdata import Core


FIELD_FRAME_ARGS = {
    # optional arguments
    'verbose': ['v', dict(action='count', default=0, help='Verbosity level.')],
    'username': ['U', dict(default=None, help='S-PLUS cloud username.')],
    'password': ['P', dict(default=None, help='S-PLUS cloud password.')],
    'weight': ['w', dict(action='store_true', default=False, help='Download the weight map associated to the stamp.')],   
    'data_release': ['D', dict(default='DR4', help='S-PLUS data release version.')],

    # positional arguments
    'field': ['pos', dict(metavar='FIELD', help='Field identifier, e.g., "SPLUS-n01s10"')],
    'band': ['pos', dict(metavar='BAND', help='S-PLUS band, e.g., "R", "I", "F660", "U".')],
}

FIELD_FRAME_PROG_DESC = f'''
    Download and open a full field FITS image.
'''

def field_frame():
    '''
    Script function for downloading a S-PLUS field FITS image.

    Raises
    ------
    SystemExit
        If S-PLUS data server is not reachable.

    Returns
    -------
    None
    '''
    parser = create_parser(args_dict=FIELD_FRAME_ARGS, program_description=FIELD_FRAME_PROG_DESC)
    args = parser.parse_args(args=sys.argv[1:])

    conn = Core(args.username, args.password)

    print_level(f'Downloading field {args.field} - band {args.band}', 1, args.verbose)
    outfile = f'{args.field}_{args.band}.fits.fz'
    conn.field_frame(args.field, args.band, weight=args.weight, data_release=args.data_release, outfile=outfile)

STAMP_ARGS = {
    # optional arguments
    'verbose': ['v', dict(action='count', default=0, help='Verbosity level.')],
    'username': ['U', dict(default=None, help='S-PLUS cloud username.')],
    'password': ['P', dict(default=None, help='S-PLUS cloud password.')],
    'weight': ['w', dict(action='store_true', default=False, help='Download the weight map associated to the stamp.')],   
    'field_name': ['F', dict(metavar='FIELD', help='Field identifier, e.g., "SPLUS-n01s10"')],
    'size_unit': ['u', dict(metavar='SIZE_UNIT', choices=['arcsec', 'arcmin', 'pixels'], default='pix', help='Unit of the size parameter (arcsec, arcmin, pixels).')],
    'data_release': ['D', dict(default='DR4', help='S-PLUS data release version.')],
    'outfile': ['o', dict(default='stamp.fits.fz', help='Output filename for the stamp FITS image.')],

    # positional arguments
    'ra': ['pos', dict(metavar='RA', help="Object's right ascension")],
    'dec': ['pos', dict(metavar='DEC', help="Object's declination")],
    'size': ['pos', dict(metavar='SIZE', help='Size of the stamp in size_unit (defaults to pixels) (see --size_unit).')],
    'band': ['pos', dict(metavar='BAND', help='S-PLUS band, e.g., "R", "I", "F660", "U".')],
}

STAMP_PROG_DESC = f'''
    Download a FITS stamp (cutout) by coordinates or by object name.
'''

def stamp():
    '''
    Script function for downloading a S-PLUS stamp FITS image.

    Raises
    ------
    SystemExit
        If S-PLUS data server is not reachable.

    Returns
    -------
    None
    '''
    parser = create_parser(args_dict=STAMP_ARGS, program_description=STAMP_PROG_DESC)
    args = parser.parse_args(args=sys.argv[1:])

    conn = Core(args.username, args.password)
    print_level(f'Downloading stamp at RA: {args.ra}, DEC: {args.dec} - band {args.band}', 1, args.verbose)
    conn.stamp(args.ra, args.dec, args.size, args.band, 
               weight=args.weight, field_name=args.field_name, 
               size_unit=args.size_unit, data_release=args.data_release, outfile=args.outfile,
    )

LUPTON_RGB_ARGS = {
    'verbose': ['v', dict(action='count', default=0, help='Verbosity level.')],
    'username': ['U', dict(default=None, help='S-PLUS cloud username.')],
    'password': ['P', dict(default=None, help='S-PLUS cloud password.')],
    'rgb': ['b', dict(metavar='BAND1,BAND2,BAND3', nargs=3, default='I,R,G', help='Space-separated bands for RGB channels (default: I R G).')],
    'field_name': ['F', dict(metavar='FIELD', help='Field identifier, e.g., "SPLUS-n01s10"')],
    'size_unit': ['u', dict(metavar='SIZE_UNIT', choices=['arcsec', 'arcmin', 'pixels'], default='pix', help='Unit of the size parameter (arcsec, arcmin, pixels).')],
    'data_release': ['D', dict(default='DR4', help='S-PLUS data release version.')],
    'outfile': ['o', dict(default='lupton_RGB.png', help='Output filename for the Lupton RGB image.')],
    'Q': ['Q', dict(type=float, default=8, help='Lupton Q parameter (default: 8).')],
    'stretch': ['s', dict(type=float, default=3, help='Lupton stretch parameter (default: 3).')],

    # positional arguments
    'ra': ['pos', dict(metavar='RA', help="Object's right ascension")],
    'dec': ['pos', dict(metavar='DEC', help="Object's declination")],
    'size': ['pos', dict(metavar='SIZE', help='Size of the stamp in size_unit (defaults to pixels) (see --size_unit).')],
}

LUPTON_RGB_PROG_DESC = f'''
    Create a Lupton RGB composite.
'''

def lupton_rgb_argparse(args):
    '''
    A particular parser of the command-line arguments for `lupton_rgb` script.

    Parameters
    ----------
    args : :class:`argparse.Namespace`
        Command-line arguments parsed by :meth:`argparse.ArgumentParser.parse_args`

    Returns
    -------
    :class:`argparse.Namespace`
        Command-line arguments parsed.
    '''
    # split RGB bands
    args.R, args.G, args.B = args.rgb
    return args

def lupton_rgb():
    '''
    Script function for downloading a S-PLUS Lupton RGB image.

    Raises
    ------
    SystemExit
        If S-PLUS data server is not reachable.

    Returns
    -------
    None
    '''
    parser = create_parser(args_dict=LUPTON_RGB_ARGS, program_description=LUPTON_RGB_PROG_DESC)
    args = lupton_rgb_argparse(args=parser.parse_args(args=sys.argv[1:]))

    conn = Core(args.username, args.password)

    print_level(f'Downloading Lupton RGB image at RA: {args.ra}, DEC: {args.dec}', 1, args.verbose)
    conn.lupton_rgb(args.ra, args.dec, args.size, R=args.R, G=args.G, B=args.B,
                    field_name=args.field_name, size_unit=args.size_unit,
                    data_release=args.data_release, outfile=args.outfile,
                    Q=args.Q, stretch=args.stretch
    )

TRILOGY_IMAGE_ARGS = {
    'verbose': ['v', dict(action='count', default=0, help='Verbosity level.')],
    'username': ['U', dict(default=None, help='S-PLUS cloud username.')],
    'password': ['P', dict(default=None, help='S-PLUS cloud password.')],
    'red': ['R', dict(metavar='RED_BAND', default='I', nargs='+', help='Band(s) for the red channel (default: I R G).')],
    'green': ['G', dict(metavar='GREEN_BAND', default='R', nargs='+', help='Band(s) for the green channel (default: R G B).')],
    'blue': ['B', dict(metavar='BLUE_BAND', default='G', nargs='+', help='Band(s) for the blue channel (default: G B I).')],
    'field_name': ['F', dict(metavar='FIELD', help='Field identifier, e.g., "SPLUS-n01s10"')],
    'size_unit': ['u', dict(metavar='SIZE_UNIT', choices=['arcsec', 'arcmin', 'pixels'], default='pix', help='Unit of the size parameter (arcsec, arcmin, pixels).')],
    'data_release': ['D', dict(default='DR4', help='S-PLUS data release version.')],
    'outfile': ['o', dict(default='trilogy_image.png', help='Output filename for the Lupton RGB image.')],
    'noiselum': ['n', dict(type=float, default=0.15, help='Controls noise luminance suppression')],
    'satpercent': ['s', dict(type=float, default=0.15, help='Percentile value for saturation clipping (default: 0.15).')],
    'colorsatfac': ['c', dict(type=float, default=2, help='Factor for color saturation (default: 2).')],

    # positional arguments
    'ra': ['pos', dict(metavar='RA', help="Object's right ascension")],
    'dec': ['pos', dict(metavar='DEC', help="Object's declination")],
    'size': ['pos', dict(metavar='SIZE', help='Size of the stamp in size_unit (defaults to pixels) (see --size_unit).')],
}

TRILOGY_IMAGE_PROG_DESC = f'''
    Create a Trilogy RGB composite (multi-filter blend).
'''

def trilogy_image():
    '''
    Script function for downloading a S-PLUS Trilogy RGB image.

    Raises
    ------
    SystemExit
        If S-PLUS data server is not reachable.

    Returns
    -------
    None
    '''
    parser = create_parser(args_dict=TRILOGY_IMAGE_ARGS, program_description=TRILOGY_IMAGE_PROG_DESC)
    args = parser.parse_args(args=sys.argv[1:])

    conn = Core(args.username, args.password)

    print_level(f'Downloading Trilogy RGB image at RA: {args.ra}, DEC: {args.dec}', 1, args.verbose)
    conn.trilogy_image(args.ra, args.dec, args.size, R=args.red, G=args.green, B=args.blue,
                       field_name=args.field_name, size_unit=args.size_unit,
                       data_release=args.data_release, outfile=args.outfile,
                       noiselum=args.noiselum, satpercent=args.satpercent,
                       colorsatfac=args.colorsatfac,
    )

CALIBRATED_STAMP_ARGS = {
    # optional arguments
    'verbose': ['v', dict(action='count', default=0, help='Verbosity level.')],
    'username': ['U', dict(default=None, help='S-PLUS cloud username.')],
    'password': ['P', dict(default=None, help='S-PLUS cloud password.')],
    'weight': ['w', dict(action='store_true', default=False, help='Download the weight map associated to the stamp.')],   
    'field_name': ['F', dict(metavar='FIELD', help='Field identifier, e.g., "SPLUS-n01s10"')],
    'size_unit': ['u', dict(metavar='SIZE_UNIT', choices=['arcsec', 'arcmin', 'pixels'], default='pix', help='Unit of the size parameter (arcsec, arcmin, pixels).')],
    'data_release': ['D', dict(default='DR4', help='S-PLUS data release version.')],
    'outfile': ['o', dict(default='stamp.fits.fz', help='Output filename for the stamp FITS image.')],

    # positional arguments
    'ra': ['pos', dict(metavar='RA', help="Object's right ascension")],
    'dec': ['pos', dict(metavar='DEC', help="Object's declination")],
    'size': ['pos', dict(metavar='SIZE', help='Size of the stamp in size_unit (defaults to pixels) (see --size_unit).')],
    'band': ['pos', dict(metavar='BAND', help='S-PLUS band, e.g., "R", "I", "F660", "U".')],
}

CALIBRATED_STAMP_PROG_DESC = f'''
    Create a stamp and return a photometrically calibrated PrimaryHDU.

    This computes a cutout via `stamp(...)`, then loads the appropriate DR6+
    per-field zero-point model and applies spatially varying calibration.
'''

def calibrated_stamp():
    '''
    Script function for downloading a S-PLUS calibrated stamp FITS image.

    Raises
    ------
    SystemExit
        If S-PLUS data server is not reachable.

    Returns
    -------
    None
    '''
    parser = create_parser(args_dict=CALIBRATED_STAMP_ARGS, program_description=CALIBRATED_STAMP_PROG_DESC)
    args = parser.parse_args(args=sys.argv[1:])

    conn = Core(args.username, args.password)
    print_level(f'Downloading calibrated stamp at RA: {args.ra}, DEC: {args.dec} - band {args.band}', 1, args.verbose)
    conn.calibrated_stamp(args.ra, args.dec, args.size, args.band, 
               weight=args.weight, field_name=args.field_name, 
               size_unit=args.size_unit, data_release=args.data_release, outfile=args.outfile,
    )
