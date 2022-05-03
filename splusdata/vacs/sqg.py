import pickle
import pandas as pd
import numpy as np
from astropy import units as u
from astroquery.utils.tap.core import TapPlus
from astropy.coordinates import SkyCoord
import requests

class SQGClass:
    __author__ = "Lilianne Nakazono"
    __version__ = "0.1.0"
    _pos = ["RA", "DEC"]
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

    def __init__(self, model='auto', verbose=False):
        self.model = model
        self.verbose = verbose
        try:
            if self.model == 'RF16':
                if self.verbose:
                    print("Loading model...")
                self.model_splus = requests.get("https://splus.cloud/files/models/iDR3n4_RF_12S4M")
                self.model_splus = self.model_splus.content
                self.model_splus = pickle.loads(self.model_splus)
            elif self.model == 'RF18':
                if self.verbose:
                    print("Loading model...")
                self.model_wise = requests.get("https://splus.cloud/files/models/iDR3n4_RF_12S2W4M")
                self.model_wise = self.model_wise.content
                self.model_wise = pickle.loads(self.model_wise)
            else:
                if self.verbose:
                    print("Loading both models...")
                self.model_splus = requests.get("https://splus.cloud/files/models/iDR3n4_RF_12S4M")
                self.model_splus = self.model_splus.content
                self.model_splus = pickle.loads(self.model_splus)
                self.model_wise = requests.get("https://splus.cloud/files/models/iDR3n4_RF_12S2W4M")
                self.model_wise = self.model_wise.content
                self.model_wise = pickle.loads(self.model_wise)
        except:
            raise (ValueError)("Unexpected error downloading model from splus.cloud.")

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

    def irsa_query(self, data):
        '''
        Query ALLWISE catalogue from IRSA database.
        Note that this is optimized for querying per fields (i.e., the dataframe input must correspond to a unique field from S-PLUS)

        Keywords arguments:
        data -- dataframe containing information of RA and DEC for each object
        return dataframe containing WISE sources
        '''
        if self.verbose:
            print("Note that irsa_query() is not yet optimized for large data inputs. Please consider running classify() per S-PLUS field if irsa_query()=True.")
        ramin = np.min(data["RA"])
        ramax = np.max(data["RA"])
        decmin = np.min(data["DEC"])
        decmax = np.max(data["DEC"])
        col = ['ra', 'dec', 'w1mpro', 'w2mpro', 'w1snr', 'w2snr', 'w1sigmpro', 'w2sigmpro']
        if ramin < 2 and ramax > 358:
            ramax = np.max(data.query("RA<2").RA)
            ramin = np.min(data.query("RA>358").RA)
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
            if feat in data.columns:
                data.rename(columns={feat: feat + "_" + str(0)}, inplace=True)

        df_wise = df_wise.rename(
            columns={"col_0": col[0], "col_1": col[1], "col_2": col[2],
                     "col_3": col[3], "col_4": col[4], "col_5": col[5],
                     "col_6": col[6], "col_7": col[7]})

        return df_wise

    @staticmethod
    def crossmatch(data, df_wise):
        '''
        Perform cross match between two catalogues based on RA and DEC

        data_ra -- RA from S-PLUS catalogue
        data_dec -- DEC from S-PLUS catalogue
        df_wise_ra -- RA from ALLWISE catalogue
        df_wise_dec -- DEC from ALLWISE catalogue

        returns dataframe containing all original columns from data cross-matched with the ALLWISE query catalogue
        '''

        coo_splus = SkyCoord(data["RA"] * u.deg, data["DEC"] * u.deg)
        coo_wise = SkyCoord(df_wise["ra"] * u.deg, df_wise["dec"] * u.deg)
        idx, d2d, d3d = coo_splus.match_to_catalog_sky(coo_wise)
        data['d2d'] = pd.Series(d2d.arcsec)
        data = pd.concat([data, df_wise.iloc[idx].reset_index()], axis=1)

        return data

    @staticmethod
    def check_columns(data, list_columns):
        try:
            for element in list_columns:
                data[element]
        except ValueError:
            print("Please ensure that ", element,
                      "column is in data. Please provide a ALLWISE cross-matched data or set match_irsa == True. Use model == 'opt' if the provided data do not have any source with WISE counteerpart.")
        return

    def check_match_irsa(self, data,  match_irsa):
        '''
        Check statement of match_irsa and performs cross-match if True
        data -- dataframe containing S-PLUS information
        match_irsa -- If true, query ALLWISE catalogue and performs cross-match. If false, checks if all necessary columns are in data
        '''

        if match_irsa == False:
            self.check_columns(data, self._feat_wise)
            self.check_columns(data, self._error_wise)
        else:
            try:
                for element in self._pos:  # check if RA and DEC are in data to perfom the cross-match
                    data[element]
            except ValueError:
                print("Please ensure that ", element,
                      "column is in data, otherwise the cross-match with ALLWISE cannot be done.")

            if self.verbose:
                print("Querying ALLWISE catalogue via TapPlus(url='https://irsa.ipac.caltech.edu/TAP')...")

            df_wise = self.irsa_query(data)

            if self.verbose:
                print("Starting cross-match...")
            data = self.crossmatch(data, df_wise)
        return data

    def classify(self, df, return_prob=True, match_irsa=False, columns_wise={'w1mpro': 'w1mpro',
                                                                               'w2mpro': 'w2mpro', 'w1snr': 'w1snr',
                                                                               'w2snr': 'w2snr',
                                                                               'w1sigmpro': 'w1sigmpro',
                                                                               'w2sigmpro': 'w2sigmpro'}, verbose=False):

        '''
        Create classifications for sources with or without counterpart

        Keywords arguments:
        data -- dataframe containing information of the 12 S-PLUS ISO magnitudes already extincted corrected
        prob -- if true, estimates the probabilities for each class
        model -- options are "auto", "RF16" or "RF18". If "opt", returns classification from model trained with 12 S-PLUS bands
                 + 4 morphological features. If "RF18", returns classification from model trained with 12 S-PLUS bands + 2 WISE bands+
                 4 morphological features, only for sources with WISE counterpart. If "auto", return classification from the same model as "RF18" (flagged as 0) if
                 the source has WISE counterpart, otherwise returns classification from model "RF16" (flagged as 1).
        match_irsa -- determines if cross-match with ALLWISE catalogue will be performed. If model == "RF16", match_irsa == False.
        returns a dataframe with classes
        '''

        data = df.copy(deep=True)

        self._feat_wise = [columns_wise["w1mpro"], columns_wise["w2mpro"]]
        self._error_wise = [columns_wise["w1snr"], columns_wise["w2snr"],
                            columns_wise["w1sigmpro"], columns_wise["w2sigmpro"]]

        if self.model == "RF16":
            if match_irsa:
                if self.verbose:
                    print("Parameter match_irsa is being set automatically to false.")
                match_irsa = False
        try:
            data.iloc[0,]
        except:
            raise (ValueError)("Data input is empty.")

        for element in self._morph + self._feat:
            try:
                data[element]
            except:
                raise (KeyError)("Please ensure that ", element,
                                 "column is in data. Use splusdata.connect.query() to retrieve it.")

        self.results = pd.DataFrame()

        if verbose:
            print(
                "Note that this function assumes that the input data were previously extinction corrected. Starting classification... ")

        if self.model == "RF16":
            y_pred = pd.DataFrame(self.model_splus.predict(data[self._morph + self._feat]))
            y_pred = y_pred.astype("float64")
            y_pred.index = data.index

            results = y_pred
            results.columns = ["CLASS"]

            if return_prob:
                if verbose:
                    print("Calculating probabilities...")
                prob_df = pd.DataFrame(self.model_splus.predict_proba(data[self._morph + self._feat]))
                prob_df.index = data.index

                results = pd.concat([results, prob_df], axis=1)
                results.columns = ["CLASS", "PROB_QSO", "PROB_STAR", "PROB_GAL"]

        elif self.model == "RF18":
            data = self.check_match_irsa(data, match_irsa)
            data_wise = self.get_wise(data, self._feat_wise + self._error_wise)
            ypred_wise = pd.DataFrame(self.model_wise.predict(
                data_wise[self._morph + self._feat + self._feat_wise]))  # classify sources with WISE
            ypred_wise.index = data_wise.index
            results = ypred_wise
            results.columns = ["CLASS"]

            if return_prob:
                if verbose:
                    print("Calculating probabilities...")

                prob_wise_df = pd.DataFrame(
                    self.model_wise.predict_proba(data_wise[self._morph + self._feat + self._feat_wise]))
                prob_wise_df.index = data_wise.index
                results = pd.concat([results, prob_wise_df], axis=1)
                results.columns = ["CLASS", "PROB_QSO", "PROB_STAR", "PROB_GAL"]

        elif self.model == "auto":
            data = self.check_match_irsa(data, match_irsa)
            data_wise = self.get_wise(data, self._feat_wise + self._error_wise)
            data_nowise = data.drop(data_wise.index)

            y_pred = pd.DataFrame(self.model_splus.predict(data_nowise[self._morph + self._feat]))
            y_pred = y_pred.astype("float64")
            y_pred.index = data_nowise.index
            y_pred["model_flag"] = "1"  # S-PLUS

            ypred_wise = pd.DataFrame(self.model_wise.predict(
                data_wise[self._morph + self._feat + self._feat_wise]))  # classify sources with WISE
            ypred_wise.index = data_wise.index
            ypred_wise["model_flag"] = "0"  # S-PLUS + WISE
            results = pd.concat([y_pred, ypred_wise], axis=0)
            results.columns = ["CLASS", "model_flag"]

            if return_prob:
                if verbose:
                    print("Calculating probabilities...")
                prob_df = pd.DataFrame(self.model_splus.predict_proba(data_nowise[self._morph + self._feat]))
                prob_wise_df = pd.DataFrame(
                    self.model_wise.predict_proba(data_wise[self._morph + self._feat + self._feat_wise]))
                prob_df.index = data_nowise.index
                prob_wise_df.index = data_wise.index
                prob_results = pd.concat([prob_df, prob_wise_df], axis=0)
                results = pd.concat([results, prob_results], axis=1)
                results.columns = ["CLASS", "model_flag", "PROB_QSO", "PROB_STAR", "PROB_GAL"]

        else:
            raise (ValueError)("Parameter 'model' should be 'RF16', 'RF18' or 'auto'.")

        if verbose:
            print("Finished process.")

        return results.sort_index(axis=0)