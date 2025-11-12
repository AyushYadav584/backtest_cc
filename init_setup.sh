echo [$(date)]: 'START'
echo [$(date)]: 'Creating conda env with python 3.9'
conda create --prefix ./eis_env python=3.9 -y
echo [$(date)]: 'activate env'
source activate ./eis_env
echo [$(date)]: 'installing TA-LIB'
conda install -c conda-forge ta-lib -y
echo [$(date)]: 'installing requirements'
pip3 install -r requirements.txt
echo [$(date)]: 'Setup END'

#RUN : bash init_setup.sh
