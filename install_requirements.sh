#!/bin/bash

echo [$(date)]: '======== START ========'
echo [$(date)]: 'Creating env with python 3.8'
python -m venv eis-global-env

echo [$(date)]: 'Activating virtual env ...'
source eis-global-env/bin/activate

echo [$(date)]: 'Installing Libraries (this may take some time)'
pip install -r final_libs.txt

# Install Ta-Lib
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
rm ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make

echo [$(date)]: 'Please ENTER your PASSWORD to install ta-lib'
sudo make install



echo [$(date)]: '======== COMPLETED ========'