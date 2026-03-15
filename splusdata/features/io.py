import re
from os.path import basename
from datetime import datetime
from astropy.coordinates import SkyCoord


def print_level(msg, level=0, verbose=0):
    """
    Print a message with a specified verbosity level.

    Parameters
    ----------
    msg : str
        The message to be printed.

    level : int, optional
        The verbosity level of the message. Defaults to 0.

    verbose : int, optional
        The overall verbosity level. Messages with verbosity levels less than or equal to
        this value will be printed. Defaults to 0.
    """
    import __main__ as main

    try:
        __script_name__ = basename(main.__file__)
    except AttributeError:
        __script_name__ = ""

    if verbose >= level:
        print(f"[{datetime.now().isoformat()}] - {__script_name__}: {msg}")


def check_units(ra, dec):
    """
    Check and add units to the input coordinates if units are missing.

    Parameters
    ----------
    ra : str or numeric
        Right ascension coordinate.

    dec : str or numeric
        Declination coordinate.

    Returns
    -------
    tuple
        Tuple containing the checked and possibly modified right ascension and declination.
    """

    # Pattern to match: any letter (a-z, A-Z) or "°"
    # Default unit is degrees, so if no unit, then is assumed as degs.
    def check_deg(input_string):
        pattern = r"[a-zA-Z°]"
        # re.search returns a match object if the pattern is found, None otherwise
        if re.search(pattern, input_string):
            return input_string
        else:
            return input_string + "°"

    def check(input_string):
        pattern = r"[hdms]"
        x = re.search(pattern, input_string)
        if x is None:
            return check_deg(input_string)
        else:
            return input_string

    if not isinstance(ra, str):
        ra = str(ra)

    if not isinstance(dec, str):
        dec = str(dec)

    return check(ra), check(dec)


def convert_coord_to_degrees(ra, dec, frame="icrs"):
    """
    Convert the input celestial coordinates to degrees.

    Parameters
    ----------
    ra : str or numeric
        Right ascension coordinate.

    dec : str or numeric
        Declination coordinate.

    frame : str, optional
        Reference frame for the coordinates. Defaults to 'icrs'.

    Returns
    -------
    tuple
        Tuple containing the right ascension and declination converted to degrees.
    """
    ra, dec = check_units(ra, dec)

    # Create a SkyCoord object
    c = SkyCoord(ra, dec, frame=frame)

    # Return RA and Dec in degrees
    return c.ra.deg, c.dec.deg
