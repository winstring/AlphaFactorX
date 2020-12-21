#!/usr/local/anaconda3/bin/python
## Tool to revert factor modules to ones compatible to old factor development framework
## 2020/12/18 by gqy

import sys
import re
import json


def revert(facname, from_path, to_path):
    hfs = ['KD', 'KH', 'KJ', 'KL']
    if not any([facname.startswith(i) for i in hfs]):
        factype = 'KFC'
    else:
        factype = facname.split('_')[0]

    with open(f'{from_path}{facname}.py', 'r') as f:
        py = f.read()
    
    rpl = rf'import sys\nsys.path.insert(0, "{to_path}AlphaFramework/DataPreprocessor/")\n'
    if factype == 'KFC':
        rpl = rpl + 'from AlphaFactor import *'
    else:
        rpl = rpl + 'from HFactor import *'
    py = re.sub(r'from framework.core import AlphaFactorX', rpl, py)

    if factype == 'KFC':
        py = re.sub(r'AlphaFactorX', r'AlphaFactor', py)
    else:
        py = re.sub(r'AlphaFactorX', r'HFactor', py)

    py = re.sub(r'\s+def set_p.+?return params\n\n', '', py, flags=re.S)

    minute_params = re.findall(r'def minute\((.*)\)', py)[0]
    minute_params = [p.strip() for p in minute_params.split(',')]
    minute_params.insert(1, rf'"{facname}Help"')
    help_params = ', '.join(minute_params[1:])
    py = re.sub(r'minute_help\(\)', rf'minute_help(self.minute, {help_params})', py)

    js = re.findall(r'\{.*def_arg.+\}', py)[0]
    js = eval(js)

    if factype == 'KFC':
        py_loc = f'{to_path}AlphaFramework/FactorManagement/daily/compute_script/{facname}.py'
        js_loc = f'{to_path}AlphaFramework/FactorManagement/daily/parameter_json/{facname}.json'
    else:
        py_loc = f'{to_path}AlphaFramework/FactorManagement/hf/{factype}/compute_script/{facname}.py'
        js_loc = f'{to_path}AlphaFramework/FactorManagement/hf/{factype}/parameter_json/{facname}.json'

    with open(py_loc, 'w') as f:
        f.write(py)

    with open(js_loc, 'w') as f:
        json.dump(js, f)

    return


if __name__ == '__main__':
    factor_names = sys.argv[1:]
    from_path = ''
    to_path = ''

    if len(factor_names) == 0:
        print('Please provide at least one factor name!!!')
        exit

    for factor_name in factor_names:
        revert(factor_name, from_path, to_path)

