#!/usr/local/anaconda3/bin/python
## Tool to convert old factor modules to ones compatible to the new factor development framework
## 2020/12/28 by gqy

import sys
import re
import json

def convert(facname, from_path, to_path):
    hfs = ['KD', 'KH', 'KJ', 'KL']
    if not any([facname.startswith(i) for i in hfs]):
        factype = 'KFC'
    else:
        factype = facname.split('_')[0]

    if factype == 'KFC':
        py_loc = f'{from_path}AlphaFramework/FactorManagement/daily/compute_script/{facname}.py'
        js_loc = f'{from_path}AlphaFramework/FactorManagement/daily/parameter_json/{facname}.json'
    else:
        py_loc = f'{from_path}AlphaFramework/FactorManagement/hf/{factype}/compute_script/{facname}.py'
        js_loc = f'{from_path}AlphaFramework/FactorManagement/hf/{factype}/parameter_json/{facname}.json'

    with open(py_loc, 'r') as f:
        py = f.read()

    new_py = re.sub(r'import sys.+?from.+import \*', '\nfrom framework.core import AlphaFactorX', py, flags=re.S)
    new_py = re.sub(r'minute_help\(.+\)', r'minute_help()', new_py)
    new_py = re.sub(rf'{facname}\(.+\)', rf'{facname}(AlphaFactorX)', new_py)

    with open(js_loc, 'r') as f:
        js = json.load(f)
    js = {k: v for k, v in js.items() if k in ['prelength', 'min_prelen']}

    with open(f'{to_path}migration/add_params.txt', 'r') as f:
        to_add = f.read()
    to_add = re.sub(r'params = .+', rf'params = {js}', to_add)

    new_py = re.sub(r'(\s+def definition)', rf'\n{to_add}\1', new_py, flags=re.S)

    with open(f'{to_path}factor_script/{facname}.py', 'w') as f:
        f.write(new_py)    

    return


if __name__ == '__main__':
    factor_names = sys.argv[1:]
    from_path = '/home/gqy/Factor_Factory/'
    to_path = '/home/gqy/facdev/'

    if len(factor_names) == 0:
        print('Please provide at least one factor name!!!')
        exit

    for factor_name in factor_names:
        convert(factor_name, from_path, to_path)

