import numpy as np
import pandas as pd

# Definição usada pra calcular as PDFs
def Calc_PDF(x, Weights, Means, STDs):
    PDF = np.sum(Weights*(1/(STDs*np.sqrt(2*np.pi))) * np.exp((-1/2) * ((x[:,None]-Means)**2)/(STDs)**2), axis=1)
    return PDF/np.trapz(PDF, x)

# Carregamos os dados (recém baixados do splus.cloud)
# PDF_Catalogue = pd.read_csv('../PDF_Test.csv')


def Calculate_PDFs(PDF_Catalogue):
    # Agora calculamos as PDFs em loop
    Final_PDFs = []
    x = np.arange(0, 1, 0.001)
    for i in tqdm(range(len(PDF_Catalogue))):
        Final_PDFs.append(Calc_PDF(x, np.fromstring(PDF_Catalogue['PDF_Weights'][i][1:-1], sep=','), 
                                      np.fromstring(PDF_Catalogue['PDF_Means'][i][1:-1], sep=','), 
                                      np.fromstring(PDF_Catalogue['PDF_STDs'][i][1:-1], sep=',')))

    return Final_PDFs