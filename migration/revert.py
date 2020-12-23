#!/usr/local/anaconda3/bin/python
## Tool to revert factor modules to ones compatible to old factor development framework
## 2020/12/28 by gqy

import sys
import re
import json


def revert(facname, from_path, to_path):
    '''revert the new factor script to the old version.
    Params:
        facname: string, factor name
        from_path: string, root path of the new framework
        to_path: string, root path of the old framework
    Returns:
        py: string, reverted script
        js: dict, reverted paring json
    '''
    hfs = ['KD', 'KH', 'KJ', 'KL']
    if not any([facname.startswith(i) for i in hfs]):
        factype = 'daily'
        subtype = 'KFC'
        base_class = 'AlphaFactor'
    else:
        factype = 'hf'
        subtype = facname.split('_')[0]
        base_class = 'HFactor'

    with open(f'{from_path}factor_script/{facname}.py', 'r') as f:
        py = f.read()
        
    rpl = rf'import sys\nsys.path.insert(0, "{to_path}AlphaFramework/DataPreprocessor/")\nfrom {base_class} import *'
    py = re.sub(r'from framework.core import AlphaFactorX', rpl, py)
    py = re.sub(r'AlphaFactorX', base_class, py)
    
    data_params = re.findall(r'def definition\((.*)\)', py)[0]
    data_params = [p.strip() for p in data_params.split(',')]
    data_params.remove('self')
    data_params_str = ', '.join(data_params)
            
    py = re.sub(r'\s+def set_p.+?return.*?\n\n', '', py, flags=re.S)
    py = re.sub(r'minute_help\(\)', rf'minute_help(self.minute, "{facname}Help", {data_params_str})', py)
    py = re.sub(r'def minute\(.+\):', rf'def minute(self, {data_params_str}):', py)
    
    js = {'def_arg': data_params}
    dicts = re.findall(r'\{.+\}', py)
    for d in dicts[::-1]:
        d = eval(d)
        v1 = d.get('prelength', None)
        v2 = d.get('min_prelen', None)
        if (v1 is not None) and (v2 is not None):
            js['prelength'] = v1
            js['min_prelen'] = v2
            break
    js['type'] = factype

    if factype == 'daily':
        py_loc = f'{to_path}AlphaFramework/FactorManagement/{factype}/compute_script/{facname}.py'
        js_loc = f'{to_path}AlphaFramework/FactorManagement/{factype}/parameter_json/{facname}.json'
    else:
        py_loc = f'{to_path}AlphaFramework/FactorManagement/{factype}/{subtype}/compute_script/{facname}.py'
        js_loc = f'{to_path}AlphaFramework/FactorManagement/{factype}/{subtype}/parameter_json/{facname}.json'

    with open(py_loc, 'w') as f:
        f.write(py)

    with open(js_loc, 'w') as f:
        json.dump(js, f)

    return py, js


if __name__ == '__main__':
    factor_names = sys.argv[1:]
    from_path = 'path_to_the_new_framework'
    to_path = 'path_to_the_old_framework'

    if len(factor_names) == 0:
        print('Please provide at least one factor name!!!')
        exit

    for factor_name in factor_names:
        _, _ = revert(factor_name, from_path, to_path)
