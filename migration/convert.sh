#!/bin/bash
## convert old factor modules to ones that compatible to this framework

# change import
for py in $(ls ${1}/*.py)
do
    cat ${py} | tr '\n' '\r' | sed -e 's/import sys\rsys.*\rfrom.*\*\r/\rfrom framework.core import AlphaFactorX\r/' | tr '\r' '\n' > ${py}.bak
done

# change inheritance
sed -i 's/(HFactor)/(AlphaFactorX)/' factor_script/*.py.bak # HF
sed -i 's/(AlphaFactor)/(AlphaFactorX)/' factor_script/*.py.bak # KFC

# empty minute_help
sed -i 's/minute_help(.*)/minute_help()/' factor_script/*.py.bak

# add set_param method
sed -i '/def definition/e cat add_init.txt' factor_script/*.py.bak

# replace origin
for py in $(ls ${1}/*.py)
do
    mv ${py}.bak ${py}
done
