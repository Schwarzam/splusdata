import numpy as np
import pandas as pd

# Function that calculates PDFs
def Calc_PDF(x, Weights, Means, STDs):
    PDF = np.sum(Weights*(1/(STDs*np.sqrt(2*np.pi))) * np.exp((-1/2) * ((x[:,None]-Means)**2)/(STDs)**2), axis=1)
    return PDF/np.trapz(PDF, x)

def Calculate_PDFs(PDF_Catalogue, x=np.arange(0, 1.001, 0.001)):
    Final_PDFs = []
    PDF_Catalogue = PDF_Catalogue.reset_index(drop=True)
    for i in range(len(PDF_Catalogue)):
        Final_PDFs.append(Calc_PDF(x, np.fromstring(PDF_Catalogue['PDF_Weights'][i][0:], sep=','), 
                                      np.fromstring(PDF_Catalogue['PDF_Means'][i][0:], sep=','), 
                                      np.fromstring(PDF_Catalogue['PDF_STDs'][i][0:], sep=',')))

    return x, Final_PDFs