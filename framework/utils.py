# -*- coding: utf-8 -*-

import os
import numpy as np
import pandas as pd
from scipy import stats

from framework.config import conf


def ringwx(text, desp=''):
    import requests
    res = requests.post(
        conf.get('serverchan_addr', ''),
        data={'text': text, 'desp': desp}
        )

    return res.status_code


def ttest_positive_sided(s, m):
    (t, p) = stats.ttest_1samp(s, m, nan_policy='omit')
    
    if t>0:
        oneside_p = p/2
    else:
        oneside_p = 1 - p/2

    return oneside_p


def ttest_negative_sided(s, m):
    (t, p) = stats.ttest_1samp(s, m, nan_policy='omit')

    if t<0:
        oneside_p = p/2
    else:
        oneside_p = 1- p/2

    return oneside_p


def check_prediction(activation, act_type='close', buy_price='vwap', transaction_time='1500', filter_close_fac=None, group_number=20):
    '''
    activation:
        输入pd.DataFrame:factor_value => close因子，factor_value需要在输入时shift(2)
        输入pd.DataFrame:factor_value => minute因子，factor_value需要在输入时shift(1)
    act_type:
        输入'close' => activation type
        输入'minute' => activation type
    buy_price:
        close因子 => vwap / first_10m_vwap / pm_vwap -- 全天vwap / 上午前10分钟vwap / 全天vwap
        minute因子 => vwap -- 分钟vwap
    transaction_time:
        close因子 => 默认，'1500'
        minute因子 => 买入时间，格式如'0936'
    filter_close_fac:
        bool or string, 是否用分钟valid信息筛close因子; 亦可提供close因子py文件路径通过文件内容自动判定
    group_number:
        分组数，默认分20组
    '''
    # assertion
    assert act_type in ['close', 'minute'], 'wrong act_type'
    assert buy_price in ['vwap', 'first_10m_vwap', 'pm_vwap'] if act_type=='close' else buy_price == 'vwap'
    assert len(transaction_time) == 4 if act_type == 'minute' else True
    assert transaction_time[:2] in ['09', '10', '11', '13', '14'] if act_type == 'minute' else transaction_time == '1500'
    assert int(transaction_time[2:]) >= 0 and int(transaction_time[2:]) < 60
    assert (int(transaction_time) >= 930 and int(transaction_time) < 1130) or (int(transaction_time) >= 1300 and int(transaction_time) < 1500) if act_type == 'minute' else True
    # assert span > 0 and isinstance(span, int)
    assert group_number > 0 and isinstance(group_number, int), 'wrong group_number'
    
    act = activation.copy().astype(np.float64)
    
    basic_daily_path  = conf.get('daily_data_path', '')
    basic_minute_path = conf.get('minute_data_path', '')
    adjfactor = pd.read_pickle(basic_daily_path + 'adjfactor.pkl').loc[pd.Timestamp('20160101'):]
    
    assert len(set(act.index).difference(adjfactor.iloc[1:].index))==0, "please enter prediction dates between %s and %s" %(adjfactor.index[1], adjfactor.index[-1])
    
    '''    收益部分    '''
    # Generatge date_list for trade_price
    idx_start = adjfactor.index.tolist().index(act.index[0]) - 1
    idx_end = adjfactor.index.tolist().index(act.index[-1]) + 1
    date_index = adjfactor.iloc[idx_start:idx_end].index
    date_list = sorted(date_index.strftime(r'%Y%m%d').tolist())
    adjfactor = adjfactor.loc[date_index]
    
    is_valid_raw = pd.read_pickle(basic_daily_path + 'is_valid_raw.pkl').loc[date_index]
    vwap = pd.read_pickle(basic_daily_path+'vwap.pkl').loc[date_index]
    pre_close = pd.read_pickle(basic_daily_path+'pre_close.pkl').loc[date_index]
    stocks_cyb = [col for col in adjfactor.columns if col.startswith('3')]
    
    if act_type == 'close':
        if buy_price == 'vwap': # buy_price为全天vwap
            ret = (vwap * adjfactor).pct_change(1) * 100
            pct_change_buy_day = (vwap / pre_close - 1.).shift(1).abs()
            
        elif buy_price == 'first_10m_vwap':
            vwap10 = pd.DataFrame(np.nan, index=date_index, columns=adjfactor.columns)
            for date in date_list:
                minute_amt = pd.read_pickle(basic_minute_path + 'Amount/' + date + '.pkl').iloc[:10].sum()
                minute_vol = pd.read_pickle(basic_minute_path + 'Volume/' + date + '.pkl').iloc[:10].sum()
                vwap10.loc[date] = minute_amt / minute_vol
            
            vwap10[np.isinf(vwap10)] = np.nan
            ret = ((vwap * adjfactor) / (vwap10 * adjfactor).shift(1) - 1) * 100
            pct_change_buy_day = (vwap10 / pre_close - 1.).shift(1).abs()
        elif buy_price == 'pm_vwap':
            vwap_pm = pd.DataFrame(np.nan, index=date_index, columns=adjfactor.columns)
            for date in date_list:
                minute_amt = pd.read_pickle(basic_minute_path + 'Amount/' + date + '.pkl').loc[date+'1300':date+'1456'].sum()
                minute_vol = pd.read_pickle(basic_minute_path + 'Volume/' + date + '.pkl').loc[date+'1300':date+'1456'].sum()
                vwap_pm.loc[date] = minute_amt / minute_vol
            vwap_pm[np.isinf(vwap_pm)] = np.nan
            
            # ret = (vwap_pm * adjfactor).pct_change(1) * 100
            ret = ((vwap * adjfactor) / (vwap_pm * adjfactor).shift(1) - 1.) * 100
            pct_change_buy_day = (vwap_pm / pre_close - 1.).shift(1).abs()
        
    else:
        vwapn = pd.DataFrame(np.nan, index=date_index, columns=adjfactor.columns)
        for date in date_list:
            minute_amt = pd.read_pickle(basic_minute_path + 'Amount/' + date + '.pkl').loc[pd.Timestamp(date+transaction_time+'00')]
            minute_vol = pd.read_pickle(basic_minute_path + 'Volume/' + date + '.pkl').loc[pd.Timestamp(date+transaction_time+'00')]
            vwapn.loc[date] = minute_amt / minute_vol
            
        vwapn[np.isinf(vwapn)] = np.nan
        
        ret = ((vwap * adjfactor) / (vwapn * adjfactor).shift(1) - 1) * 100
        pct_change_buy_day = (vwapn / pre_close - 1.).shift(1).abs()
        
    nomaxupordown = pct_change_buy_day.lt(.098)
    if date_list[-1] >= '20200824':
        nomaxupordown.loc[pd.to_datetime('20200824'):, stocks_cyb] = pct_change_buy_day.loc[pd.to_datetime('20200824'):, stocks_cyb].lt(.198)

    valid = (is_valid_raw.shift(1)==1) & (is_valid_raw==1) & (nomaxupordown) & (~np.isnan(ret)) & (~np.isinf(ret))
    valid_ret = pd.DataFrame(False, index=valid.index, columns=valid.columns)
    valid_ret[ret.lt(33.) & ret.gt(-25.)] = True # 涨: 1.1*1.1/0.9-1=34.44% 跌: 0.9*0.9/1.1-1=-26.36%
    if date_list[-1] >= '20200824':
        valid_ret_cyb = valid_ret.loc[pd.Timestamp('20200824'):, stocks_cyb].copy()
        ret_cyb = ret.loc[pd.Timestamp('20200824'):, stocks_cyb].copy()
        valid_ret_cyb[ret_cyb.lt(78.) & ret_cyb.gt(-45.)] = True # 涨: 1.2*1.2/0.8-1=80.00% 跌: 0.8*0.8/1.2-1=-46.67%
        valid_ret.loc[pd.Timestamp('20200824'):, stocks_cyb] = valid_ret_cyb
    valid = valid & valid_ret
    ret = ret[valid].iloc[1:]
    ret = ret.sub(ret.mean(axis=1), axis=0)
    
    if act_type == 'close':
        if isinstance(filter_close_fac, str) and os.path.exists(filter_close_fac):
            with open(filter_close_fac) as f:
                tt = f.readlines()
            minute_flag = False
            for line in tt:
                if ('def definition(self' in line) or ('def definition(sef' in line):
                    if 'Minute' in line:
                        minute_flag = True
                        break
        elif isinstance(filter_close_fac, bool):
            minute_flag = filter_close_fac
        else:
            raise TypeError('filter_close_fac should be either boolean or correct string path to a .py file')

        if minute_flag:
            valid_noudlmt = pd.read_pickle(conf.get('valid_minute_path', '')+'1500.pkl').shift(2).loc[act.index]
            act = act[valid_noudlmt==True]
        else:
            pass
    else:
        valid_noudlmt = pd.read_pickle(conf.get('valid_minute_path', '')+transaction_time+'.pkl').shift(1).loc[act.index]
        act = act[valid_noudlmt==True]
    
    '''    分组部分    '''    
    act = act.mul(ret.replace(0, 1)).div(ret.replace(0, 1))
    act_rank = act.rank(axis=1, method='first', ascending=False, pct=True)

    score = pd.DataFrame(index=act.index, columns=np.arange(1, group_number+1), data=np.nan)
    for i in range(group_number):
        score[i+1] = ret[act_rank.gt(i/group_number) & act_rank.le((i+1)/group_number)].mean(axis=1)
    
    return score


