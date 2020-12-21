# -*- coding: utf-8 -*-

# on 2020-12-11: rewrite of former factor framework, which is unmaintainable and slow.

import os
from datetime import datetime
import inspect
import re

import pandas as pd
import numpy as np

from framework.config import conf


class AlphaFactorX(object):
    '''Core component of alpha factor development framework. Base class for factor modules to inherit.
    Params:
        start_date: str, start date to have a value.

    Returns:
        pandas.DataFrame, factor values
    '''
    def __init__(self, start_date='20180101'):
        params = self.set_param()
        self.prelen_ = params.get('prelength', 0)
        self.mprelen_ = params.get('min_prelen', 0)
        self.fac_type_ = self.get_factype()
        self.hf_map_ = {'KD': '0934', 'KH': '0959', 'KJ': '1129', 'KL': '1449', 'KFC': '1500'}


        assert isinstance(self.prelen_, int) and (self.prelen_>=0), 'prelength should be int and ge 0!!!'
        assert isinstance(self.mprelen_, int) and (self.mprelen_>=0), 'min_prelen should be int and ge 0!!!'
        assert start_date > '20150101', 'start_date earlier than default earliest date!!!'

        self.daily_data_path_ = conf.get('daily_data_path', '')
        self.minute_data_path_ = conf.get('minute_data_path', '')

        adjfactor = pd.read_pickle(self.daily_data_path_+'adjfactor.pkl').loc[pd.Timestamp('20150101'):]
        self.start_date_ = pd.Timestamp(start_date)
        if self.prelen_+self.mprelen_ > 0:
            start_date_pre = self.start_date_ - pd.Timedelta('1 day')
            start_date_pre = adjfactor.loc[:start_date_pre].index[-1]
            self.start_date_pre_ = adjfactor.loc[:start_date_pre].index[-self.prelen_-self.mprelen_]
        else:
            self.start_date_pre_ = self.start_date_
        self.adj_ = adjfactor.loc[self.start_date_pre_:]
        self.date_list_ = self.adj_.index[self.mprelen_:].strftime(r'%Y%m%d').tolist()

        self.minute_data_map_ = {'Minute'+m: m for m in ['High', 'Low', 'Open', 'Close', 'Turnover', 'Volume']}
        self.minute_data_map_.update({'MinuteTurnover': 'Amount'})


    def get_factype(self):
        factor_name = self.__class__.__name__
        hfs = ['KD', 'KH', 'KJ', 'KL']
        if not any([factor_name.startswith(i) for i in hfs]):
            factype = 'KFC'
        else:
            factype = factor_name.split('_')[0]

        return factype


    def get_vars_unused(self, func):
        varnames = inspect.getfullargspec(func).args[1:] # exclude self
        code_lines = [l.strip() for l in inspect.getsourcelines(func)[0] if not l.strip().startswith('#')]
        codes = ' '.join(code_lines)
        unused = [var for var in varnames if len(re.findall(rf'\b{var}\b', codes)) < 2]

        return varnames, unused

    
    def minute_help(self):
        varnames, unused = self.get_vars_unused(self.minute)

        daily_data = {}
        for d in varnames:
            if (d in unused) or ('Minute' in d):
                continue

            if d == 'adjfactor':
                daily_data[d] = self.adj_
                continue

            if self.fac_type_ == 'KFC':
                daily_data[d] = pd.read_pickle(self.daily_data_path_+d+'.pkl').loc[self.start_date_pre_:]
            else:
                daily_data[d] = pd.read_pickle(self.daily_data_path_+d+'.pkl').shift(1).loc[self.start_date_pre_:]
        
        factors = {}
        for date in self.date_list_:
            compute_dates = self.adj_.loc[:date].index[-self.mprelen_-1:]

            compute_data = {}
            for d in varnames:
                if d in unused:
                    compute_data[d] = None
                    continue

                if 'Minute' not in d:
                    compute_data[d] = daily_data[d].loc[compute_dates]
                    continue

                compute_data[d] = pd.DataFrame()
                if self.mprelen_ > 0:
                    for compute_date in compute_dates[:-1]:
                        tmp = pd.read_pickle(self.minute_data_path_+self.minute_data_map_[d]+'/'+compute_date.strftime(r'%Y%m%d')+'.pkl')
                        compute_data[d] = compute_data[d].append(tmp)
                else:
                    pass
                tmp = pd.read_pickle(self.minute_data_path_+self.minute_data_map_[d]+'/'+date+'.pkl').loc[:date+self.hf_map_[self.fac_type_]]
                compute_data[d] = compute_data[d].append(tmp)

            factors[pd.Timestamp(date)] = self.minute(*[compute_data[var] for var in varnames])

        factors = pd.DataFrame(factors).T

        return factors


    def calculate(self):
        varnames, unused = self.get_vars_unused(self.definition)

        compute_data = {}
        for d in varnames:
            if (d in unused) or ('Minute' in d):
                compute_data[d] = None
                continue

            if d == 'adjfactor':
                compute_data[d] = self.adj_
                continue

            if self.fac_type_ == 'KFC':
                compute_data[d] = pd.read_pickle(self.daily_data_path_+d+'.pkl').loc[self.start_date_pre_:]
            else:
                compute_data[d] = pd.read_pickle(self.daily_data_path_+d+'.pkl').shift(1).loc[self.start_date_pre_:]
        
        result = self.definition(*[compute_data[var] for var in varnames])

        return result.loc[self.start_date_:]


    def set_param(self):
        raise NotImplementedError


    def definition(self):
        raise NotImplementedError

            
    def minute(self):
        raise NotImplementedError

