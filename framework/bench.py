# -*- coding: utf-8 -*-

# on 2020/11/25 - enable changing transaction time for hf factors

import os
import sys
import time
import importlib
import warnings

import numpy as np
import pandas as pd
import multiprocessing as mp
from tqdm import tqdm

from framework.config import conf
from framework.utils import (ttest_positive_sided, ttest_negative_sided, check_prediction)

warnings.filterwarnings("ignore", category=RuntimeWarning)
abs_path = os.path.dirname(os.path.abspath(__file__))
prj_path = abs_path[:-9] # parent folder of framework subfolder


class FactorComputerChecker(object):
    '''Compute and check hf and close factors
    Params:
        start_date: str, start date, default '20180101'
        tr_minute: transaction minute of hf factor, mapped to hf type by default
        nproc: int, number of cores used for computation when a file with tens of factor names is provided, default 8

    Returns:
        factor values, scores and specifications.
    '''
    def __init__(self, start_date='20180101', tr_minute=None, nproc=8):
        self.start_date_ = start_date
        self.tr_minute_ = tr_minute
        self.nproc_ = nproc
        self.time_map_ = {"KD": "0935", "KH": "1000", "KJ": "1300", "KL": "1450", "KFC": "1500"}


    def compute_factor_value(self, factor_name):
        tic = time.perf_counter()
        mod = importlib.import_module(conf.get('factor_script_dir', 'factor_script')+'.'+factor_name)
        obj = getattr(mod, factor_name)(start_date=self.start_date_)

        hfs = ['KD', 'KH', 'KJ', 'KL']
        if not any([factor_name.startswith(i) for i in hfs]):
            self.catalog_type_ = 'KFC'
            self.transaction_time_ = '1500'
        else:
            self.catalog_type_ = factor_name.split('_')[0]

            if not self.tr_minute_:
                self.transaction_time_ = self.time_map_[self.catalog_type_]
            else:
                self.transaction_time_ = self.tr_minute_
                map_time = pd.Timestamp(f'20200202 {self.transaction_time_}') - pd.Timedelta('1 minute')
                obj.hf_map_.update({self.catalog_type_: map_time.strftime(r'%H%M')})
        
        print(f'@@@@ Begin to compute the {self.catalog_type_} factor {factor_name}\n')
        factor_df = obj.calculate()
        if self.catalog_type_ == 'KFC':
            factor_df.loc[pd.Timestamp('20200203')] = np.nan
        else:
            factor_df.loc[pd.Timestamp('20200203'):pd.Timestamp('20200204')] = np.nan

        factor_df.to_pickle(prj_path+conf.get('factor_value_dir', 'factor_values')+'/'+factor_name+'.pkl')
        toc = time.perf_counter()
        print(f"#### Factor Computing Time: {toc-tic:0.2f} seconds.")

        return factor_df
        

    def compute_factor_score(self, factor_name):
        # cal factor values
        factor_df = self.compute_factor_value(factor_name)
        nan_ratio = np.round(factor_df.isna().mean(axis=1).mean(), 4)
        print(f'#### p(nan): {nan_ratio:.2%}\n')

        factor_unique_count = factor_df.apply(lambda x: len(pd.Series.unique(x)), axis=1).mean()
        factor_mode_count = factor_df.apply(lambda x: x.value_counts(sort=False).max(), axis=1, raw=False).mean()
        if (factor_unique_count<=200):
            print('warning: factor values not discriminative!\n')
        if (factor_mode_count>=300):
            print('warning: too many stocks have same values!\n')
        discrim = (factor_unique_count>200) and (factor_mode_count<300)

        # cal score
        if self.catalog_type_ == 'KFC':
            py_path = prj_path+conf.get('factor_script_dir', 'factor_script')+'/'+factor_name+'.py'
            score = check_prediction(
                factor_df.shift(2),
                act_type='close',
                buy_price='vwap',
                filter_close_fac=py_path,
                group_number=20
            )
        else:
            score = check_prediction(
                factor_df.shift(1),
                act_type='minute',
                transaction_time=self.transaction_time_,
                group_number=20
            )

        score.to_pickle(prj_path+conf.get('factor_excess_dir', 'factor_excess')+'/'+factor_name+'_excess.pkl')

        return score, discrim, nan_ratio


    def score_eval(self, factor_name, score, discrim, nan_ratio):
        specs = pd.Series(
            data={
                'global_top_p': np.nan,
                'global_top_exc': np.nan,
                'half_top_p': np.nan,
                'half_top_exc': np.nan,
                'max_corr_name': np.nan,
                'max_corr': np.nan,
                'TEST-0': discrim,
                'TEST-1': False,
                'TEST-2': False,
                'TEST-3': False,
                'p(nan)': nan_ratio
            },
            name=factor_name
        )

        whole_top_loc = score.mean().idxmax()
        whole_bottom_loc = score.mean().idxmin()
        
        mid = pd.Timestamp('20190630')
        score_first_half = score.loc[:mid]
        score_second_half = score.loc[mid:]
        first_half_top_loc = score_first_half.mean().idxmax()
        first_half_bottom_loc = score_first_half.mean().idxmin()

        con1 = abs(whole_top_loc - whole_bottom_loc) >= 2
        con2 = abs(first_half_top_loc - first_half_bottom_loc) >= 2

        print('####### TEST-1. locations of top and bottom groups #######')
        print(f'global top: {whole_top_loc}')
        print(f'global bottom: {whole_bottom_loc}')
        print(f'first-half top: {first_half_top_loc}')
        print(f'first-half bottom: {first_half_bottom_loc}')
        if not (con1 and con2):
            print('TEST-1 failed! diff between locations of top and bottom groups larger than 2!!!\n')
        else:
            print('TEST-1 passed.\n')
            specs.loc['TEST-1'] = True

        whole_top_series = score[whole_top_loc]
        whole_bottom_series = score[whole_bottom_loc]
        second_half_top_series = score_second_half[first_half_top_loc]
        second_half_bottom_series = score_second_half[first_half_bottom_loc]   
        
        if self.catalog_type_ in ['KD', 'KH']:
            min_ret = 0
        else:
            min_ret = 0.01

        p_whole_top = ttest_positive_sided(whole_top_series, min_ret)
        p_whole_bottom = ttest_negative_sided(whole_bottom_series, -min_ret)
        p_second_top = ttest_positive_sided(second_half_top_series, min_ret)
        p_second_bottom = ttest_negative_sided(second_half_bottom_series, -min_ret)

        if self.catalog_type_ == 'KD':
            max_p = 0.1
        else:
            max_p = 0.05

        con3 = p_whole_top <= max_p
        con4 = p_whole_bottom <= max_p
        con5 = p_second_top <= max_p
        con6 = p_second_bottom <= max_p

        print('####### TEST-2. t-test on ret series of top and bottom groups #######')
        print(f'p-value of global top group rets: {p_whole_top:0.4f}, excess return mean: {whole_top_series.mean():0.4f}')
        print(f'p-value of global bottom group rets: {p_whole_bottom:0.4f}, excess return mean: {whole_bottom_series.mean():0.4f}')
        print(f'p-value of second-half top group rets: {p_second_top:0.4f}, excess return mean: {second_half_top_series.mean():0.4f}')
        print(f'p-value of second-half bottom group rets: {p_second_bottom:0.4f}, excess return mean: {second_half_bottom_series.mean():0.4f}')

        specs.loc['global_top_p'] = np.round(p_whole_top, 4)
        specs.loc['global_top_exc'] = np.round(whole_top_series.mean(), 4)
        specs.loc['half_top_p'] = np.round(p_second_top, 4)
        specs.loc['half_top_exc'] = np.round(second_half_top_series.mean(), 4)

        if not (con3 and con4 and con5 and con6):
            print(f'TEST-2 failed! one or more p-values larger than {max_p:0.2f}!!!\n')
        else:
            print('TEST-2 passed.\n')
            specs.loc['TEST-2'] = True
        

        print('####### TEST-3. max correlation of top return series #######')
        try:
            valid_facs = pd.read_pickle(conf.get('valid_factors_file', None)).loc[self.transaction_time_].index
            if self.catalog_type_ == 'KFC':
                fac_all = pd.read_pickle(conf.get('all_kfc_excess_file', None))[valid_facs]
            else:
                fac_all = pd.read_pickle(conf.get('all_hf_excess_file', None))[self.transaction_time_][valid_facs]

            fac_top_group = fac_all.groupby(level=0, axis=0).mean().apply(pd.Series.idxmax)

            fac_top_rets = fac_all.apply(lambda x: x[fac_top_group[x.name]])

            corr_top = fac_top_rets.corrwith(whole_top_series).sort_values(ascending=False) # no abs

            print(f'max corr. info: {corr_top.index[0]}, {corr_top.iloc[0]:0.4f}')

            specs.loc['max_corr_name'] = corr_top.index[0]
            specs.loc['max_corr'] = np.round(corr_top.iloc[0], 4)

            if (corr_top.iloc[0] >= 0.7):
                print('TEST-3 failed! max correlation exceeded 0.7!!!\n')
            else:
                print('TEST-3 passed.\n')
                specs.loc['TEST-3'] = True
        except KeyError:
            print('Warning: correlation check skipped because irregular transaction time used.\n')

        print(f'@@@ Excess Return Mean: {whole_top_series.mean():0.4f}\n')

        return specs


    def main(self, factor_name):
        score, discrim, nan_ratio = self.compute_factor_score(factor_name)
        specs = self.score_eval(factor_name, score, discrim, nan_ratio)

        return specs


    def main_mp(self, factor_list):
        '''multiprocessing, stdout replaced by progress bar'''
        old_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')
        try:
            rs = []
            with mp.Pool(processes=self.nproc_) as p:
                for r in tqdm(p.imap_unordered(self.main, factor_list), total=len(factor_list)):
                    rs.append(r)
        finally:
            sys.stdout.close()
            sys.stdout = old_stdout

        result = pd.concat(rs, axis=1).T.sort_index(axis=0)

        return result

