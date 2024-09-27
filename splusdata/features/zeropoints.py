import pandas as pd

source_cat = "https://splus.cloud/files/documentation/iDR4/tabelas/iDR4_zero-points.csv"
zps = pd.read_csv(source_cat)

def get_zeropoint(conn, ra, dec, band):
    """
    Retrieve the zero point for a given sky position and band.

    Parameters
    ----------
    conn : object
        Connection object that has a method `checkcoords` to retrieve the field name based on coordinates.
    ra : float
        Right Ascension of the target position (in degrees).
    dec : float
        Declination of the target position (in degrees).
    band : str
        Photometric band for which to retrieve the zero point (e.g., 'g', 'r', 'i'). 
        If set to 'all', returns zero points for all bands.

    Returns
    -------
    float or pandas.DataFrame
        - If a specific band is provided, returns the zero point as a float.
        - If 'all' is provided as the band, returns a DataFrame containing zero points for all bands.

    Raises
    ------
    KeyError
        If the provided field or band is not found in the zero point table.
    
    Examples
    --------
    >>> conn = some_connection_object()
    >>> ra, dec = 150.0, 2.0
    >>> zp = get_zeropoint(conn, ra, dec, 'g')
    >>> print(zp)
    25.13

    >>> zp_all = get_zeropoint(conn, ra, dec, 'all')
    >>> print(zp_all)
          Field   ZP_u   ZP_g   ZP_r  ...
    1234_56789  25.13  24.98  25.02  ...
    """
    
    field =  list(conn.checkcoords(ra, dec).values())[0]
    
    zps["Field"] = zps["Field"].str.replace("-", "_")
    field = field.replace("-", "_")
    
    if band.lower() == "all":
        zp = zps[zps["Field"] == field]
    else:
        zp = zps[zps["Field"] == field]["ZP_" + band].values[0]
    
    return zp
    