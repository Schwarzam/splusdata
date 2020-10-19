import astropy
import pandas as pd
import numpy as np

from astropy.table import Table
from astropy.io import ascii
import sqlalchemy
from sqlalchemy import inspect
import psycopg2
import re
import itertools

def queryidr3(Survey, conditions=[], columns = ['Field', 'ID', 'RA', 'DEC', 'X', 'Y', 'ISOarea', 'MU_MAX', 'A', 'B', 'THETA', 'ELONGATION', 'ELLIPTICITY', 'PhotoFlagDet', 'CLASS_STAR', 'FWHM', 'U_auto', 'e_U_auto', 'F378_auto', 'e_F378_auto', 'F395_auto', 'e_F395_auto', 'F410_auto', 'e_F410_auto', 'F430_auto', 'e_F430_auto', 'G_auto', 'e_G_auto', 'F515_auto', 'e_F515_auto', 'R_auto', 'e_R_auto', 'F660_auto', 'e_F660_auto', 'I_auto', 'e_I_auto', 'F861_auto', 'e_F861_auto', 'Z_auto', 'e_Z_auto', 'nDet_auto', 'U_aper_3', 'e_U_aper_3', 'F378_aper_3', 'e_F378_aper_3', 'F395_aper_3', 'e_F395_aper_3', 'F410_aper_3', 'e_F410_aper_3', 'F430_aper_3', 'e_F430_aper_3', 'G_aper_3', 'e_G_aper_3', 'F515_aper_3', 'e_F515_aper_3', 'R_aper_3', 'e_R_aper_3', 'F660_aper_3', 'e_F660_aper_3', 'I_aper_3', 'e_I_aper_3', 'F861_aper_3', 'e_F861_aper_3', 'Z_aper_3', 'e_Z_aper_3', 'U_PStotal', 'e_U_PStotal', 'F378_PStotal', 'e_F378_PStotal', 'F395_PStotal', 'e_F395_PStotal', 'F410_PStotal', 'e_F410_PStotal', 'F430_PStotal', 'e_F430_PStotal', 'G_PStotal', 'e_G_PStotal', 'F515_PStotal', 'e_F515_PStotal', 'R_PStotal', 'e_R_PStotal', 'F660_PStotal', 'e_F660_PStotal', 'I_PStotal', 'e_I_PStotal', 'F861_PStotal', 'e_F861_PStotal', 'Z_PStotal', 'e_Z_PStotal', 'U_petro', 'F378_petro', 'F395_petro', 'F410_petro', 'F430_petro','G_petro','F515_petro','R_petro','F660_petro','I_petro','F861_petro','Z_petro','e_U_petro','e_F378_petro','e_F395_petro','e_F410_petro','e_F430_petro','e_G_petro','e_F515_petro','e_R_petro','e_F660_petro','e_I_petro','e_F861_petro','e_Z_petro'], password = None):
    if not password:
        password = str(input("input password: "))
    engine = sqlalchemy.create_engine(f'postgresql://SPLUS_readonly:{password}@splus.cloud:5432/splus')

    if columns != 'all':
        columns = format_cols(columns)
    if columns == 'all':
        columns = "*"

    try:
        if conditions == []:
            query = f"""SELECT {columns} FROM "{Survey.lower()}" """
            result = pd.read_sql_query(query, engine)
            print('Done!')
            return(result)

        if conditions[0].split('=')[0].strip().lower() == 'field':
            query = f"""SELECT {columns} FROM "{Survey.lower()}" WHERE "Field" = '{conditions[0].split('=')[1].strip()}'"""
            result = pd.read_sql_query(query, engine)
            print('Done!')
            return(result)
        if conditions[0].split('==')[0].strip().lower() == 'field':
            query = f"""SELECT {columns} FROM "{Survey.lower()}" WHERE "Field" = '{conditions[0].split('==')[1].strip()}'"""
            result = pd.read_sql_query(query, engine)
            print('Done!')
            return(result)

        if conditions[0].split('=')[0].strip().lower() == 'id':
            query = f"""SELECT {columns} FROM "{Survey.lower()}" WHERE "ID" = '{conditions[0].split('=')[1].strip()}'"""
            result = pd.read_sql_query(query, engine)
            print('Done!')
            return(result)
        if conditions[0].split('==')[0].strip().lower() == 'id':
            query = f"""SELECT {columns} FROM "{Survey.lower()}" WHERE "ID" = '{conditions[0].split('==')[1].strip()}'"""
            result = pd.read_sql_query(query, engine)
            print('Done!')
            return(result)

        if conditions != []:
            conditions = get_conditions(conditions)
            query = f"""SELECT {columns} FROM "{Survey.lower()}" WHERE """
            for key, condition in enumerate(conditions):
                if key == 0:
                    query = str(query) + str(condition) + ' '
                if key != 0:
                    query = str(query) + 'and ' + str(condition) + ' '
            print('getting data...\n')
            print('it may take a minute\n')
        result = pd.read_sql_query(query, engine)
        print('Done!')
        return(result)


    except sqlalchemy.exc.ProgrammingError:
        print("Error while searching, check if the column exists or if it is typed correctly")
    else:
        print("Something is wrong!")

def get_columns(password = None):
    if not password:
        password = str(input("input password: "))
    engine = sqlalchemy.create_engine(f'postgresql://SPLUS_readonly:{password}@splus.cloud:5432/splus')

    cols = []
    for x in inspect(engine).get_columns('main3.1'):
        cols.append(x['name'])

    return cols

def get_columns_return(engine):
    cols = []
    for x in inspect(engine).get_columns('main3.1'):
        cols.append(x['name'])

    return cols


def get_surveys():
    surveys = ['main3.1', 'main3.2', 'main3.3', 'main3.4', 'main3.5', 'main3.6', 'main3.7', 'main3.8', 'stripe82']
    print(surveys)

def get_conditions(condits):
    conditions = []
    cols = ['index', 'Field', 'ID', 'RA', 'DEC', 'X', 'Y', 'ISOarea', 'MU_MAX', 'A', 'B', 'THETA', 'ELONGATION', 'ELLIPTICITY', 'FLUX_RADIUS', 'KRON_RADIUS', 'PhotoFlagDet', 'CLASS_STAR', 'FWHM', 'FWHM_n', 's2nDet', 'PhotoFlag_U', 'CLASS_STAR_U', 'FWHM_U', 'PhotoFlag_F378', 'CLASS_STAR_F378', 'FWHM_F378', 'PhotoFlag_F395', 'CLASS_STAR_F395', 'FWHM_F395', 'PhotoFlag_F410', 'CLASS_STAR_F410', 'FWHM_F410', 'PhotoFlag_F430', 'CLASS_STAR_F430', 'FWHM_F430', 'PhotoFlag_G', 'CLASS_STAR_G', 'FWHM_G', 'PhotoFlag_F515', 'CLASS_STAR_F515', 'FWHM_F515', 'PhotoFlag_R', 'CLASS_STAR_R', 'FWHM_R', 'PhotoFlag_F660', 'CLASS_STAR_F660', 'FWHM_F660', 'PhotoFlag_I', 'CLASS_STAR_I', 'FWHM_I', 'PhotoFlag_F861', 'CLASS_STAR_F861', 'FWHM_F861', 'PhotoFlag_Z', 'CLASS_STAR_Z', 'FWHM_Z', 'U_auto', 'e_U_auto', 's2n_U_auto', 'F378_auto', 'e_F378_auto', 's2n_F378_auto', 'F395_auto', 'e_F395_auto', 's2n_F395_auto', 'F410_auto', 'e_F410_auto', 's2n_F410_auto', 'F430_auto', 'e_F430_auto', 's2n_F430_auto', 'G_auto', 'e_G_auto', 's2n_G_auto', 'F515_auto', 'e_F515_auto', 's2n_F515_auto', 'R_auto', 'e_R_auto', 's2n_R_auto', 'F660_auto', 'e_F660_auto', 's2n_F660_auto', 'I_auto', 'e_I_auto', 's2n_I_auto', 'F861_auto', 'e_F861_auto', 's2n_F861_auto', 'Z_auto', 'e_Z_auto', 's2n_Z_auto', 'nDet_auto', 'U_petro', 'e_U_petro', 's2n_U_petro', 'F378_petro', 'e_F378_petro', 's2n_F378_petro', 'F395_petro', 'e_F395_petro', 's2n_F395_petro', 'F410_petro', 'e_F410_petro', 's2n_F410_petro', 'F430_petro', 'e_F430_petro', 's2n_F430_petro', 'G_petro', 'e_G_petro', 's2n_G_petro', 'F515_petro', 'e_F515_petro', 's2n_F515_petro', 'R_petro', 'e_R_petro', 's2n_R_petro', 'F660_petro', 'e_F660_petro', 's2n_F660_petro', 'I_petro', 'e_I_petro', 's2n_I_petro', 'F861_petro', 'e_F861_petro', 's2n_F861_petro', 'Z_petro', 'e_Z_petro', 's2n_Z_petro', 'nDet_petro', 'U_iso', 'e_U_iso', 's2n_U_iso', 'F378_iso', 'e_F378_iso', 's2n_F378_iso', 'F395_iso', 'e_F395_iso', 's2n_F395_iso', 'F410_iso', 'e_F410_iso', 's2n_F410_iso', 'F430_iso', 'e_F430_iso', 's2n_F430_iso', 'G_iso', 'e_G_iso', 's2n_G_iso', 'F515_iso', 'e_F515_iso', 's2n_F515_iso', 'R_iso', 'e_R_iso', 's2n_R_iso', 'F660_iso', 'e_F660_iso', 's2n_F660_iso', 'I_iso', 'e_I_iso', 's2n_I_iso', 'F861_iso', 'e_F861_iso', 's2n_F861_iso', 'Z_iso', 'e_Z_iso', 's2n_Z_iso', 'nDet_iso', 'U_aper_3', 'e_U_aper_3', 's2n_U_aper_3', 'F378_aper_3', 'e_F378_aper_3', 's2n_F378_aper_3', 'F395_aper_3', 'e_F395_aper_3', 's2n_F395_aper_3', 'F410_aper_3', 'e_F410_aper_3', 's2n_F410_aper_3', 'F430_aper_3', 'e_F430_aper_3', 's2n_F430_aper_3', 'G_aper_3', 'e_G_aper_3', 's2n_G_aper_3', 'F515_aper_3', 'e_F515_aper_3', 's2n_F515_aper_3', 'R_aper_3', 'e_R_aper_3', 's2n_R_aper_3', 'F660_aper_3', 'e_F660_aper_3', 's2n_F660_aper_3', 'I_aper_3', 'e_I_aper_3', 's2n_I_aper_3', 'F861_aper_3', 'e_F861_aper_3', 's2n_F861_aper_3', 'Z_aper_3', 'e_Z_aper_3', 's2n_Z_aper_3', 'nDet_aper_3', 'U_aper_6', 'e_U_aper_6', 's2n_U_aper_6', 'F378_aper_6', 'e_F378_aper_6', 's2n_F378_aper_6', 'F395_aper_6', 'e_F395_aper_6', 's2n_F395_aper_6', 'F410_aper_6', 'e_F410_aper_6', 's2n_F410_aper_6', 'F430_aper_6', 'e_F430_aper_6', 's2n_F430_aper_6', 'G_aper_6', 'e_G_aper_6', 's2n_G_aper_6', 'F515_aper_6', 'e_F515_aper_6', 's2n_F515_aper_6', 'R_aper_6', 'e_R_aper_6', 's2n_R_aper_6', 'F660_aper_6', 'e_F660_aper_6', 's2n_F660_aper_6', 'I_aper_6', 'e_I_aper_6', 's2n_I_aper_6', 'F861_aper_6', 'e_F861_aper_6', 's2n_F861_aper_6', 'Z_aper_6', 'e_Z_aper_6', 's2n_Z_aper_6', 'nDet_aper_6', 'U_PStotal', 'e_U_PStotal', 's2n_U_PStotal', 'F378_PStotal', 'e_F378_PStotal', 's2n_F378_PStotal', 'F395_PStotal', 'e_F395_PStotal', 's2n_F395_PStotal', 'F410_PStotal', 'e_F410_PStotal', 's2n_F410_PStotal', 'F430_PStotal', 'e_F430_PStotal', 's2n_F430_PStotal', 'G_PStotal', 'e_G_PStotal', 's2n_G_PStotal', 'F515_PStotal', 'e_F515_PStotal', 's2n_F515_PStotal', 'R_PStotal', 'e_R_PStotal', 's2n_R_PStotal', 'F660_PStotal', 'e_F660_PStotal', 's2n_F660_PStotal', 'I_PStotal', 'e_I_PStotal', 's2n_I_PStotal', 'F861_PStotal', 'e_F861_PStotal', 's2n_F861_PStotal', 'Z_PStotal', 'e_Z_PStotal', 's2n_Z_PStotal', 'nDet_magPStotal']
    for item in condits:
        re_pattern = r'\b\w+\b'
        words = re.findall(re_pattern, item)
        for word in words:
            try:
                cols.index(word)
                item = item.replace(word, f'"{word}"', )
                item = item.replace('""', '"')
            except: pass
        conditions.append(item)
    return conditions


def queryidr3_sql(password = None):
    print('Example: SELECT "RA", "DEC" FROM "main3.1" WHERE "RA" > 68.1 and "RA" < 68.2')
    if not password:
        password = str(input("input password: "))
    engine = sqlalchemy.create_engine(f'postgresql://SPLUS_readonly:{password}@splus.cloud:5432/splus')

    try:
        result = pd.read_sql_query(input("input query: "), engine)

        return result
    except:
        print("ERROR with query")

def format_cols(columns):
    x = ''
    for key, col in enumerate(columns):
        if key != len(columns) - 1:
            x = x + str(f'"{col}",')
        if key == len(columns) - 1:
            x = x + str(f'"{col}"')
    return x
