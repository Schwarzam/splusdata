import math
import numpy as numpy
from astropy.wcs import WCS
from astropy.io import fits
from astropy.table import Table
import os as os
from scipy import interpolate
from scipy import fft

##Butterworth
def filter_bw(hdu):
    #frequencia de corte da filtragem a ser utilizada. Para os dados do SPLUS 0.5 é um valor ótimo.
    cutoff_frequency_x=0.5
    cutoff_frequency_y=0.5

    #ordem da filtragem, para os dados do SPLUS a melhor ordem é 1. Se usar 2, começam a surgir anéis.
    order=1.0

    #formato do filtro, não mudar. Para SPLUS elipse2= yes
    elipse='no'
    elipse2='yes'
    elipsevssquare='no'

    #tamanho dos pixels
    CDELT1=0.55
    CDELT2=0.55

    try:
        data=hdu[0].data
        if data == None:
            data=hdu[1].data
    except:
        data=hdu[1].data
    
    #y-eixo vertical da imagem
    #-eixo horizontal da imagem

    y,x =data.shape


    #imagem zerada com tamanho maior do que o original, ela recebe a informação da imagem original
    imagemzero=numpy.zeros((y+6,x+6))

    for i in range(0,x):
        for j in range(0,y):
            imagemzero[3+j,3+i]=data[j,i]

    #replicação da informação da imagem nas bordas(borda esquerda do cubo)

    for i in range(0,3):
        for j in range(0,y):
            imagemzero[3+j,i]=data[j,0]

    #replicação da informação da imagem nas bordas(borda direita do cubo)

    for i in range(0,3):
        for j in range(0,y):
            imagemzero[3+j,3+x+i]=data[j,x-1]

    #replicação da  informação da imagem nas bordas(borda de baixo do cubo)

    for i in range(0,x):
        for j in range(0,3):
            imagemzero[j,3+i]=data[0,i]

    #replicação da  informação da imagem nas bordas(borda de cima do cubo)

    for i in range(0,x):
        for j in range(0,3):
            imagemzero[3+y+j,3+i]= data[y-1,i]

    #sobrou os 4 cantos da imagem com zeros, precisamos preenche-los.

    #canto inferior esquerdo
    for i in range(0,3):
        for j in range(0,3):
            imagemzero[j,i]=imagemzero[j,3]

    #canto inferior direito
    for i in range(0,3):
        for j in range(0,3):
            imagemzero[j,3+i+x]=imagemzero[j,3+x-1]

    #canto superior esquerdo
    for i in range (0,3):
        for j in range(0,3):
            imagemzero[3+y+j,i]=imagemzero[3+y+j,3]

    #canto superior direito
    for i in range(0,3):
        for j in range(0,3):
            imagemzero[3+y+j,3+x+i]=imagemzero[3+y+j,3+x-1]

    y1,x1=imagemzero.shape

    #cria uma imagem maior com bordas zeradas mas com a imagemzero no meio (segunda ampliação do cubo)
    imagemfinalexpandida=numpy.zeros((y1+30,x1+30))
    imagemfinalexpandida[15:y1+15,15:x1+15]=imagemzero

    interpol_values=numpy.zeros((2,2))
    interpol_values1=numpy.zeros((2,2))
    interpol_values2=numpy.zeros((2,2))
    interpol_values3=numpy.zeros((2,2))

    temporary_column=numpy.zeros((y1+2,2))
    temporary_column[y1+1,0]=y1+30
    temporary_column[1:y1+1,0]=range(15,y1+15)

    #as bordas desta imagem devem ter valores caindo para zero.

    interpol_values[1,0]=15
    for i in range(15,x1+30):
        interpol_values[1,1]=imagemfinalexpandida[15,i]
        interpolate_function=interpolate.interp1d(interpol_values[0:2,0],interpol_values[0:2,1], kind='linear')
        imagemfinalexpandida[0:16,i]=interpolate_function(numpy.arange(16))

    interpol_values1[0,0]=y1+15-1
    interpol_values1[1,0]=y1+30
    interpol_values1[1,1]=0.0
    for i in range(15,x1+30):
        interpol_values1[0,1]=imagemfinalexpandida[y1+15-1,i]
        interpolate_function1=interpolate.interp1d(interpol_values1[0:2,0],interpol_values1[0:2,1], kind='linear')
        imagemfinalexpandida[y1+15-1:y1+30,i]=interpolate_function1(y1+15-1+numpy.arange(16))

    interpol_values2[0,0]=0.0
    interpol_values2[1,0]=15
    interpol_values2[0,1]=0.0
    for j in range(0,y1+30):
        interpol_values2[1,1]=imagemfinalexpandida[j,15]
        interpolate_function2=interpolate.interp1d(interpol_values2[0:2,0],interpol_values2[0:2,1], kind='linear')
        imagemfinalexpandida[j,0:16]=interpolate_function2(numpy.arange(16))

    interpol_values3[0,0]=x1+15-1
    interpol_values3[1,0]=x1+30
    interpol_values3[1,1]=0.0
    for j in range(0, y1+30):
        interpol_values3[0,1]=imagemfinalexpandida[j,x1+15-1]
        interpolate_function3=interpolate.interp1d(interpol_values3[0:2,0],interpol_values3[0:2,1], kind='linear')
        imagemfinalexpandida[j,x1+15-1:x1+30]=interpolate_function3(x1+15-1+numpy.arange(16))

    yf,xf= imagemfinalexpandida.shape

    #criar o filtro com o dobro do tamanho do imagemfinalexpandida (que vai ser o tamanho da transformada de fourier)
    filtro=numpy.zeros((2*yf,2*xf))

    aa=cutoff_frequency_x*xf
    bb=cutoff_frequency_y*yf
    cc=cutoff_frequency_x*xf
    dd=cutoff_frequency_y*yf

    exporder=2.0*order

    imfilter1=filtro
    xm=xf
    ym=yf

    for i in range(0,2*xf):
        for j in range(0,2*yf):
            conta= math.sqrt(((i-xm)/aa)**2+((j-ym)/bb)**2)
            imfilter1[j,i]=1.0/(1.0+conta**exporder)

    imfilter2=filtro
    for i in range(0,2*xf):
        for j in range(0,2*yf):
            conta1=abs(i-xm)/cc
            conta2=abs(j-ym)/dd
            imfilter2[j,i]=(1.0/(1.0+conta1**exporder))*(1.0/(1.0+conta2**exporder))

    #define o filtro final (baseando-se no seu formato)        
    if elipse == 'yes':
        filtro=imfilter1
    elif elipse2 == 'yes':
        filtro=imfilter1*imfilter1
    elif elipsevssquare == 'yes':
        filtro=imfilter1*imfilter2

    #imagem que vai receber a filtragem
    imagemsaida=imagemfinalexpandida
    npadd=numpy.zeros((2*yf,2*xf))


    #faz a filtragem

    imagein=imagemfinalexpandida[0:yf,0:xf]
    imageflag=npadd
        #padding - procedimento de multiplicar certos pixels da imagem por -1, para que a transformada de Fourier fique com
        #frequência = 0 no centro.
        #faz o  padding para cada imagem
    for i in range(0,2*xf):
        for j in range(0,2*yf):
            if (i<=xf-1) and (j > yf-1):
                if((i+j)%2) != 0:
                    flag=1
                else:
                    flag=-1
                imageflag[j,i]=flag*imagein[j-yf,i]
            else:
                imageflag[j,i]=0.0

    #faz a transformada de fourier
    twodfft=fft.fft2(imageflag)
    #multiplica pelo filtro
    filtragem=twodfft*filtro
    #faz a transformada de fourier inversa
    twodifft=fft.ifft2(filtragem)
    invfft=numpy.real(twodifft)
    paddout=npadd
    imageout=imagein

    #remove o padding
    for i in range(0,2*xf):
        for j in range(0,2*yf):
            if((i+j)%2) != 0:
                flag=1
            else:
                flag=-1
            paddout[j,i]=flag*invfft[j,i]
            if (i<=xf-1) and (j >yf-1):
                imageout[j-yf,i]=paddout[j,i]
    imagemsaida[0:yf,0:xf]=imageout


    #cria a imagem final, cortando a imagem filtrada (tirando as bordas)
    imagemsaida_final=numpy.zeros((y,x))
    imagemsaida_final=imagemsaida[18:yf-18,18:xf-18]

    #header
    header=hdu[0].header
    new_hdu = fits.PrimaryHDU()
    new_hdu.header=header
    image_hdu = fits.ImageHDU(imagemsaida_final)
    new_hdu.header.set('SIMPLE','T')
    new_hdu.header.set('CDELT1',0.55)
    new_hdu.header.set('CDELT2',0.55)
    new_hdu.verify('fix')
    hdul = fits.HDUList([new_hdu, image_hdu])
    
    return hdul