import adss
import getpass

from PIL import Image
from astropy.io import fits
import astropy.units as u
import io
import os

from splusdata.features.io import print_level
from splusdata.features.find_pointings import find_pointing

class SplusdataError(Exception):
    """Custom exception type for S-PLUS data errors raised by this helper module.

    Use this to catch and handle issues such as:
    - Missing collections or files on the server.
    - Invalid filter/field combinations.
    - Empty results (e.g., zero candidates for a filename pattern).
    """


def open_image(image_bytes):
    """Open an image from raw bytes and return a PIL Image.

    Parameters
    ----------
    image_bytes : bytes
        Raw image bytes (e.g., returned by ADSS endpoints).

    Returns
    -------
    PIL.Image.Image
        A Pillow image instance.

    Raises
    ------
    OSError
        If Pillow cannot identify or open the image.
    """
    from PIL import Image
    im = Image.open(io.BytesIO(image_bytes))
    return im


def save_image(image_bytes, filename):
    """Save image bytes to a file on disk.

    Parameters
    ----------
    image_bytes : bytes
        Raw image bytes (e.g., returned by ADSS endpoints).
    filename : str or pathlib.Path
        Output file path, including the desired extension.

    Returns
    -------
    None

    Raises
    ------
    OSError
        If the image cannot be opened or saved.
    """
    im = open_image(image_bytes)
    im.save(filename)
    

# field frame
class Core:
    """Convenience interface around `adss.ADSSClient` for S-PLUS images and queries.

    This wrapper streamlines common tasks:
    - Listing available image collections.
    - Fetching full field FITS frames or small cutouts (stamps).
    - Generating Lupton or Trilogy RGB composites.
    - Submitting SQL/ADQL queries (with optional table upload).
    - Retrieving and applying per-field zero points (DR6).

    Notes
    -----
    * Authentication: If `username`/`password` are not provided, the constructor
      will prompt interactively (stdin).
    * All methods pass through to a single `adss.ADSSClient` instance.
    """

    def __init__(self, username=None, password=None, SERVER_IP=f"https://splus.cloud", auto_renew=False, verbose=0):
        """Initialize a Core client.

        Parameters
        ----------
        username : str, optional
            S-PLUS account username. If None, asked interactively.
        password : str, optional
            S-PLUS account password. If None, prompted via getpass.
        SERVER_IP : str, optional
            Base URL of the S-PLUS service (default: "https://splus.cloud").
        auto_renew : bool, optional
            Placeholder for future token auto-renew behavior (unused here).
        verbose : int, optional
            Verbosity level. Defaults to 0.

        Attributes
        ----------
        client : adss.ADSSClient
            Underlying authenticated ADSS client.
        collections : list[dict]
            Cached list of collections after `_load_collections()`.

        Raises
        ------
        Exception
            Propagates any authentication/connection exceptions raised by ADSSClient.
        """
        if not username:
            username = input("splus.cloud username: ")
        if not password:    
            password = getpass.getpass("splus.cloud password: ")
            
        self.client = adss.ADSSClient(
            SERVER_IP,
            username=username,
            password=password,
        )
        self.collections = []
        self.verbose = verbose
        
    def _load_collections(self):
        """Fetch and cache image collections from the server.

        Returns
        -------
        None

        Side Effects
        ------------
        Populates `self.collections` with a list of collection dicts, as returned by
        `ADSSClient.get_collections()`.
        """
        collections = self.client.get_collections()
        self.collections = collections

    def check_available_images_releases(self):
        """List available image collection names (data releases).

        Returns
        -------
        list[str]
            Collection names, e.g., ["dr4", "dr5", "dr6", ...].
        """
        collections = self.client.get_collections()
        names = [col['name'] for col in collections]
        return names

    def get_collection_id_by_pattern(self, pattern):
        """Return the first collection whose `name` contains `pattern`.

        Parameters
        ----------
        pattern : str
            Substring to search for inside the collection name.

        Returns
        -------
        dict
            The first matching collection dictionary.

        Raises
        ------
        SplusdataError
            If no collection name contains the given pattern.
        """
        self._load_collections()
        for col in self.collections:
            if pattern in col['name']:
                return col
        raise SplusdataError("Collection not found")
    
    def get_file_metadata(self, field, band, pattern = "", data_release = "dr4"):
        """Resolve a single file metadata entry matching field/band/pattern.

        Parameters
        ----------
        field : str
            Field identifier (e.g., "SPLUS-n01s10"). If not found, tries swapping
            '-' and '_' once to be tolerant to naming variants.
        band : str
            Filter/band name (e.g., "R", "I", "F660", "U", ...).
        pattern : str, optional
            Key into the collection's `patterns` dict. Empty string selects the
            default pattern list for full science images. "weight" commonly selects
            weight maps.
        data_release : str, optional
            Collection pattern (substring) to select the DR (defaults to "dr4").

        Returns
        -------
        dict
            A file entry suitable for `download_file()`, containing at least
            `id`, `filename`, and `file_type`.

        Selection Logic
        ---------------
        1. Lists candidates via `list_files(collection_id, filter_str=field, filter_name=band)`.
        2. If none, swaps '-' and '_' in `field` and retries once.
        3. Reads the collection's `patterns[pattern]`, splits by commas, and filters:
           - Tokens starting with '!' mean "exclude those containing token".
           - Otherwise, "include if contains token".
        4. If multiple remain, prefer those with `file_type == "fz"`.

        Raises
        ------
        SplusdataError
            If no candidate files are found for the given (field, band).
        KeyError
            If `pattern` is not a key in the collection's `patterns` dict.
        """
        collection = self.get_collection_id_by_pattern(data_release)
        collection_id = collection['id']
        
        candidates = self.client.list_files(collection_id, filter_str=field, filter_name=band)
        
        if len(candidates) == 0 and ("-" in field or "_" in field):
            field = field.replace("-", "_") if "-" in field else field.replace("_", "-")
            candidates = self.client.list_files(collection_id, filter_str=field, filter_name=band)
        if len(candidates) == 0:
            raise SplusdataError(f"Field {field} not found in band {band}")
        
        patterns = collection['patterns']

        final_candidate = None
        f_candidates = []
        
        pattern = patterns[pattern]
        
        pattern = pattern.split(",")
        for c in candidates:
            for p in pattern:
                if p.startswith("!"):
                    if p not in c['filename']:
                        f_candidates.append(c)
                else:
                    if p in c['filename']:
                        f_candidates.append(c)

        if len(f_candidates) == 0:
            final_candidate = candidates[0]
        elif len(f_candidates) == 1:
            final_candidate = f_candidates[0]
        else:
            fz_candidates = [c for c in f_candidates if c['file_type'] == "fz"]
            final_candidate = fz_candidates[0] if fz_candidates else f_candidates

        return final_candidate

    def field_frame(self, field, band, weight=False, outfile=None, data_release="dr4", timeout = 60):
        """Download and open a full field FITS image.

        Parameters
        ----------
        field : str
            Field identifier, e.g., "SPLUS-n01s10".
        band : str
            Filter name, e.g., "R", "I", "F660", "U".
        weight : bool, optional
            If True, selects the "weight" pattern (commonly a weight map).
        outfile : str or pathlib.Path, optional
            If provided, ADSS will also write the downloaded file to this path.
        data_release : str, optional
            Target data release (pattern matched in collection name). Default "dr4".

        Returns
        -------
        astropy.io.fits.HDUList
            Opened FITS file as an HDUList.

        Raises
        ------
        SplusdataError
            If the file cannot be resolved.
        """
        if weight:
            pattern = "weight"
        else:
            pattern = ""

        final_candidate = self.get_file_metadata(field, band, pattern, data_release)
        image_bytes = self.client.download_file(
            final_candidate['id'],
            output_path=outfile,
            timeout=timeout
        )
        
        return fits.open(io.BytesIO(image_bytes))
                                   
    def stamp(self, ra, dec, size, band, weight=False, field_name=None, size_unit="pixels", outfile=None, data_release="dr4", timeout = 60):
        """Create and open a FITS stamp (cutout) by coordinates or by object name.

        Parameters
        ----------
        ra : float
            Right ascension in degrees.
        dec : float
            Declination in degrees.
        size : int or float
            Stamp size in `size_unit`.
        band : str
            Filter name (e.g., "R", "I", "F660").
        weight : bool, optional
            If True, selects weight images (pattern "weight").
        field_name : str, optional
            If provided, creates a stamp using object/field name context instead
            of pure coordinates (server may use FIELD metadata).
        size_unit : {"pixels", "arcsec"}, optional
            Unit for the size argument. Default "pixels".
        outfile : str or pathlib.Path, optional
            If provided, ADSS may also write the cutout to disk.
        data_release : str, optional
            Collection selector (substring). Default "dr4".

        Returns
        -------
        astropy.io.fits.HDUList
            Opened FITS cutout.

        Raises
        ------
        SplusdataError
            If the collection cannot be resolved.
        """
        collection = self.get_collection_id_by_pattern(data_release)
        collection_id = collection['id']
        
        if weight:
            weight = "weight"
        if not field_name:
            stamp_bytes = self.client.create_stamp_by_coordinates(
                collection_id=collection_id,
                filter=band,
                ra=ra,
                dec=dec,
                size=size,
                size_unit=size_unit,
                pattern=weight if weight else "",
                output_path=outfile,
                timeout=timeout
            )
        else:
            stamp_bytes = self.client.stamp_images.create_stamp_by_object(
                collection_id=collection_id,
                object_name=field_name,
                filter_name=band,
                ra=ra,
                dec=dec,
                size=size,
                size_unit=size_unit,
                pattern=weight if weight else "",
                output_path=outfile,
                timeout=timeout
            )
            
        return fits.open(io.BytesIO(stamp_bytes))

    def lupton_rgb(self, ra, dec, size, R="I", G="R", B="G", Q=8, stretch=3, field_name=None, size_unit="pixels", outfile=None, data_release="dr4"):
        """Create a Lupton RGB composite and return a PIL image.

        Parameters
        ----------
        ra, dec : float
            Coordinates in degrees.
        size : int or float
            Output image size in `size_unit`.
        R, G, B : str, optional
            Filter names for the RGB channels (defaults: I/R/G).
        Q : float, optional
            Lupton Q parameter (contrast). Default 8.
        stretch : float, optional
            Lupton stretch parameter. Default 3.
        field_name : str, optional
            If provided, generate by object/field context.
        size_unit : {"pixels", "arcsec"}, optional
            Unit for `size`. Default "pixels".
        outfile : str or pathlib.Path, optional
            If provided, ADSS may also write PNG/JPEG to disk.
        data_release : str, optional
            Collection selector (substring). Default "dr4".

        Returns
        -------
        PIL.Image.Image
            Composite RGB image.
        """
        collection = self.get_collection_id_by_pattern(data_release)
        collection_id = collection['id']

        if not field_name:
            stamp_bytes = self.client.create_rgb_image_by_coordinates(
                collection_id=collection_id,
                ra=ra,
                dec=dec,
                size=size,
                r_filter=R,
                g_filter=G,
                b_filter=B,
                Q=Q,
                size_unit=size_unit,
                stretch=stretch,
                output_path=outfile
            )
        else:
            stamp_bytes = self.client.lupton_images.create_rgb_by_object(
                collection_id=collection_id,
                object_name=field_name,
                ra=ra,
                dec=dec,
                size=size,
                r_filter=R,
                g_filter=G,
                b_filter=B,
                Q=Q,
                size_unit=size_unit,
                stretch=stretch,
                output_path=outfile
            )

        return Image.open(io.BytesIO(stamp_bytes))

    def trilogy_image(self, ra, dec, size, R=["R", "I", "F861", "Z"], G=["G", "F515", "F660"], B=["U", "F378", "F395", "F410", "F430"], noiselum=0.15, satpercent=0.15, colorsatfac=2, size_unit="pixels", field_name=None, outfile=None, data_release="dr4"):
        """Create a Trilogy RGB composite (multi-filter blend) and return a PIL image.

        Parameters
        ----------
        ra, dec : float
            Coordinates in degrees.
        size : int or float
            Output size in `size_unit`.
        R, G, B : list[str], optional
            Lists of filters contributing to each RGB channel.
        noiselum : float, optional
            Controls noise luminance suppression.
        satpercent : float, optional
            Percentile value for saturation clipping.
        colorsatfac : float, optional
            Factor for color saturation.
        size_unit : {"pixels", "arcsec"}, optional
            Size unit. Default "pixels".
        field_name : str, optional
            If provided, generate by object/field context.
        outfile : str or pathlib.Path, optional
            If provided, ADSS may also write the composite to disk.
        data_release : str, optional
            Collection selector (substring). Default "dr4".

        Returns
        -------
        PIL.Image.Image
            Composite RGB image (Trilogy method).
        """
        collection = self.get_collection_id_by_pattern(data_release)
        collection_id = collection['id']

        if not field_name:
            stamp_bytes = self.client.trilogy_images.create_trilogy_rgb_by_coordinates(
                collection_id=collection_id,
                ra=ra,
                dec=dec,
                size=size,
                r_filters=R,
                g_filters=G,
                b_filters=B,
                size_unit=size_unit,
                noiselum=noiselum,
                satpercent=satpercent,
                colorsatfac=colorsatfac,
                output_path=outfile
            )
        else:
            stamp_bytes = self.client.trilogy_images.create_trilogy_rgb_by_object(
                collection_id=collection_id,
                object_name=field_name,
                ra=ra,
                dec=dec,
                size=size,
                r_filters=R,
                g_filters=G,
                b_filters=B,
                noiselum=noiselum,
                size_unit=size_unit,
                satpercent=satpercent,
                colorsatfac=colorsatfac,
                output_path=outfile
            )

        return Image.open(io.BytesIO(stamp_bytes))
    
    def query(self, query, table_upload=None, table_name=None, verbose = False, timeout = 320):
        """Execute a server-side query; optionally upload a small table first.

        Parameters
        ----------
        query : str
            SQL/ADQL text to execute on the server.
        table_upload : pandas.DataFrame or astropy.table.Table, optional
            In-memory table to upload as a temporary (CSV) file for the query.
        table_name : str, optional
            Name to assign to the uploaded table on the server.
        timeout : int, optional
            Timeout in seconds for the query download time (default 320s). (the execution time is still limited by the server config, usually 2h)

        Returns
        -------
        Any
            The `response.data` returned by `ADSSClient.query_and_wait`. Depends
            on the query and server configuration (often JSON-like dict/list).

        Raises
        ------
        ValueError
            If `table_upload` is provided but is neither a DataFrame nor an
            Astropy Table.
        Exception
            Propagates server or network errors from the ADSS client.
        """
        table_upload_bytes = None
        if table_upload is not None and table_name is not None:
            import pandas as pd
            from astropy.table import Table
            
            table_upload_bytes = None
            if isinstance(table_upload, pd.DataFrame):
                table_upload_bytes = table_upload.to_csv(index=False).encode()
            elif isinstance(table_upload, Table):
                table_upload_bytes = table_upload.to_pandas().to_csv(index=False).encode()
            else:
                raise ValueError("table_upload must be a pandas DataFrame or an astropy Table")

        response = self.client.query_and_wait(
            query_text=query,
            table_name=table_name,
            file=table_upload_bytes, 
            verbose=verbose,
            timeout = 320
        )
        return response.data

    def get_zp_file(self, field, band, data_release = "dr6"):
        """Download and parse the per-field zero-point model (DR6).

        Parameters
        ----------
        field : str
            Field name used in the DR6 collection.
        band : str
            Filter/band name.
        data_release : str, optional
            Collection selector, defaults to "dr6" (where zp models are expected).

        Returns
        -------
        dict
            Parsed JSON zero-point model.

        Raises
        ------
        SplusdataError
            If no zero-point model file is found for the field/band.
        JSONDecodeError
            If the downloaded bytes are not valid JSON.
        """
        import json
        collection = self.get_collection_id_by_pattern(data_release)
        collection_id = collection['id']
        
        files = self.client.list_files(
            collection_id, 
            filter_str=f"{field}_{band}_zp", 
        )
        if len(files) == 0:
            raise SplusdataError(f"No zp model found for field {field} in band {band} in {data_release}")
        file = files[0]
        
        print_level(f"Downloading zp_model {file['filename']}", 1, self.verbose)
        json_bytes = self.client.download_file(file["id"], timeout = 20)
        json_data = json.loads(json_bytes)
        return json_data
    
    def get_zp(self, field, band, ra, dec):
        """Evaluate the local zero point at a sky position using the field model.

        Parameters
        ----------
        field : str
            Field identifier for the zero-point model to use.
        band : str
            Filter name matching the zp model.
        ra, dec : float
            Coordinates (deg) where the zp should be evaluated.

        Returns
        -------
        float
            Zero point value at (ra, dec), in magnitudes.

        Raises
        ------
        SplusdataError
            If the model file cannot be found/downloaded.
        Exception
            Any error propagated from `zp_at_coord` evaluation.
        """
        model = self.get_zp_file(field, band)
        
        from splusdata.features.zeropoints.zp_map import zp_at_coord
        return zp_at_coord(model, ra, dec)
    
    def calibrated_stamp(self, ra, dec, size, band, weight=False, field_name=None, size_unit="pixels", outfile=None, data_release="dr6"):
        """Create a stamp and return a photometrically calibrated PrimaryHDU.

        This computes a cutout via `stamp(...)`, then loads the appropriate DR6+
        per-field zero-point model and applies spatially varying calibration.

        Parameters
        ----------
        ra, dec : float
            Coordinates in degrees.
        size : int or float
            Cutout size in `size_unit`.
        band : str
            Filter name.
        weight : bool, optional
            If True, returns weight cutouts (note: calibration typically applies
            to science images, not weights).
        field_name : str, optional
            Use object/field context for the stamp creation.
        size_unit : {"pixels", "arcsec"}, optional
            Size unit (default "pixels").
        outfile : str or pathlib.Path, optional
            If provided, writes the calibrated HDU to disk (FITS).
        data_release : str, optional
            DR to use for both the stamp and the zp model (default "dr6").

        Returns
        -------
        astropy.io.fits.PrimaryHDU
            The calibrated science HDU (new object unless `in_place=True` were used).

        Raises
        ------
        SplusdataError
            If the zp model cannot be found.
        KeyError
            If expected header keys (e.g., FIELD, FILTER) are missing in the stamp.
        Exception
            Propagates any calibration errors from `calibrate_hdu_with_zpmodel`.
        """
        stamp = self.stamp(ra, dec, size, band, weight=weight, field_name=field_name, size_unit=size_unit, data_release=data_release)
        
        if not weight:           
            from splusdata.features.zeropoints.zp_image import calibrate_hdu_with_zpmodel
            zp_model = self.get_zp_file(stamp[1].header["FIELD"], stamp[1].header["FILTER"], data_release=data_release)
            
            calibrated_hdu, factor_map = calibrate_hdu_with_zpmodel(
                stamp[1], zp_model, in_place=False, return_factor=True
            )

            stamp[1] = calibrated_hdu
            stamp.append(fits.ImageHDU(factor_map, name="ZP_FACTOR"))
        
        if outfile:
            stamp.writeto(outfile, overwrite=True)
        return stamp
    
    def get_zps_field(self, ras, decs, field, band, data_release="dr6"):
        """
        Compute zero-point (ZP) values for a set of coordinates in a specific field and band.

        Parameters
        ----------
        ras : array-like
            Right ascension values in degrees.
        decs : array-like
            Declination values in degrees. Must have the same shape as `ras`.
        field : str
            Name of the S-PLUS field to retrieve the ZP model for.
        band : str
            S-PLUS band name (e.g., 'r', 'g', 'J0660') to get the corresponding ZP model.
        data_release : str, optional
            Data release identifier. Default is "dr6".

        Returns
        -------
        np.ndarray
            Array of zero-point values (in magnitudes) for each input (RA, Dec) pair.
        """
        zp_model = self.get_zp_file(field, band, data_release=data_release)
        
        from splusdata.features.zeropoints.zp_image import compute_zp_for_coords_array
        return compute_zp_for_coords_array(ras, decs, zp_model)
    
    def check_coords(self, ra, dec, radius=1 * u.degree):
        """Check which DR contains a pointing within `radius` of (ra, dec).

        Parameters
        ----------
        ra, dec : float
            Coordinates in degrees.
        radius : Astropy unit, optional
            Search radius in degrees (default 1 deg).

        Returns
        -------
        dict or None
            If found, a dict with keys 'dr', 'field', and 'distance' (an astropy
            Quantity in degrees). If not found in any DR, returns None.

        Raises
        ------
        Exception
            Propagates any errors from `find_pointing`.
        """
        return find_pointing(ra, dec, radius=radius)
    
    def download_collection(self, collection, outfolder="."):
        if isinstance(collection, str):
            collection = self.get_collection_id_by_pattern(collection)
        elif isinstance(collection, int):
            collection = {'id': collection}

        if not os.path.exists(outfolder):
            os.makedirs(outfolder)
            
        not_over = True
        skip = 0
        while not_over:
            files = self.client.list_files(
                collection_id=collection['id'],
                skip=skip,
                limit=200
            )
            if len(files) == 0:
                not_over = False
            for f in files:
                print(f"Downloading {f['filename']}")
                try:
                    if not os.path.exists(os.path.join(outfolder, f['filename'])):
                        self.client.download_file(file_id=f['id'], output_path=os.path.join(outfolder, f['filename']), timeout=180)
                    else:
                        print(f"File {f['filename']} already exists, skipping download.")
                except Exception as e:
                    # delete partial file if exists
                    if os.path.exists(os.path.join(outfolder, f['filename'])):
                        os.remove(os.path.join(outfolder, f['filename']))
                    print(f"Error downloading {f['filename']}: {e}")