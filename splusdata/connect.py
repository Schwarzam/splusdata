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

from astropy.io.votable import from_table, writeto

class connect:
    def __init__(self, username, password):
        
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
        
    
    def twelve_band_img(self, ra, dec, radius, noise=0.15, saturation=0.15):
        res = requests.get("https://splus.cloud/api/get_image/" + str(ra) + "/" + str(dec) + "/" + str(radius) + "/" + str("R,I,F861,Z-G,F515,F660-U,F378,F395,F410,F430") + "/" + str(noise) + "/" + str(saturation), headers=self.headers)
        source = json.loads(res.content)
        source['filename']
        res = requests.get("https://splus.cloud" + source['filename'], headers=self.headers)
        image = Image.open(io.BytesIO(res.content))
        
        self.lastcontent = image
        self.lastres = '12img'
        return image

    def get_img(self, ra, dec, radius, R="I", G="R", B="G", stretch=3, Q=8):
        res = requests.get("https://splus.cloud/api/get_lupton_image/" + str(ra) + "/" + str(dec) + "/" + str(radius) + "/" + str(R) + "/" + str(G) + "/" + str(B) + "/" + str(stretch) + "/" + str(Q), headers=self.headers)
        source = json.loads(res.content)
        source['filename']
        res = requests.get("https://splus.cloud" + source['filename'], headers=self.headers)
        image = Image.open(io.BytesIO(res.content))
        
        self.lastcontent = image
        self.lastres = 'get_cut'
        return image

    def get_band_img(self, ra, dec, radius, band='R', mode='linear'):
        res = requests.get("https://splus.cloud/api/get_band_image/" + str(ra) + "/" + str(dec) + "/" + str(radius) + "/" + str(band) + "/" + str(mode), headers=self.headers)
        source = json.loads(res.content)
        source['filename']
        res = requests.get("https://splus.cloud" + source['filename'], headers=self.headers)
        image = Image.open(io.BytesIO(res.content))
        
        self.lastcontent = image
        self.lastres = 'get_band_image'
        return image

    
    def get_cut(self, ra, dec, radius, band, filepath=None):
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
            
        res = requests.get("https://splus.cloud/api/get_direct_cut/"  + str(ra) + "/" + str(dec) + "/" + str(radius) + "/" + str(band), headers=self.headers)
        hdu = fits.open(io.BytesIO(res.content))
        if filepath != None:
            hdu.writeto(filepath + ".fz")
        
        self.lastcontent = hdu
        self.lastres = 'cut'
        return hdu

    def get_cut_weight(self, ra, dec, radius, band, filepath=None):
        if band.upper() == 'ALL':
            if filepath == None:
                return 'You must save the file while getting "all" bands'
            
            elif filepath != None:  
                filepath = filepath + ".tar.gz"
                res = requests.get("https://splus.cloud/api/get_direct_cut_weight/"  + str(ra) + "/" + str(dec) + "/" + str(radius) + "/" + "ALL", headers=self.headers)
                
                with open(filepath, 'wb') as f:
                    f.write(res.content)
                    f.close()
                    
                return 'File saved to ' + filepath
            
        res = requests.get("https://splus.cloud/api/get_direct_cut_weight/"  + str(ra) + "/" + str(dec) + "/" + str(radius) + "/" + str(band), headers=self.headers)
        hdu = fits.open(io.BytesIO(res.content))
        if filepath != None:
            hdu.writeto(filepath + ".fz")
        
        self.lastcontent = hdu
        self.lastres = 'cut'
        return hdu
    
    def get_field(self, field, band):
        res = requests.get("https://splus.cloud/api/get_direct_field/" + str(field) + "/" + str(band) , headers=self.headers)
        hdu = fits.open(io.BytesIO(res.content))
        
        self.lastres = 'field'
        self.lastcontent = hdu
        return hdu  

    def get_field_weight(self, field, band):
        res = requests.get("https://splus.cloud/api/get_direct_field_weight/" + str(field) + "/" + str(band) , headers=self.headers)
        hdu = fits.open(io.BytesIO(res.content))
        
        self.lastres = 'field'
        self.lastcontent = hdu
        return hdu  

    def get_tap_tables(self):
        if self.collab:
            print("Tables and columns info at https://splus.cloud/")
        else:
            print("Tables and columns info available at https://splus.cloud/query/")
            
    def query(self, query, table_upload=None, publicdata=None):
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
                if len(table_upload) > 2000:
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

                link = link.replace("http://10.180.0.208:8080", "https://splus.cloud").replace("http://10.180.0.209:8080", "https://splus.cloud").replace("http://10.180.0.207:8080", "https://splus.cloud").replace("http://10.180.0.219:8080", "https://splus.cloud")
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
        res = requests.get("https://splus.cloud/api/whichdr/" + str(ra) + "/" + str(dec) , headers=self.headers)
        res = res.content.decode("utf-8")
        
        res = ast.literal_eval(res)
        return res

    
    def get_last_result(self):
        return self.lastcontent