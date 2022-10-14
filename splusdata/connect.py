import requests
import json
import astropy
from astropy.io import fits
import io
from PIL import Image
from urllib.parse import quote
from xml.dom import minidom
from astropy.table import Table
import time
import ast
from getpass import getpass

from astropy.io.votable import from_table, writeto

class connect:
    """Class that logs in into splus.cloud and perform all types of download operation. 
    """    
    def __init__(self, username=None, password=None):
        """Class must be initialized with splus.cloud user and password.

        Args:
            username (str, optional): splus.cloud username
            password (str, optional): splus.cloud pasword
        """        

        if not username or not password:
            username = input("splus.cloud username: ")
            password = getpass("splus.cloud password: ")
        
        data = {'username':username, 'password':password}
        res = requests.post("https://splus.cloud/api/auth/login", data = data)
        usr = json.loads(res.content)
        self.token = usr['token']
        self.headers = {'Authorization': 'Token ' + self.token}
        
        res = requests.post("https://splus.cloud/api/auth/collab", headers = self.headers)
        collab = json.loads(res.content)
        
        if collab['collab'] == 'yes':
            self.collab = True
            print('You have access to internal data')
        else:
            self.collab = False
            pass
        
        self.lastres = ''
        
    
    def twelve_band_img(self, ra, dec, radius, noise=0.15, saturation=0.15, R="R,I,F861,Z", G="G,F515,F660", B="U,F378,F395,F410,F430", option=1):        
        """Function to get twelve band composed images. 

        Args:
            ra (float): RA coordinate in degrees. 
            dec (float): DEC coordinate in degrees.
            radius (int): Image size in pixels. Final size will be (radius X radius)
            noise (float, optional): Image noise value. Defaults to 0.15.
            saturation (float, optional): Image saturation value. Defaults to 0.15.    
            R (str, optional): Combinations of bands to compose red. Defaults to "R,I,F861,Z".
            G (str, optional): Combinations of bands to compose green. Defaults to "G,F515,F660".
            B (str, optional): Combinations of bands to compose blue. Defaults to "U,F378,F395,F410,F430".
            option (str, optional): in case a coordinate overlap over two fields, use option = 2 if you want the second field.
        Returns:
            PIL.Image: Image requested
        """             

  
        res = requests.get("https://splus.cloud/api/get_image/" + str(ra) + "/" + str(dec) + "/" + str(radius) + "/" + R + "-" + G + "-" + B + "/" + str(noise) + "/" + str(saturation) + "/" + str(option), headers=self.headers)
        source = json.loads(res.content)
        source['filename']
        res = requests.get("https://splus.cloud" + source['filename'], headers=self.headers)
        image = Image.open(io.BytesIO(res.content))
        
        self.lastcontent = image
        self.lastres = '12img'
        return image

    def get_img(self, ra, dec, radius, R="I", G="R", B="G", stretch=3, Q=8, option=1):
        """Function to get three band composed images made by lupton. 

        Args:
            ra (float): RA coordinate in degrees. 
            dec (float): DEC coordinate in degrees.
            radius (int): Image size in pixels. Final size will be (radius X radius)
            R (str, optional): Band to compose red. Defaults to "I".
            G (str, optional): Band to compose green. Defaults to "R".
            B (str, optional): Band to compose blue. Defaults to "G".
            stretch (int, optional): Stretch of image, same of make_lupton_rgb from astropy. Defaults to 3.
            Q (int, optional): Q of image, same of make_lupton_rgb from astropy. Defaults to 8.
            option (str, optional): in case a coordinate overlap over two fields, use option = 2 if you want the second field.
        Returns:
            PIL.Image: Image requested
        """        
        res = requests.get("https://splus.cloud/api/get_lupton_image/" + str(ra) + "/" + str(dec) + "/" + str(radius) + "/" + str(R) + "/" + str(G) + "/" + str(B) + "/" + str(stretch) + "/" + str(Q) + "/" + str(option), headers=self.headers)
        source = json.loads(res.content)
        source['filename']
        res = requests.get("https://splus.cloud" + source['filename'], headers=self.headers)
        image = Image.open(io.BytesIO(res.content))
        
        self.lastcontent = image
        self.lastres = 'get_cut'
        return image

    def get_band_img(self, ra, dec, radius, band='R', mode='linear', option=1):
        """Get image composed with one band.

        Args:
            ra (float): RA coordinate in degrees. 
            dec (float): DEC coordinate in degrees.
            radius (int): Image size in pixels. Final size will be (radius X radius)
            band (str, optional): Band to compose image. Defaults to 'R'.
            mode (str, optional): Mode. Defaults to 'linear'.
            option (str, optional): in case a coordinate overlap over two fields, use option = 2 if you want the second field.
        Returns:
            PIL.Image: Image requested
        """        
        res = requests.get("https://splus.cloud/api/get_band_image/" + str(ra) + "/" + str(dec) + "/" + str(radius) + "/" + str(band) + "/" + str(mode) + "/" + str(option), headers=self.headers)
        source = json.loads(res.content)
        source['filename']
        res = requests.get("https://splus.cloud" + source['filename'], headers=self.headers)
        image = Image.open(io.BytesIO(res.content))
        
        self.lastcontent = image
        self.lastres = 'get_band_image'
        return image

    
    def get_cut(self, ra, dec, radius, band, filepath=None, option=1):
        """Get fits cut.

        Args:
            ra (float): RA coordinate in degrees. 
            dec (float): DEC coordinate in degrees.
            radius (int): Image size in pixels. Final size will be (radius X radius)
            band (str): Band requested
            filepath (str, optional): file path to save result. Defaults to None.
            option (str, optional): in case a coordinate overlap over two fields, use option = 2 if you want the second field.
        Returns:
            astropy.io.fits: Fits file with image. 
        """        
        if band.upper() == 'ALL':
            if filepath == None:
                return 'You must save the file while getting "all" bands'
            
            elif filepath != None:  
                filepath = filepath + ".tar.gz"
                res = requests.get("https://splus.cloud/api/get_direct_cut/"  + str(ra) + "/" + str(dec) + "/" + str(radius) + "/" + "ALL", headers=self.headers)
                
                with open(filepath, 'wb') as f:
                    f.write(res.content)
                    f.close()
                    
                return 'File saved to ' + filepath
            
        res = requests.get("https://splus.cloud/api/get_direct_cut/"  + str(ra) + "/" + str(dec) + "/" + str(radius) + "/" + str(band) + "/" + str(option), headers=self.headers)
        hdu = fits.open(io.BytesIO(res.content))
        if filepath != None:
            hdu.writeto(filepath + ".fz")
        
        self.lastcontent = hdu
        self.lastres = 'cut'
        return hdu

    def get_cut_weight(self, ra, dec, radius, band, filepath=None, option=1):
        """Get weight image fits cut. 

        Args:
            ra (float): RA coordinate in degrees. 
            dec (float): DEC coordinate in degrees.
            radius (int): Image size in pixels. Final size will be (radius X radius)
            band (str): Band requested
            filepath (str, optional): file path to save result. Defaults to None.
            option (str, optional): in case a coordinate overlap over two fields, use option = 2 if you want the second field.
        Returns:
            astropy.io.fits: Fits file with image. 
        """        
        if band.upper() == 'ALL':
            if filepath == None:
                return 'You must save the file while getting "all" bands'
            
            elif filepath != None:  
                filepath = filepath + ".tar.gz"
                res = requests.get("https://splus.cloud/api/get_direct_cut_weight/"  + str(ra) + "/" + str(dec) + "/" + str(radius) + "/" + "ALL" + "/" + str(option), headers=self.headers)
                
                with open(filepath, 'wb') as f:
                    f.write(res.content)
                    f.close()
                    
                return 'File saved to ' + filepath
            
        res = requests.get("https://splus.cloud/api/get_direct_cut_weight/"  + str(ra) + "/" + str(dec) + "/" + str(radius) + "/" + str(band) + "/" + str(option), headers=self.headers)
        hdu = fits.open(io.BytesIO(res.content))
        if filepath != None:
            hdu.writeto(filepath + ".fz")
        
        self.lastcontent = hdu
        self.lastres = 'cut'
        return hdu
    
    def get_field(self, field, band):
        """Get whole 11k field fits.

        Args:
            field (str): field name. 
            band (str): Band.

        Returns:
            astropy.io.fits: Fits file with image. 
        """        
        res = requests.get("https://splus.cloud/api/get_direct_field/" + str(field) + "/" + str(band) , headers=self.headers)
        hdu = fits.open(io.BytesIO(res.content))
        
        self.lastres = 'field'
        self.lastcontent = hdu
        return hdu  

    def get_field_weight(self, field, band):
        """Get whole 11k weight field fits.

        Args:
            field (str): field name. 
            band (str): Band.

        Returns:
            astropy.io.fits: Fits file with image. 
        """        
        res = requests.get("https://splus.cloud/api/get_direct_field_weight/" + str(field) + "/" + str(band) , headers=self.headers)
        hdu = fits.open(io.BytesIO(res.content))
        
        self.lastres = 'field'
        self.lastcontent = hdu
        return hdu  

    def get_tap_tables(self):
        """Get info about available tables.
        """        

        print("Tables and columns available at https://splus.cloud/query/")
            
    def query(self, query, table_upload=None, publicdata=None):
        """Perform async queries on splus cloud TAP service. 

        Args:
            query (str): query itself.
            table_upload (pandas.DataFrame, optional): table to upload. Defaults to None.
            publicdata (bool, optional): If internal wants to access public data. Defaults to None.

        Returns:
            astropy.table.Table: result table.
        """        
        if self.collab:
            baselink = "https://splus.cloud/tap/tap/async/"
        else:
            baselink = "https://splus.cloud/public-TAP/tap/async/"


        if publicdata and self.collab:
            baselink = "https://splus.cloud/public-TAP/tap/async/"

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

                link = link.replace("http://192.168.10.23:8080", "https://splus.cloud").replace("http://10.180.0.209:8080", "https://splus.cloud").replace("http://10.180.0.207:8080", "https://splus.cloud").replace("http://10.180.0.219:8080", "https://splus.cloud")
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


    def checkcoords(self, ra, dec):
        """Check if coords are in footprint

        Args:
            ra (float): RA coordinate in degrees. 
            dec (float): DEC coordinate in degrees.
        Returns:
            dict: result.
        """        
        res = requests.get("https://splus.cloud/api/whichdr/" + str(ra) + "/" + str(dec) , headers=self.headers)
        res = res.content.decode("utf-8")
        
        res = ast.literal_eval(res)
        return res

    
    def get_last_result(self):
        """If you missed to save your last query or image into a variable, you may get it here.

        Returns:
            _type_: Last result, may be image or query. 
        """        
        return self.lastcontent
