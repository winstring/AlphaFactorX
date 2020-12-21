#!/usr/local/anaconda3/bin/python

# -*- coding: utf-8 -*-
# last updated on 2020/12/13 - reconstruct

import os
import argparse

import sys
prj_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, prj_path)

from framework.utils import ringwx
from framework.config import conf
from framework.bench import FactorComputerChecker



parser = argparse.ArgumentParser(description='Compute factor values and scores.')
parser.add_argument(
    '-s', dest='start_date', type=str, default='20180101',
    help='start date (default: 20180101)'
)
parser.add_argument(
    '-n', dest='nproc', type=int, default=8,
    help='number of cores to use for computation (default: 8)'
)
parser.add_argument(
    '-t', dest='tr_minute', type=str, default=None,
    help='transaction time, e.g. 0935, 1000, 1300... (default: None, use default keyword mapping)'
)
parser.add_argument(
    '-f', dest='factor_file', type=str, default=None,
    help='path to file which containing lines of factor names (default: None)'
)
parser.add_argument(
    '-o', dest='result_csv', type=str, default=conf.get('default_result_csv', '/tmp/result.csv'),
    help=f'path to csv file to write results. works with -f only. (default: {conf.get("default_result_csv", "/tmp/result.csv")})'
)
parser.add_argument(
    '-i', nargs='+', default=[],
    help='factor name(s) to compute and check (default: [])'
)
parser.add_argument(
    'factor_name', nargs='*', default=[],
    help='factor name(s) to compute and check (default: [])'
)
args = parser.parse_args()

fcc = FactorComputerChecker(
    start_date=args.start_date,
    tr_minute=args.tr_minute,
    nproc=args.nproc
)

if args.factor_file is not None:
    with open(os.path.abspath(args.factor_file), 'r') as f:
        factor_list = [fac.strip() for fac in f]
    result = fcc.main_mp(factor_list)
    result.to_csv(os.path.abspath(args.result_csv))
    _ = ringwx('Done computing factor values and scores (g).')

if (len(args.factor_name)>0) or (len(args.i)>0):
    factor_names = list(set(args.factor_name).union(set(args.i)))
    for factor_name in factor_names:
        _ = fcc.main(factor_name)

