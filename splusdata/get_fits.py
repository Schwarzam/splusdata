import warnings
from urllib.request import urlopen
import time
import numpy as np
import json
from astropy.io import fits
from astropy.nddata import Cutout2D
from astropy import wcs
from astropy import coordinates as coord
from astropy import units as u

def get_fits(name, ra, dec, cut_size, band, filename=None):
    warnings.simplefilter("ignore")

    response = urlopen(f'http://splus.cloud:8000/api/{name}/{ra}/{dec}/{cut_size}/{band}/0')
    name_in_query = response.read().decode('utf-8')

    response = urlopen(f'http://splus.cloud:8000/api/{name_in_query}/{ra}/{dec}/{cut_size}/{band}/1')
    queue = response.read().decode('utf-8')

    while int(queue) != 0:
        time.sleep(5)
        response = urlopen(f'http://splus.cloud:8000/api/{name_in_query}/{ra}/{dec}/{cut_size}/{band}/1')
        string = response.read().decode('utf-8')

        queue = int(string)
        print('you are in position:', string, 'in queue')

    if int(queue) == 0:
        response = urlopen(f'http://splus.cloud:8000/api/{name_in_query}/{ra}/{dec}/{cut_size}/{band}/2')
        queue = response.read().decode('utf-8')

        new_hdu = fits.PrimaryHDU()
        for key, value in json.loads(queue).items():
            if key != 'data':
                new_hdu.header[key] = value
            if key == 'data':
                new_hdu.data = np.array(value).astype('float64')

        if filename:
            new_hdu.writeto(filename)

        return new_hdu
