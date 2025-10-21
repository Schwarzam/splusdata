import sys
import numpy as np
from os import getcwd
from os.path import join
from astropy.io import fits

from splusdata.features.io import print_level
from splusdata.scripts.args import create_parser
from splusdata.scubes.core import __scubes_author__, __scubes_version__

def ml2header_updheader(cube_filename, ml_table, force=False):
    '''
    Updates a S-CUBES raw cube primary header with the masterlist 
    information.

    Parameters
    ----------
    cube_filename : str
        Path to S-CUBES raw cube.
    
    ml_table : :class:`astropy.table.table.Table`
        Masterlist read using :meth:`astropy.io.ascii.read`
        
    force : bool, optional
        Force the update the key value is the key is existent at the 
        S-CUBES header. 
    '''
    with fits.open(cube_filename, 'update') as hdul:
        hdu = hdul['PRIMARY']

        # SNAME CONTROL
        sname = hdu.header.get('OBJECT', None)
        if sname is None:
            print_level('header: missing SNAME information')
            sys.exit(1)
        if sname not in ml_table['SNAME']:
            print_level(f'masterlist: {sname}: missing SNAME information')
            sys.exit(1)

        mlcut = ml_table[ml_table['SNAME'] == sname]
        for col in ml_table.colnames:
            v = mlcut[col][0]
            desc = None
            if v is np.ma.masked:
                v = None
            if '__' in col:
                col, desc = col.split('__')
            if not force and (col in hdu.header):
                continue 
            if col == 'FIELD' or col == 'SNAME':
                continue
            if col == 'SIZE':
                col = 'SIZE_ML'
                desc = 'SIZE masterlist'
            hdu.header.set(col, value=v, comment=desc)

SPLUS_MOTD_TOP = '┌─┐   ┌─┐┬ ┬┌┐ ┌─┐┌─┐ '
SPLUS_MOTD_MID = '└─┐───│  │ │├┴┐├┤ └─┐ '
SPLUS_MOTD_BOT = '└─┘   └─┘└─┘└─┘└─┘└─┘ '
SPLUS_MOTD_SEP = '----------------------'

SCUBES_PROG_DESC = f'''
{SPLUS_MOTD_TOP} | Create S-PLUS galaxies data cubes, a.k.a. S-CUBES. 
{SPLUS_MOTD_MID} | S-CUBES is an organized FITS file with data, errors, 
{SPLUS_MOTD_BOT} | mask and metadata about some galaxy present on any 
{SPLUS_MOTD_SEP} + S-PLUS observed tile. Any problem contact:

   {__scubes_author__}

The input values of RA and DEC will be converted to degrees using the 
splusdata.features.io.convert_coord_to_degrees(). All scripts with RA 
and DEC inputs parse angles in two different units:

- **hourangle**: using *hms* divisors; Ex: *10h37m2.5s*
- **degrees**: using *:* or *dms*  divisors; Ex: *10:37:2.5* or *10d37m2.5s*

Note that *10h37m2.5s* is a totally different angle from *10:37:2.5* 
(*159.26 deg* and *10.62 deg* respectively).

'''

size_help = 'Size of the cube in pixels. '
size_help += 'If size is a odd number, the program '
size_help += 'will choose the closest even integer.'

SCUBES_ARGS = {
    # optional arguments
    'force': ['f', dict(action='store_true', default=False, help='Force overwrite of existing files.')],
    'size': ['l', dict(default=500, type=int, help=size_help)],
    'workdir': ['w', dict(default=getcwd(), help='Working directory.')],
    'verbose': ['v', dict(action='count', default=0, help='Verbosity level.')],
    'username': ['U', dict(default=None, help='S-PLUS cloud username.')],
    'password': ['P', dict(default=None, help='S-PLUS cloud password.')],
    'force_mem': ['F', dict(action='store_true', default=False, help='Force memory mapping of downloaded input files.')],

    # positional arguments
    'field': ['pos', dict(metavar='SPLUS_TILE', help='Name of the S-PLUS field')],
    'ra': ['pos', dict(metavar='RA', help="Object's right ascension")],
    'dec': ['pos', dict(metavar='DEC', help="Object's declination")],
    'object': ['pos', dict(metavar='OBJECT_NAME', help="Object's name")],
}
           
def scubes_argparse(args):
    '''
    A particular parser of the command-line arguments for `scubes` script.

    Parameters
    ----------
    args : :class:`argparse.Namespace`
        Command-line arguments parsed by :meth:`argparse.ArgumentParser.parse_args`

    Returns
    -------
    :class:`argparse.Namespace`
        Command-line arguments parsed.
    '''
    # closest even
    args.size = round(float(args.size)/2)*2

    return args

def scubes():
    '''
    Script function for creating S-PLUS galaxy data cubes (S-CUBES).

    Raises
    ------
    SystemExit
        If SExtractor is not found.

    Returns
    -------
    None
    '''
    from splusdata.scubes.core import SCubes

    parser = create_parser(args_dict=SCUBES_ARGS, program_description=SCUBES_PROG_DESC)
    # ADD VERSION OPTION
    parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__scubes_version__))
    args = scubes_argparse(parser.parse_args(args=sys.argv[1:]))

    SCubes(
        ra=args.ra, dec=args.dec, field=args.field, 
        size=args.size, username=args.username, password=args.password,
        verbose=args.verbose,
    ).create_cube(
        objname=args.object, 
        outpath=join(args.workdir, args.object), 
        force=args.force, force_mem=args.force_mem
    )

SCUBESML_PROG_DESC = f'''
{SPLUS_MOTD_TOP} | scubesml script:
{SPLUS_MOTD_MID} | Create S-PLUS galaxies data cubes, a.k.a. S-CUBES
{SPLUS_MOTD_BOT} | using the masterlist information as input.
{SPLUS_MOTD_SEP} + 

   {__scubes_author__}
'''

SCUBESML_ARGS = {
    # optional arguments
    'force': ['f', dict(action='store_true', default=False, help='Force overwrite of existing files.')],
    'size_multiplicator': ['S', dict(default=10, type=float, help='Factor to multiply the SIZE__pix value of the masterlist to create the galaxy size. If size is a odd number, the program will choose the closest even integer.')],
    'min_size': ['m', dict(default=200, type=int, help='Minimal size of the cube in pixels. If size negative, uses the original value of size calculation.')],
    'workdir': ['w', dict(default=getcwd(), help='Working directory.')],
    'verbose': ['v', dict(action='count', default=0, help='Verbosity level.')],
    'username': ['U', dict(default=None, help='S-PLUS Cloud username.')],
    'password': ['P', dict(default=None, help='S-PLUS Cloud password.')],
    'sname': ['O', dict(default=None, metavar='OBJECT_SNAME', help="Object's masterlist SNAME")],
    'force_mem': ['F', dict(action='store_true', default=False, help='Force memory mapping of downloaded input files.')],

    'masterlist': ['pos', dict(metavar='MASTERLIST', help='Path to masterlist file')]
}

def scubesml_argparse(args):
    '''
    A particular parser of the command-line arguments for `scubesml` script.

    Parameters
    ----------
    args : :class:`argparse.Namespace`
        Command-line arguments parsed by :meth:`argparse.ArgumentParser.parse_args`

    Returns
    -------
    :class:`argparse.Namespace`
        Command-line arguments parsed.
    '''
    # closest even
    from astropy.io import ascii

    try:
        args.ml = ascii.read(args.masterlist)
    except:
        print_level(f'{args.masterlist}: unable to read file')
        sys.exit(1)
    
    return args

def scubesml():
    '''
    Script for creating S-PLUS galaxy data cubes (S-CUBES) using the 
    masterlist for the input arguments.

    Raises
    ------
    SystemExit
        If masterlist not found

    Returns
    -------
    None
    '''

    from splusdata.scubes.core import SCubes
    
    parser = create_parser(args_dict=SCUBESML_ARGS, program_description=SCUBESML_PROG_DESC)
    # ADD VERSION OPTION
    parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__scubes_version__))
    args = scubesml_argparse(parser.parse_args(args=sys.argv[1:]))

    sname_list = args.ml['SNAME'] if args.sname is None else [args.sname]

    for sname in sname_list:
        mlcut = args.ml[args.ml['SNAME'] == sname]
        ra = mlcut['RA__deg'][0]
        dec = mlcut['DEC__deg'][0]
        field = mlcut['FIELD'][0]
        size_pix = max(round(args.size_multiplicator*float(mlcut['SIZE__pix'][0])/2)*2, args.min_size)
        #print(size_pix)
        #print(ra, dec, field, size_pix)
        creator = SCubes(
            ra=ra, dec=dec, field=field, 
            size=size_pix, 
            username=args.username, password=args.password, verbose=args.verbose
        )
        #try:
        creator.create_cube(objname=sname, outpath=args.workdir, force=args.force, force_mem=args.force_mem)
        if creator.cubepath is not None:
            ml2header_updheader(creator.cubepath, args.ml)
        #except Exception as e:
        #    print_level(f'{sname}: Cube creation failed: {e}')