import pickle
import pandas as pd
import numpy as np
from astropy import units as u
from astroquery.utils.tap.core import TapPlus
from astropy.coordinates import SkyCoord
import requests

__author__ = "Lilianne Nakazono"
__version__ = "0.1.0"

class ClassifyObj:
    _morph = ['FWHM_n', 'A', 'B', 'KRON_RADIUS']
    _feat = ['u_iso',
                 'J0378_iso',
                 'J0395_iso',
                 'J0410_iso',
                 'J0430_iso',
                 'g_iso',
                 'J0515_iso',
                 'r_iso',
                 'J0660_iso',
                 'i_iso',
                 'J0861_iso',
                 'z_iso']
    _feat_wise = ['w1mpro', 'w2mpro']
    _error_wise = ['w1snr', 'w2snr', 'w1sigmpro', 'w2sigmpro']
    _pos = ["RA", "DEC"]

    def __init__(self, data, model = 'RF16', return_prob = True, match_irsa = False, verbose=True):
        self.data = data
        self.model = model
        self.return_prob = return_prob
        self.match_irsa = match_irsa
        self.verbose = verbose
        self.results = self.classificator()

    @staticmethod
    def get_wise(df, list_names):
        '''
        Deletes objects without WISE counterpart (> 2 arcsecond) from data

        Keywords arguments:
        data -- dataframe containing WISE information
        list_names --  names of the columns corresponding to W1 and W2 magnitudes/error/snr from WISE

        returns a copy of a subset from data with objects that have WISE counterpart
        '''

        copy = df.copy(deep=True)
        copy = copy.query("d2d <= 2")
        for feat in list_names:
            copy = copy[pd.isnull(copy[feat]) == False]
        return copy

    def irsa_query(self):
        '''
        Query ALLWISE catalogue from IRSA database

        Keywords arguments:
        data -- dataframe containing information of RA and DEC for each object
        return dataframe containing WISE sources
        '''

        ramin = np.min(self.data["RA"])
        ramax = np.max(self.data["RA"])
        decmin = np.min(self.data["DEC"])
        decmax = np.max(self.data["DEC"])
        col = ['ra', 'dec', 'w1mpro', 'w2mpro', 'w1snr', 'w2snr', 'w1sigmpro', 'w2sigmpro']
        if ramin < 2 and ramax > 358:
            ramax = np.max(self.data.query("RA<2"))
            ramin = np.min(self.data.query("RA>358"))
            query = f"""select {col[0]}, {col[1]}, {col[2]}, 
                                          {col[3]}, {col[4]}, {col[5]}, {col[6]}, {col[7]} from allwise_p3as_psd 
                                          where ra > {ramin - 0.15} or ra < {ramax + 0.15} and dec > {decmin - 0.15} and dec < {decmax + 0.15}"""
        else:
            query = f"""select {col[0]}, {col[1]}, {col[2]}, 
                                          {col[3]}, {col[4]}, {col[5]}, {col[6]}, {col[7]} from allwise_p3as_psd 
                                          where ra > {ramin - 0.15} and ra < {ramax + 0.15} and dec > {decmin - 0.15} and dec < {decmax + 0.15}"""

        irsa = TapPlus(url="https://irsa.ipac.caltech.edu/TAP")

        try:
            job = irsa.launch_job_async(query)
            r = job.get_results()
        except ConnectionError:
            print("Unexpected error during query.")

        df_wise = r.to_pandas()

        # Renaming any original column in data that has the same name from query
        for feat in col:
            if feat in self.data.columns:
                self.data.rename(columns={feat: feat+"_"+str(0)}, inplace=True)

        df_wise = df_wise.rename(
        columns={"col_0": col[0], "col_1": col[1], "col_2": col[2],
                 "col_3": col[3], "col_4": col[4], "col_5": col[5],
                 "col_6": col[6], "col_7": col[7]})

        return df_wise

    def crossmatch(self, df_wise):
        '''
        Perform cross match between two catalogues based on RA and DEC

        data_ra -- RA from S-PLUS catalogue
        data_dec -- DEC from S-PLUS catalogue
        df_wise_ra -- RA from ALLWISE catalogue
        df_wise_dec -- DEC from ALLWISE catalogue

        returns dataframe containing all original columns from data cross-matched with the ALLWISE query catalogue
        '''

        coo_splus = SkyCoord(self.data["RA"]* u.deg, self.data["DEC"] * u.deg)
        coo_wise = SkyCoord(df_wise["ra"]* u.deg, df_wise["dec"] * u.deg)
        idx, d2d, d3d = coo_splus.match_to_catalog_sky(coo_wise)
        self.data['d2d'] = pd.Series(d2d.arcsec)
        self.data = pd.concat([self.data, df_wise.iloc[idx].reset_index()], axis=1)

        return self.data

    def check_match_irsa(self):
        '''
        Check statement of match_irsa and performs cross-match if True
        data -- dataframe containing S-PLUS information
        match_irsa -- If true, query ALLWISE catalogue and performs cross-match. If false, checks if all necessary columns are in data
        '''


        if self.match_irsa == False:
            try:
                for element in self._feat_wise + self._error_wise:
                    i = self.data[element]
            except ValueError:
                print("Please ensure that ", element,
                      "column is in data. Please provide a ALLWISE cross-matched data or set match_irsa == True. Use model == 'opt' if the provided data do not have any source with WISE counteerpart.")
        else:
            try:
                for element in self._pos: #check if RA and DEC are in data to perfom the cross-match
                    i = self.data[element]
            except ValueError:
                print("Please ensure that ", element,
                      "column is in data, otherwise the cross-match with ALLWISE cannot be done.")
            if self.verbose:
                print("Querying ALLWISE catalogue via TapPlus(url='https://irsa.ipac.caltech.edu/TAP')...")
            df_wise = self.irsa_query()
            if self.verbose:
                print("Starting cross-match...")
            self.data = self.crossmatch(df_wise)
        return self.data

    def classificator(self):

        '''
        Create classifications for sources with or without counterpart
    
        Keywords arguments:
        data -- dataframe containing information of the 12 S-PLUS ISO magnitudes already extincted corrected
        prob -- if true, estimates the probabilities for each class
        model -- options are "both", "RF16" or "RF18". If "opt", returns classification from model trained with 12 S-PLUS bands
                 + 4 morphological features. If "RF18", returns classification from model trained with 12 S-PLUS bands + 2 WISE bands+
                 4 morphological features, only for sources with WISE counterpart. If "both", return classification from the same model as "RF18" (flagged as 0) if
                 the source has WISE counterpart, otherwise returns classification from model "RF16" (flagged as 1). 
        match_irsa -- determines if cross-match with ALLWISE catalogue will be performed. If model == "RF16", match_irsa == False.
        returns a dataframe with classes 
        '''

        if self.model == "RF16":
            if self.match_irsa:
                if self.verbose:
                    print("Parameter match_irsa is being set automatically to false.")
                self.match_irsa = False
        try:
            i = self.data.iloc[0,]
        except:
            raise(ValueError)("Data input is empty.")

        try:
            if self.model == 'RF16':
                print("Loading model")
                model = requests.get("https://splus.cloud/files/models/iDR3n4_RF_12S4M")
                model = model.content
                model = pickle.loads(model)
            elif self.model == 'RF18':
                print("Loading model")
                model_wise = requests.get("https://splus.cloud/files/models/iDR3n4_RF_12S2W4M")
                model_wise = model_wise.content
                model_wise = pickle.loads(model_wise)
            else:  
                print("Loading both models")
                model = requests.get("https://splus.cloud/files/models/iDR3n4_RF_12S4M")
                model = model.content
                model = pickle.loads(model)
                model_wise = requests.get("https://splus.cloud/files/models/iDR3n4_RF_12S2W4M")
                model_wise = model_wise.content
                model_wise = pickle.loads(model_wise)
        except:
            raise(ValueError)("Error downloading model from splus.cloud")


        try:
            for element in self._morph+self._feat:
                i = self.data[element]
        except ValueError:
            print("Please ensure that ", element, "column is in data. Use splusdata.connect.query() to retrieve it." )

        self.results = pd.DataFrame()

        if self.verbose:
            print("Note that this function assumes that the input data were previously extinction corrected. Starting classification... ")

        if self.model == "RF16":
            y_pred = pd.DataFrame(model.predict(self.data[self._morph + self._feat]))
            y_pred = y_pred.astype("float64")
            y_pred.index = self.data.index

            results = y_pred
            results.columns = ["CLASS"]

            if self.return_prob:
                if self.verbose:
                    print("Calculating probabilities...")
                prob_df = pd.DataFrame(model.predict_proba(self.data[self._morph + self._feat]))
                prob_df.index = self.data.index

                results = pd.concat([results, prob_df], axis=1)
                results.columns = ["CLASS", "PROB_QSO", "PROB_STAR", "PROB_GAL"]

        elif self.model == "RF18":
            self.check_match_irsa()
            data_wise = self.get_wise(self.data, self._feat_wise+self._error_wise)
            ypred_wise = pd.DataFrame(model_wise.predict(data_wise[self._morph + self._feat + self._feat_wise]))  # classify sources with WISE
            ypred_wise.index = data_wise.index
            results = ypred_wise
            results.columns = ["CLASS"]

            if self.return_prob:
                if self.verbose:
                    print("Calculating probabilities...")

                prob_wise_df = pd.DataFrame(model_wise.predict_proba(data_wise[self._morph + self._feat + self._feat_wise]))
                prob_wise_df.index = data_wise.index
                results = pd.concat([results, prob_wise_df], axis=1)
                results.columns = ["CLASS", "PROB_QSO", "PROB_STAR", "PROB_GAL"]

        elif self.model=="both":
            self.check_match_irsa()
            data_wise = self.get_wise(self.data, self._feat_wise+self._error_wise)
            data_nowise = self.data.drop(data_wise.index)

            y_pred = pd.DataFrame(model.predict(data_nowise[self._morph + self._feat]))
            y_pred = y_pred.astype("float64")
            y_pred.index = data_nowise.index
            y_pred["model_flag"] = "1"  # S-PLUS

            ypred_wise = pd.DataFrame(model_wise.predict(data_wise[self._morph + self._feat + self._feat_wise]))  # classify sources with WISE
            ypred_wise.index = data_wise.index
            ypred_wise["model_flag"] = "0"  # S-PLUS + WISE
            results = pd.concat([y_pred, ypred_wise], axis=0)
            results.columns = ["CLASS", "model_flag"]

            if self.return_prob:
                if self.verbose:
                    print("Calculating probabilities...")
                prob_df = pd.DataFrame(model.predict_proba(data_nowise[self._morph + self._feat]))
                prob_wise_df = pd.DataFrame(model_wise.predict_proba(data_wise[self._morph + self._feat + self._feat_wise]))
                prob_df.index = data_nowise.index
                prob_wise_df.index = data_wise.index
                prob_results = pd.concat([prob_df, prob_wise_df], axis=0)
                results = pd.concat([results, prob_results], axis=1)
                results.columns = ["CLASS", "model_flag", "PROB_QSO", "PROB_STAR", "PROB_GAL"]

        else:
            raise(ValueError)("Parameter 'model' should be 'RF16', 'RF18' or 'both'.")

        if self.verbose:
            print("Finished process.")

        return results.sort_index(axis=0)