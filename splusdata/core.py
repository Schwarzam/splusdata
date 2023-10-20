import requests
import time
import json
import io 

from getpass import getpass

# TODO: DEPRECATE and remove imports on old API

## Error handling
class AuthenticationError(Exception):
    pass

class SplusError(Exception):
    pass


# ----------------------------
""" FIXME: Put in another folder later"""

def open_image(image_bytes):
    from PIL import Image
    im = Image.open(io.BytesIO(image_bytes))
    return im

def save_image(image_bytes, filename):
    im = open_image(image_bytes)
    im.save(filename)
    
def open_fits(fits_bytes):
    from astropy.io import fits
    return fits.open(io.BytesIO(fits_bytes))

def save_fits(fits, filename):
    from astropy.io.fits import CompImageHDU
    sufix = ""
    for ext in fits:
        # check if extension is compressed
        if isinstance(ext, CompImageHDU):
            if not ".fz" in filename:
                sufix = ".fz"
    
    fits.writeto(filename + sufix, overwrite=True)
    
# ----------------------------


class Core:
    """
    A class for interacting with the S-PLUS API.

    Parameters
    ----------
    username : str, optional
        The username for the splus.cloud account. If not provided, the user will be prompted to enter it.
    password : str, optional
        The password for the splus.cloud account. If not provided, the user will be prompted to enter it.

    Attributes
    ----------
    SERVER_URL : str
        The base URL for the S-PLUS API server.
    session : requests.Session
        The session object used for making requests to the S-PLUS API.
    token : str
        The authentication token for the S-PLUS API.
    headers : dict
        The headers to be included in requests to the S-PLUS API.
    collab : bool
        Whether the user has access to collaboration data.

    Methods
    -------
    authenticate(username=None, password=None)
        Authenticates the user with the S-PLUS API.
    _make_request(method, url, data=None, json_=None, params=None)
        Makes a request to the S-PLUS API.
    field_frame(field, band, filename=None, _data_release=None)
        Downloads a FITS file for a given field and band.
    field_info(field)
        Gets information about a given field.
    info_mar(data)
        Gets information about a given data file.
    fetch_mar_file(file, filename=None)
        Downloads a data file.
    """

    def __init__(self, username=None, password=None, SERVER_IP = f"https://splus.cloud"):
        """
        Initializes a new instance of the Core class.

        Parameters
        ----------
        username : str, optional
            The username for the splus.cloud account. If not provided, the user will be prompted to enter it.
        password : str, optional
            The password for the splus.cloud account. If not provided, the user will be prompted to enter it.
        """
        self.SERVER_IP = SERVER_IP
        self.SERVER_URL = f"{self.SERVER_IP}/api"
        
        self.session = requests.Session()
        self.authenticate(username, password)

    def authenticate(self, username=None, password=None):
        """
        Authenticates the user with the S-PLUS API.

        Parameters
        ----------
        username : str, optional
            The username for the splus.cloud account. If not provided, the user will be prompted to enter it.
        password : str, optional
            The password for the splus.cloud account. If not provided, the user will be prompted to enter it.

        Raises
        ------
        AuthenticationError
            If authentication fails.
        """
        if not username:
            username = input("splus.cloud username: ")
        if not password:    
            password = getpass("splus.cloud password: ")

        data = {'username': username, 'password': password}
        response = self.session.post(f"{self.SERVER_URL}/auth/login", data=data)

        if response.status_code != 200:
            raise AuthenticationError("Authentication failed")

        user_data = json.loads(response.content)
        self.token = user_data['token']
        self.headers = {'Authorization': 'Token ' + self.token}

        response = self.session.post(f"{self.SERVER_URL}/auth/collab", headers=self.headers)
        collab = json.loads(response.content)

        self.collab = collab.get('collab') == 'yes'
        
    def _make_request(self, method, url, data=None, json_=None, params=None):
        """
        Makes a request to the S-PLUS API.

        Parameters
        ----------
        method : str
            The HTTP method to use for the request.
        url : str
            The URL to make the request to.
        data : dict, optional
            The data to include in the request body.
        json_ : dict, optional
            The JSON data to include in the request body.
        params : dict, optional
            The query parameters to include in the request.

        Returns
        -------
        requests.Response
            The response from the S-PLUS API.

        Raises
        ------
        SplusError
            If the response contains an error.
        """
        response = self.session.request(method, url, data=data, json=json_, params=params, headers=self.headers)
        
        resjson = None
        try:
            resjson = response.json()
        except:
            pass
        
        if resjson:
            if 'error' in resjson:
                raise SplusError(resjson['error'])
            else:
                response.raise_for_status()  # Raise an exception for HTTP errors
        else:
            response.raise_for_status()  # Raise an exception for HTTP errors
        
        return response
    
    def field_frame(self, field, band, weight = False, filename=None, _data_release=None):
        """
        Downloads a FITS file for a given field and band.

        Parameters
        ----------
        field : str
            The name of the field to download the FITS file for.
        band : str
            The name of the band to download the FITS file for.
        filename : str, optional
            The name of the file to save the FITS data to.
        _data_release : str, optional
            The data release to download the FITS file for.

        Returns
        -------
        astropy.io.fits.HDUList
            The FITS data for the requested field and band.
        """
        data = {
            "fieldname": field,
            "band": band,
            "weight": weight,
            "dr": _data_release
        }
        res = self._make_request('POST', f"{self.SERVER_URL}/download_frame", json_=data)
        
        frame = open_fits(res.content)
        if filename:
            save_fits(frame, filename=filename)
        return frame
    
    
    # ----------------------------
    # TODO: Decide if its going to stay in this class
    def field_info(self, field):
        """
        Gets information about a given field.

        Parameters
        ----------
        field : str
            The name of the field to get information about.

        Returns
        -------
        dict
            The information about the requested field.
        """
        # 'api/get_field_info_mar/<str:fieldname>'
        res = self._make_request('POST', f"{self.SERVER_URL}/get_field_info_mar/{field + 'd'}")
        return res.json()


    ### TODO: INTERNAL PERMITED FUNCTIONS ###
    def info_mar(self, data):
        """
        Gets information about a given data file.

        Parameters
        ----------
        data : dict
            The data to use for the request.

        Returns
        -------
        dict
            The information about the requested data file.

        Raises
        ------
        SplusError
            If the response contains an error.
        """
        assert isinstance(data, dict), "data must be a dict"
        
        endpoints = ["finaltiles", "individualfile", "superflat", "biasblock", "flatblock"]
        if data['endpoint'] not in endpoints:
            raise SplusError("Endpoint not in {endpoints}}")
            
        res = self._make_request('POST', f"{self.SERVER_URL}/get_info_mar", json_=data)
        return res.json()

    def fetch_mar_file(self, file, filename=None):
        """
        Downloads a data file.

        Parameters
        ----------
        file : str
            The name of the file to download.
        filename : str, optional
            The name of the file to save the downloaded data to.

        Returns
        -------
        bytes or astropy.io.fits.HDUList
            The downloaded data.

        Raises
        ------
        SplusError
            If the downloaded file is not recognized or does not exist.
        """
        # get_file_mar
        
        res = self._make_request('POST', f"{self.SERVER_URL}/get_file_mar", json_={"filename": file})
        
        if filename:
            print("Saving file to", filename)
            with open(filename, 'wb') as f:
                f.write(res.content)
        
        try:
            if '.png' in file:
                return open_image(res.content)
            elif '.fits' in file:
                return open_fits(res.content)
        except:
            raise SplusError("File not recognized, may be corrupted or not exist")
        
        return res.content
    
    def stamp(self, ra, dec, size, band, weight = False, option = 1, filename=None, _data_release=None):
        """
        Downloads a FITS file for a given field and band.

        Parameters
        ----------
        ra : float
            The RA of the center of the stamp.
        dec : float
            The DEC of the center of the stamp.
        size : float
            The size of the stamp in arcseconds.
        band : str
            The name of the band to download the FITS file for.
        weight : bool, optional
            Whether to download the weight map for the stamp.
        option : int, optional
            The option to use for the match 1 -> first match, 2 -> second match.
        filename : str, optional
            The name of the file to save the FITS data to.
        _data_release : str, optional
            The data release to download the FITS file for.

        Returns
        -------
        astropy.io.fits.HDUList
            The FITS data for the requested field and band.
        """
        data = {
            "ra": ra,
            "dec": dec,
            "band": band,
            "option": str(option),
            "size": size,
            "weight": weight,
            "dr": _data_release
        }
        res = self._make_request('POST', f"{self.SERVER_URL}/download_stamp", json_=data)
        
        frame = open_fits(res.content)
        if filename:
            save_fits(frame, filename=filename)
        return frame
    
    def lupton_rgb(self, ra, dec, size, R="I", G="R", B="G", Q=8, stretch=3, option=1, filename=None, _data_release=None):
        """
        Downloads a lupton image.

        Parameters
        ----------
        ra : float
            The RA of the center of the stamp.
        dec : float
            The DEC of the center of the stamp.
        size : float
            The size of the stamp in arcseconds.
        R : str
            The name of the band to use for the red channel.
        G : str
            The name of the band to use for the green channel.
        B : str
            The name of the band to use for the blue channel.
        Q : int, optional
            Q of image, same of make_lupton_rgb from astropy. Defaults to 8.
        stretch : int, optional
            Stretch of image, same of make_lupton_rgb from astropy. Defaults to 3.
        option : int, optional
            The option to use for the match 1 -> first match, 2 -> second match.
        filename : str, optional
            The name of the file to save the FITS data to.
        _data_release : str, optional
            The data release to download the FITS file for.

        Returns
        -------
        astropy.io.fits.HDUList
            The FITS data for the requested field and band.
        """
        data = {
            "ra": ra,
            "dec": dec,
            "size": size,
            "R": R,
            "G": G,
            "B": B,
            "Q": Q,
            "stretch": stretch,
            "option": str(option),
            "dr": _data_release
        }
        res = self._make_request('POST', f"{self.SERVER_URL}/lupton_image", json_=data)
        
        
        frame = open_image(res.content)
        if filename:
            save_image(res.content, filename=filename)
        return frame
    
    def trilogy_image(self, ra, dec, size, R="R,I,F861,Z", G="G,F515,F660", B="U,F378,F395,F410,F430", noiselum=0.15, satpercent=0.15, colorsatfac=2, option=1, filename=None, _data_release=None):
        """
        Downloads a trilogy image.

        Parameters
        ----------
        ra : float
            The RA of the center of the stamp.
        dec : float
            The DEC of the center of the stamp.
        size : float
            The size of the stamp in arcseconds.
        R : str
            Combinations of bands to use for the red channel.
        G : str
            Combinations of bands to use for the green channel.
        B : str
            Combinations of bands to use for the blue channel.
        noiselum : float, optional
            The noise luminosity. Defaults to 0.15.
        satpercent : float, optional
            The saturation percentage. Defaults to 0.15.
        colorsatfac : int, optional
            The saturation factor. Defaults to 2.
        option : int, optional
            The option to use for the match 1 -> first match, 2 -> second match.
        filename : str, optional
            The name of the file to save the FITS data to.
        _data_release : str, optional
            The data release to download the FITS file for.

        Returns
        -------
        astropy.io.fits.HDUList
            The FITS data for the requested field and band.
        """
        data = {
            "ra": ra,
            "dec": dec,
            "size": size,
            "reqOrder": f"{R}-{G}-{B}",
            "noiselum": noiselum,
            "satpercent": satpercent,
            "colorsatfac": colorsatfac,
            "option": str(option),
            "dr": _data_release
        }
        res = self._make_request('POST', f"{self.SERVER_URL}/trilogy_image", json_=data)
        
        frame = open_image(res.content)
        if filename:
            save_image(res.content, filename=filename)
        return frame
    
    
    ## query method (same from old API)
    def query(self, query, table_upload=None, publicdata=None):
        from astropy.io.votable import from_table, writeto
        from xml.dom import minidom
        from astropy.table import Table
        
        """Perform async queries on splus cloud TAP service. 

        Args:
            query (str): query itself.
            table_upload (pandas.DataFrame, optional): table to upload. Defaults to None.
            publicdata (bool, optional): If internal wants to access public data. Defaults to None.

        Returns:
            astropy.table.Table: result table.
        """        
        if self.collab:
            baselink = f"{self.SERVER_IP}/tap/tap/async/"
        else:
            baselink = f"{self.SERVER_IP}/public-TAP/tap/async/"


        if publicdata and self.collab:
            baselink = f"{self.SERVER_IP}/public-TAP/tap/async/"

        data = {
            "request": 'doQuery',
            "version": '1.0',
            "lang": 'ADQL',
            "phase": 'run',
            "query": query,
            "format": 'fits'
        }
        
        if str(type(table_upload)) != "<class 'NoneType'>":
            if 'astropy.table' in str(type(table_upload)):
                if len(table_upload) > 6000:
                    print('Cutting to the first 6000 objects!')
                    table_upload = table_upload[0:6000]
                    table_upload = from_table(table_upload)

                    IObytes = io.BytesIO()
                    writeto(table_upload, IObytes)

                    IObytes.seek(0)
                else:
                    table_upload = from_table(table_upload)

                    IObytes = io.BytesIO()
                    writeto(table_upload, IObytes)

                    IObytes.seek(0)

            elif 'astropy.io.votable' in str(type(table_upload)):
                if table_upload.get_first_table().nrows > 6000:
                    return 'votable bigger than 6000'
                else:
                    IObytes = io.BytesIO()
                    writeto(table_upload, IObytes)
                    IObytes.seek(0)

            elif 'DataFrame' in str(type(table_upload)):
                if len(table_upload) > 6000:
                    print('Cutting to the first 6000 objects!')
                    table_upload = table_upload[0:6000]
                    table_upload = Table.from_pandas(table_upload)
                    table_upload = from_table(table_upload)
                    IObytes = io.BytesIO()
                    writeto(table_upload, IObytes)
                    IObytes.seek(0)
                else:
                    table_upload = Table.from_pandas(table_upload)
                    table_upload = from_table(table_upload)
                    IObytes = io.BytesIO()
                    writeto(table_upload, IObytes)
                    IObytes.seek(0)
                    

            else:
                return 'Table type not supported'

            data['upload'] = 'upload,param:uplTable'
            res = requests.post(baselink , data = data, headers=self.headers, files={'uplTable': IObytes.read()})

        if not table_upload:
            res = requests.post(baselink , data = data, headers=self.headers)

        xmldoc = minidom.parse(io.BytesIO(res.content))

        try:
            item = xmldoc.getElementsByTagName('phase')[0]
            process = item.firstChild.data

            item = xmldoc.getElementsByTagName('jobId')[0]
            jobID = item.firstChild.data

            while process == 'EXECUTING':
                res = requests.get(baselink + jobID, headers=self.headers)
                xmldoc = minidom.parse(io.BytesIO(res.content))

                item = xmldoc.getElementsByTagName('phase')[0]
                process = item.firstChild.data
                time.sleep(5)

            if process == 'COMPLETED':
                item = xmldoc.getElementsByTagName('result')[0]
                link = item.attributes['xlink:href'].value

                link = link.replace("http://192.168.10.23:8080", f"{self.SERVER_IP}").replace("http://10.180.0.209:8080", f"{self.SERVER_IP}").replace("http://10.180.0.207:8080", f"{self.SERVER_IP}").replace("http://10.180.0.219:8080", f"{self.SERVER_IP}")
                res = requests.get(link, headers=self.headers)
                
                self.lastres = 'query'
                self.lastcontent = Table.read(io.BytesIO(res.content))
                print('finished')
                
                return self.lastcontent

            if process == 'ERROR':
                item = xmldoc.getElementsByTagName('message')[0]
                message = item.firstChild.data

                print("Error: ", message)

        except:
            item = xmldoc.getElementsByTagName('INFO')
            print(item[0].attributes['value'].value, ": ", item[0].firstChild.data)

if __name__ == "__main__":
    pass

    ## TESTS
    #core = Core()
    #core.field_frame('STRIPE82-0002', "R")
    
    #core.field_info('STRIPE82-0002')
    
    # core.info_mar(
    #     {
    #         "endpoint": "biasblock",
    #         "startDate": "2018-01-01",
    #         "endDate": "2018-02-01"
    #     }
    # )
    
    #core.fetch_mar_file("PROCESSED/G/2018-09-15/proc_STRIPE82-20180915-032415.png", filename="/Users/gustavo/Downloads/te.png")
    
    