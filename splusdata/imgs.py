from PIL import Image
import requests
from io import BytesIO
import numpy as np
import matplotlib.pyplot as plt
from splusdata.searchcoords import searchcoords

def get_img_obj(Field, ID, filename=None):
    url = f'http://splus.cloud:8000/media/{Field}/{ID}.jpg'
    response = requests.get(url)
    img = Image.open(BytesIO(response.content))

    if filename:
        img2 = np.array(img)
        plt.imsave(arr=img2, fname=filename)

    return img

def get_img_coords(RA, DEC, filename=None, password=None):
    if not password:
        obj = searchcoords(RA, DEC).search_obj()
    if password:
        obj = searchcoords(RA, DEC, password).search_obj()
    print(obj)
    url = f'http://splus.cloud:8000/media/{obj.Field.array[0]}/{obj.ID.array[0]}.jpg'
    response = requests.get(url)
    img = Image.open(BytesIO(response.content))

    if filename:
        img2 = np.array(img)
        plt.imsave(arr=img2, fname=filename)

    return img
