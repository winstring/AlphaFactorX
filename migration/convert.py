#!/usr/local/anaconda3/bin/python
## Tool to convert old factor modules to ones compatible to the new factor development framework
## 2020/12/28 by gqy

import os
import re
import json
import argparse

def convert(facname, from_path, to_path):
    '''convert old factor script to the new version
    Params:
        facname: string, factor name
        from_path: string, root path of the old framework
        to_path: string, root path of the new framework
    Returns:
        new_py: string, converted script
    '''
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

    return new_py


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert factor(s) to new version.')
    parser.add_argument(
        '-from_dir', dest='from_dir', type=str, default='', help='from dir'
    )
    parser.add_argument(
        '-to_dir', dest='to_dir', type=str, default='', help='to dir'
    )
    parser.add_argument(
        '-f', dest='fac_file', type=str, default=None, help='file contains list of factors'
    )
    parser.add_argument(
        'fac_name', nargs='*', default=None, help='factor name(s)'
    )
    args = parser.parse_args()

    fac_names = []
    if args.fac_name is not None:
        fac_names.extend(args.fac_name)

    if args.fac_file is not None:
        with open(os.path.abspath(args.fac_file), 'r') as f:
            fac_names.extend([fac.strip() for fac in f])

    if len(fac_names) < 1:
        print('Please provide at least one factor name!!!')
        exit

    for factor_name in fac_names:
        _ = convert(factor_name, args.from_dir, args.to_dir)

