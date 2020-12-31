# AlphaFactorX

> AlphaFactorX is an alpha factor development framework focusing on simplicity, flexibility and maintainability.

## 1. Features

### 1.1 All-in-one design

Both close factors and minute factors can be developed and tested by inheriting the same base class now. While codes and folder trees have been heavily tailored, there's little to change in developing behavior for factor developers who used to work under old framework.

### 1.2 Boost development of close factors

Now it's 10x faster when compute and check close factors than the old one.

### 1.3 Flexible customizations

Customizable settings like start date and transaction time of minute factors could be applied without altering the codes.

### 1.4 Run in batch

Either a file containing lines of factor names or raw factor name(s) is supported for computation.

## 2. Installation

Clone this project into local workspace and keep the file structrue as it is.

## 3. Factor development

### 3.0 Configuration (required)

Configure `framework/config.py` as needed:

- `daily_data_path`: path to daily data, e.g. `close`, `open`, `high`, `low`, `volume`...
- `minute_data_path`: path to minute data, e.g. `MinuteClose`, `MinuteOpen`, `MinuteHigh`, `MinuteLow`, `MinuteVolume`...
- `valid_minute_path`: path to valid minutes
- `valid_factors_file`: full location of valid factors file
- `all_kfc_excess_file`, `all_hf_excess_file`: excess file of close factors and minute factors, respectively
- `factor_script_dir`: dir to hold factor scripts
- `factor_value_dir`: dir to hold factor value files
- `factor_excess_dir`: dir to hold factor excess files 
- `default_result_csv`:  default path to store `.csv` format result

### 3.1 Write factor module

Factor modules are hosted under folder `factor_script/`, an exemplary module file `factor_script/KH_Demo.py` looks like this:

```python
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
```

For developers who come from old factor development framework, major differences between the new and old factor modules are:

- Module path insertion is replaced by a static import `from framework.core import AlphaFactorX`.
- Corresponding `.json` file is not required any more, key parameters are now defined in function `set_param` for convinience.
- Some redundant parameters are omitted. `type` and `def_arg` are now inferred from factor name and function parameters, respectively.
- Parameters in function `minute_help` are also omitted, since it just acts as a wrapper of `minute` function.
- Corresponding data to parameters defined in function `definition` and `minute` will be loaded seperately and will be automatically skipped if unused, so it's safe if parameters within function `definition` and `minute` are not identical. In the example shown above, parameters `MinuteHigh` and `MinuteLow` in `definition` are unnecessary, certain data will not be loaded during computation, and it won't cause any problem on dismatch of appearance orders of the parameters.

Conversion tools (you may want to backup certain files first since they will be overwritten without warning):

- Use `migration/convert.py` to convert old factor script(s) to new ones. `from_path`(root of old framework) and `to_path` (root of the new framewrok) should be set by editing last block of the file first.
- Use `migration/revert.py` to convert new factor script(s) to old ones, as well as their pairing `.json` files. Also, `from_path`(root of the new framework) and `to_path` (root of the old framewrok) should be set first. And since the new framework requires less parameters and variables than its predecessor, some additional info is required to acquire a sucessful reversion: all required data should defined in function `definition`. In the example above, `MinuteHigh` and `MinuteLow` defined in `definition` is redundant to the new framework, but it's required if someone want to revert to old version factor module.

### 3.2 Compute and check

#### 3.2.1 By factor name(s)

Simply execute `python compute_and_check.py [factor_name_1] [factor_name_2] [factor_name_3] ...` or `python compute_and_check.py -i [factor_name_1] [factor_name_2] [factor_name_3] ...`. Entering the directory where `compute_and_check.py` locates before running the commands is not a must, it can be refrenced and called wherever the current working directory is.

#### 3.2.2 By text file containing factor names

Execute `python compute_and_check.py -f [path_to_text_file]`, this will generate a summary csv file containing factor specifications. Path to the csv file can be specified by adding a `-o` option, or it will try and write to a default location. Change the value of `default_result_csv` within `framework/config.py` to change the defaut csv path if necessary.

#### 3.2.3 Other parameters

- `-s`: start_date to compute factor, use `20180101` by default.
- `-t`: transaction time of minute factors, inferred from the factor type by default, i.e. `KD: 0935, KH: 1000, KJ: 1300, KL: 1450`. To compute `KH_Demo` for a transaction time other than `1000`, e.g. `0955`, execute `python compute_and_check.py -i KH_Demo -t 0955`.

For more configurable parameters, check contents in `framework/config.py` or run `python compute_and_check.py -h`.

### 4. To do

- Although not common, there are chances that about ±0.0002 mismatch is observed between results from the new and the old frameworks. Anyway, the biases are quite limited...and it's not a comfortable experience to read the old codes, so...

## logs

- 2020/12/22: update README
- 2020/12/21: add config.py to simplify configuration
- 2020/12/18: add convert.sh and revert.py for script migration
- 2020/12/16: automatically skip unused data
- 2020/12/13: load daily data once instead of each day when it's in minute function
- 2020/12/12: correct time mapping for minute factors and add altering transaction time support
- 2020/12/11: init project
