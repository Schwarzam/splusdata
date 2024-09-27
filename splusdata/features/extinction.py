# Import packages and configure the folder to save the dust maps
from astropy.coordinates import SkyCoord
import pandas as pd
import numpy  as np

import os

try:
    from dustmaps.config import config
    import dustmaps.csfd
    import extinction
except:
    pass

class SplusExtinction:
    """
    A class to apply extinction correction to astronomical magnitudes based on the 
    Cardelli, Clayton, & Mathis (1989) law using CSFD dust maps.

    Parameters
    ----------
    data_dir : str, optional
        Directory to save the downloaded dust maps, by default "../data/outputs/dustmaps".
    bands : list of str, optional
        List of band names for which extinction correction will be applied, 
        by default ['u', 'J0378', 'J0395', 'J0410', 'J0430', 'g', 'J0515', 'r', 'J0660', 'i', 'J0861', 'z'].
    wavelengths : list of int, optional
        List of wavelengths (in Angstroms) corresponding to the bands, by default 
        [3536, 3770, 3940, 4094, 4292, 4751, 5133, 6258, 6614, 7690, 8611, 8831].

    Attributes
    ----------
    data_dir : str
        Directory where the dust maps are saved.
    bands : list of str
        Names of bands used in the extinction calculation.
    wavelengths : list of int
        Wavelengths corresponding to each band in Angstroms.
    extinction_columns : list of str
        Column names for storing extinction values corresponding to each band.
    extinction_map : dustmaps.csfd.CSFDQuery
        Extinction map object for querying dust extinction values.

    Methods
    -------
    prepare_map()
        Prepares the extinction map for querying by downloading and configuring the CSFD map.
    
    get_extinction(df)
        Calculates the extinction for given coordinates and adds extinction values to the DataFrame.
    
    apply(df, mag_cols)
        Applies extinction correction to the magnitude columns in the DataFrame.

    ```python
    import SplusExtinction
    
    df = pd.DataFrame({
        'ra': [0, 1, 2],
        'dec': [0, 1, 2],
        'r_auto': [20, 21, 22],
        'i_auto': [19, 20, 21]
        ...
        #12 bands of magnitudes
    })
    
    ext = SplusExtinction("dustmaps_dir/")
    ext.prepare_map()
    
    df = ext.get_extinction(df)    
    df = ext.apply(df, [band + "_auto" for band in ext.bands])
    ```
    """
    
    def __init__(
        self, 
        dustmap_dir = "../data/outputs/dustmaps",
        bands = ['u', 'J0378', 'J0395', 'J0410', 'J0430', 'g', 'J0515', 'r', 'J0660', 'i', 'J0861', 'z'],
        wavelengths = [3536, 3770, 3940, 4094, 4292, 4751, 5133, 6258, 6614, 7690, 8611, 8831]
    ):
        self.data_dir = dustmap_dir 
        self.bands = bands
        self.wavelengths = wavelengths
        self.extinction_columns = [f"ext_{band}" for band in self.bands]
        
        self.extinction_map = None
        
        if not extinction:
            raise ImportError("The 'extinction' package is required for this class.")
        if not dustmaps:
            raise ImportError("The 'dustmaps' package is required for this class.")
        
    def prepare_map(self):
        """Prepares the extinction map by downloading the CSFD map and configuring the file paths."""
        config['data_dir'] = self.data_dir # Folder to save the dust maps
        dustmaps.csfd.fetch() # Downloads the dust map if it is not already downloaded

        self.extinction_map = dustmaps.csfd.CSFDQuery(
            map_fname=os.path.join(self.data_dir, 'csfd/csfd_ebv.fits'), 
            mask_fname=os.path.join(self.data_dir, 'csfd/mask.fits')
        )
        
    def get_extinction(self, df, ra_col='ra', dec_col='dec'):
        """
        Calculates extinction values based on RA and DEC coordinates using the CCM89 Law.

        Parameters
        ----------
        df : pandas.DataFrame
            DataFrame containing the coordinates with columns 'ra' and 'dec'.

        Returns
        -------
        pandas.DataFrame
            DataFrame with added columns for extinction values in each band.
        """
        # Obtaining E(B-V) and Av in a given RA, DEC position
        input_file_coords = SkyCoord(df[ra_col], df[dec_col], frame='icrs', unit='deg')
        ebv = self.extinction_map(input_file_coords)
        av  = 3.1*ebv

        # Calculating the extinction on the S-PLUS bands using the Cardelli, Clayton & Mathis law.
        lambdas = np.array(self.wavelengths).astype(float)

        extinctions = []
        for i in range(len(av)):
            extinctions.append(extinction.ccm89(lambdas, av[i], 3.1))
        
        extinction_df = pd.DataFrame(extinctions, columns=self.extinction_columns)
        
        df = pd.concat([df, extinction_df], axis=1)
        
        return df
    
    def apply(self, df, mag_cols):
        """
        Applies extinction correction to the magnitude columns in the DataFrame.

        Parameters
        ----------
        df : pandas.DataFrame
            DataFrame containing magnitudes and extinction values.
        mag_cols : list of str
            List of magnitude column names in the DataFrame that correspond to the bands.

        Returns
        -------
        pandas.DataFrame
            DataFrame with new columns for extinction-corrected magnitudes (_extcorr cols).
        
        Raises
        ------
        ValueError
            If the number of columns in `mag_cols` and extinction columns do not match.
        """
        if len(mag_cols) != len(self.extinction_columns):
            raise ValueError("The number of columns in mag_cols and ext_cols must be the same.")
        
        # Correct the magnitudes for extinction
        for mag_col, ext_col in zip(mag_cols, self.extinction_columns):
            df[mag_col + "_extcorr"] = df[mag_col] - df[ext_col]
        
        return df