from __future__ import print_function
import numpy as np
import glob
import json
import matplotlib.pyplot as plt
import sys
import argparse
import os
from colour import Color
from astropy.coordinates import SkyCoord
from astropy import units as u

class Graph:
    def __init__(self, Galaxy):
        self.data = Galaxy
        data = self.data
        n = data.RA
        Number = []

        self.wl = [3485, 3785, 3950, 4100, 4300, 4803, 5150, 6250, 6600, 7660, 8610, 9110]
        self.color = "#CC00FF", "#9900FF", "#6600FF", "#0000FF", "#009999", "#006600", "#DD8000", "#FF0000", "#CC0066", "#990033", "#660033", "#330034"

        mag_auto  = []
        mag_petro = []
        mag_aper = []
        mag_total = []

        mag_auto_err  = []
        mag_petro_err  = []
        mag_aper_err = []
        mag_total_err = []

        mag_auto.append(data.U_auto)
        mag_auto.append(data.F378_auto)
        mag_auto.append(data.F395_auto)
        mag_auto.append(data.F410_auto)
        mag_auto.append(data.F430_auto)
        mag_auto.append(data.G_auto)
        mag_auto.append(data.F515_auto)
        mag_auto.append(data.R_auto)
        mag_auto.append(data.F660_auto)
        mag_auto.append(data.I_auto)
        mag_auto.append(data.F861_auto)
        mag_auto.append(data.Z_auto)
            #Petro
        mag_petro.append(data.U_petro)
        mag_petro.append(data.F378_petro)
        mag_petro.append(data.F395_petro)
        mag_petro.append(data.F410_petro)
        mag_petro.append(data.F430_petro)
        mag_petro.append(data.G_petro)
        mag_petro.append(data.F515_petro)
        mag_petro.append(data.R_petro)
        mag_petro.append(data.F660_petro)
        mag_petro.append(data.I_petro)
        mag_petro.append(data.F861_petro)
        mag_petro.append(data.Z_petro)
            #aper
        mag_aper.append(data.U_aper_3)
        mag_aper.append(data.F378_aper_3)
        mag_aper.append(data.F395_aper_3)
        mag_aper.append(data.F410_aper_3)
        mag_aper.append(data.F430_aper_3)
        mag_aper.append(data.G_aper_3)
        mag_aper.append(data.F515_aper_3)
        mag_aper.append(data.R_aper_3)
        mag_aper.append(data.F660_aper_3)
        mag_aper.append(data.I_aper_3)
        mag_aper.append(data.F861_aper_3)
        mag_aper.append(data.Z_aper_3)

        mag_total.append(data.U_PStotal)
        mag_total.append(data.F378_PStotal)
        mag_total.append(data.F395_PStotal)
        mag_total.append(data.F410_PStotal)
        mag_total.append(data.F430_PStotal)
        mag_total.append(data.G_PStotal)
        mag_total.append(data.F515_PStotal)
        mag_total.append(data.R_PStotal)
        mag_total.append(data.F660_PStotal)
        mag_total.append(data.I_PStotal)
        mag_total.append(data.F861_PStotal)
        mag_total.append(data.Z_PStotal)

            #ERRO AUTO
        mag_auto_err.append(data.e_U_auto)
        mag_auto_err.append(data.e_F378_auto)
        mag_auto_err.append(data.e_F395_auto)
        mag_auto_err.append(data.e_F410_auto)
        mag_auto_err.append(data.e_F430_auto)
        mag_auto_err.append(data.e_G_auto)
        mag_auto_err.append(data.e_F515_auto)
        mag_auto_err.append(data.e_R_auto)
        mag_auto_err.append(data.e_F660_auto)
        mag_auto_err.append(data.e_I_auto)
        mag_auto_err.append(data.e_F861_auto)
        mag_auto_err.append(data.e_Z_auto)

            #ERRO petro
        mag_petro_err.append(data.e_U_petro)
        mag_petro_err.append(data.e_F378_petro)
        mag_petro_err.append(data.e_F395_petro)
        mag_petro_err.append(data.e_F410_petro)
        mag_petro_err.append(data.e_F430_petro)
        mag_petro_err.append(data.e_G_petro)
        mag_petro_err.append(data.e_F515_petro)
        mag_petro_err.append(data.e_R_petro)
        mag_petro_err.append(data.e_F660_petro)
        mag_petro_err.append(data.e_I_petro)
        mag_petro_err.append(data.e_F861_petro)
        mag_petro_err.append(data.e_Z_petro)

            #ERRO aper
        mag_aper_err.append(data.e_U_aper_3)
        mag_aper_err.append(data.e_F378_aper_3)
        mag_aper_err.append(data.e_F395_aper_3)
        mag_aper_err.append(data.e_F410_aper_3)
        mag_aper_err.append(data.e_F430_aper_3)
        mag_aper_err.append(data.e_G_aper_3)
        mag_aper_err.append(data.e_F515_aper_3)
        mag_aper_err.append(data.e_R_aper_3)
        mag_aper_err.append(data.e_F660_aper_3)
        mag_aper_err.append(data.e_I_aper_3)
        mag_aper_err.append(data.e_F861_aper_3)
        mag_aper_err.append(data.e_Z_aper_3)

        mag_total_err.append(data.e_U_PStotal)
        mag_total_err.append(data.e_F378_PStotal)
        mag_total_err.append(data.e_F395_PStotal)
        mag_total_err.append(data.e_F410_PStotal)
        mag_total_err.append(data.e_F430_PStotal)
        mag_total_err.append(data.e_G_PStotal)
        mag_total_err.append(data.e_F515_PStotal)
        mag_total_err.append(data.e_R_PStotal)
        mag_total_err.append(data.e_F660_PStotal)
        mag_total_err.append(data.e_I_PStotal)
        mag_total_err.append(data.e_F861_PStotal)
        mag_total_err.append(data.e_Z_PStotal)

        font = {'family': 'serif',
                'color':  'black',
                'weight': 'normal',
                'size': 16,
                }

        for i in range(len(mag_auto)):
          mag_auto[i] = float(mag_auto[i])
        for i in range(len(mag_auto_err)):
          mag_auto_err[i] = float(mag_auto_err[i])
        for i in range(len(mag_petro)):
          mag_petro[i] = float(mag_petro[i])
        for i in range(len(mag_petro_err)):
          mag_petro_err[i] = float(mag_petro_err[i])
        for i in range(len(mag_petro)):
          mag_aper[i] = float(mag_aper[i])
        for i in range(len(mag_petro_err)):
          mag_aper_err[i] = float(mag_aper_err[i])
        for i in range(len(mag_total)):
          mag_total[i] = float(mag_total[i])
        for i in range(len(mag_total_err)):
          mag_total_err[i] = float(mag_total_err[i])

        self.mag_auto = mag_auto
        self.mag_petro = mag_petro
        self.mag_aper = mag_aper
        self.mag_total = mag_total

        self.mag_auto_err = mag_auto_err
        self.mag_petro_err = mag_petro_err
        self.mag_aper_err = mag_aper_err
        self.mag_total_err = mag_total_err



    def autoplot(self, fname=''):
        data = self.data
        n = data.RA

        wl = self.wl
        color = self.color
        title = f'auto - {self.data.ID}'
        mag_auto  =self.mag_auto
        mag_auto_err  = self.mag_auto_err

        mag_auto = [np.nan if x == 99.0 else x for x in mag_auto]
        mag_auto = [np.nan if x == -99.0 else x for x in mag_auto]

        mag_auto_err = [np.nan if x >= 5 else x for x in mag_auto_err]
        mag_auto_err = [np.nan if x <= -5 else x for x in mag_auto_err]
        return_plot(wl, mag_auto, mag_auto_err, title, fname)

    def petroplot(self, fname=''):
        data = self.data
        n = data.RA

        wl = self.wl
        color = self.color
        title = f'petro - {self.data.ID}'
        mag_petro = self.mag_petro
        mag_petro_err  = self.mag_petro_err

        mag_petro = [np.nan if x == 99.0 else x for x in mag_petro]
        mag_petro = [np.nan if x == -99.0 else x for x in mag_petro]

        mag_petro_err = [np.nan if x >= 5 else x for x in mag_petro_err]
        mag_petro_err = [np.nan if x <= -5 else x for x in mag_petro_err]
        return_plot(wl, mag_petro, mag_petro_err, title, fname='')

    def aperplot(self, fname=''):
        data = self.data
        n = data.RA
        Number = []
        title = f'aper - {self.data.ID}'

        wl = self.wl
        color = self.color
        mag_aper = self.mag_aper
        mag_aper_err  = self.mag_aper_err

        mag_aper = [np.nan if x == 99.0 else x for x in mag_aper]
        mag_aper = [np.nan if x == -99.0 else x for x in mag_aper]

        mag_aper_err = [np.nan if x >= 5 else x for x in mag_aper_err]
        mag_aper_err = [np.nan if x <= -5 else x for x in mag_aper_err]

        return_plot(wl, mag_aper, mag_aper_err, title, fname)

    def totalplot(self, fname=''):
        data = self.data
        n = data.RA
        Number = []
        title = f'total - {self.data.ID}'
        wl = self.wl
        color = self.color
        mag_total = self.mag_total
        mag_total_err  = self.mag_total_err

        mag_total = [np.nan if x == 99.0 else x for x in mag_total]
        mag_total = [np.nan if x == -99.0 else x for x in mag_total]

        mag_total_err = [np.nan if x >= 5 else x for x in mag_total_err]
        mag_total_err = [np.nan if x <= -5 else x for x in mag_total_err]
        return_plot(wl, mag_total, mag_total_err, title, fname)

def return_plot(wl, mag, mag_err, title, fname=''):
    color = "#CC00FF", "#9900FF", "#6600FF", "#0000FF", "#009999", "#006600", "#DD8000", "#FF0000", "#CC0066", "#990033", "#660033", "#330034"
    fig = plt.figure(figsize=(5, 3.3))
    ax = fig.add_subplot(111)
    ax.tick_params(axis='x', labelsize=12)
    ax.tick_params(axis='y', labelsize=12)
    ax.set_xlim(xmin=3000, xmax=9700)

    ax.set_xlabel(r'Wavelength $[\mathrm{\AA]}$', fontsize = 12)
    ax.set_ylabel(r'Magnitude [AB]', fontsize = 12)
    ax.plot(wl, mag, '-k', alpha=0.2)

    ax.scatter(wl, mag, c=color, s=70, zorder=10)
    ax.errorbar(wl, mag, mag_err, fmt='.', elinewidth=1.9, markeredgewidth=1.7,  capsize=6.6)

    plt.title(title, fontsize=14)
    plt.gca().invert_yaxis()

    if fname != '':
        plt.savefig(f'{fname}')

    f2 = plt
    return f2
