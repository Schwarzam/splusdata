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
        
    
    def twelve_band_img(self, ra, dec, radius):
        res = requests.get("https://splus.cloud/api/collaboration/get_image/" + str(ra) + "/" + str(dec) + "/" + str(radius), headers=self.headers)
        source = json.loads(res.content)
        source['filename']
        res = requests.get("https://splus.cloud" + source['filename'], headers=self.headers)
        image = Image.open(io.BytesIO(res.content))
        
        self.lastcontent = image
        self.lastres = '12img'
        return image
    
    def get_cut(self, ra, dec, radius, band):
        res = requests.get("https://splus.cloud/api/collaboration/get_direct_link/"  + str(ra) + "/" + str(dec) + "/" + str(radius) + "/" + str(band), headers=self.headers)
        hdu = fits.open(io.BytesIO(res.content))
        
        self.lastcontent = hdu
        self.lastres = 'cut'
        return hdu
    
    def get_field(self, field, band):
        res = requests.get("https://splus.cloud/api/collaboration/get_direct_field/" + str(field) + "/" + str(band) , headers=self.headers)
        hdu = fits.open(io.BytesIO(res.content))
        
        self.lastres = 'field'
        self.lastcontent = hdu
        return hdu  
    
    def get_tap_tables(self):
        if self.collab:
            print("Tables and columns info at https://splus.cloud/")
        else:
            print("Tables and columns info available at https://splus.cloud/query/")
            
    def query(self, query):
        if self.collab:
            baselink = "https://splus.cloud/tap/tap/async/"
        else:
            baselink = "https://splus.cloud/public-TAP/tap/async/"
            
        data = {
            "request": 'doQuery',
            "version": '1.0',
            "lang": 'ADQL',
            "phase": 'run',
            "query": query,
            "format": 'fits'
        }

        res = requests.post(baselink , data = data, headers=headers)
        xmldoc = minidom.parse(io.BytesIO(res.content))

        try:
            item = xmldoc.getElementsByTagName('phase')[0]
            process = item.firstChild.data

            item = xmldoc.getElementsByTagName('jobId')[0]
            jobID = item.firstChild.data

            while process == 'EXECUTING':
                print('Executing')
                res = requests.get(baselink + jobID, headers=headers)
                xmldoc = minidom.parse(io.BytesIO(res.content))

                item = xmldoc.getElementsByTagName('phase')[0]
                process = item.firstChild.data
                time.sleep(5)

            if process == 'COMPLETED':
                item = xmldoc.getElementsByTagName('result')[0]
                link = item.attributes['xlink:href'].value

                link = link.replace("http://127.0.0.1:8080", "https://splus.cloud")
                res = requests.get(link, headers=headers)
                
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
    
    def get_last_result(self):
        return self.lastcontent
