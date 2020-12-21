# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd

from framework.core import AlphaFactorX


class KH_Demo(AlphaFactorX):
    '''A sample
    {"def_arg": ["MinuteHigh", "MinuteLow"], "prelength": 0, "min_prelen": 0, "type": "hf"}
    '''
    def set_param(self):
        params = {'prelength': 0, 'min_prelen': 0}
        return params

    def definition(self, MinuteHigh, MinuteLow):
        df = self.minute_help()
        df[np.isinf(df)] = np.nan
        return df

    def minute(self, MinuteLow, MinuteHigh):
        high = MinuteHigh.sort_index(ascending=True)
        low = MinuteLow.sort_index(ascending=True)
        res = high.std(axis=0) / low.std(axis=0) * (high.corrwith(low))
        return res

