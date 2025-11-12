
import os
import sys
from datetime import datetime
import logging as logger
from tradelib_global_constants import ROOT_DIR, output_dir_folder

import warnings
warnings.filterwarnings("ignore", message=".*The 'nopython' keyword.*")

# # Create a logger object
# # logger = logging.getLogger(__name__)

# # Set the log level
# if params['DEBUG'] == 1:
#     logger.setLevel(logging.DEBUG)
# else:
#     logger.setLevel(logging.WARNING)


# # Create a file handler
# dt_now = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
# # TODO: need to change the output file when gets bigger
# handler = logging.FileHandler(f'log/hft_{dt_now}.log')

# # Create a formatter
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# # Add the formatter to the handler
# handler.setFormatter(formatter)

# # Add the handler to the logger
# logger.addHandler(handler)

# # # Generate log messages
# # logger.debug('Debug message')
# # logger.info('Info message')
# # logger.warning('Warning message')
# # logger.error('Error message')
# # logger.critical('Critical message')

# def get_hft_logger(module_name:str):
#     return logger

def get_exception_line_no():
    
    _,_, exception_traceback = sys.exc_info()
    line_number = exception_traceback.tb_lineno
    
    return line_number


LOG_FILE_PATH = os.path.join(output_dir_folder, 'log')


def change_log_file_handler(val=""):
    dt_now = datetime.now().strftime('%Y%m%d%H%M%S%f')
    
    if val != '':
        LOG_FILE = f"htf_{dt_now}_{val}.log"
    else:
        LOG_FILE = f"hft_{dt_now}.log"
    
    os.makedirs(LOG_FILE_PATH, exist_ok= True)

    logs_path = os.path.join(LOG_FILE_PATH,LOG_FILE)

    file_handler = logger.FileHandler(logs_path)
    formatter = logger.Formatter("[ %(asctime)s ] %(lineno)d %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.getLogger().addHandler(file_handler)

    for handler in logger.getLogger().handlers:
        logger.getLogger().removeHandler(handler)

    file_handler.close()


def init_logger():
    dt_now = datetime.now().strftime('%Y%m%d%H%M%S%f')
    LOG_FILE = f"hft_{dt_now}.log"

    logs_path = os.path.join(LOG_FILE_PATH,LOG_FILE)

    # # TODO: need to change the output file when gets bigger
    os.makedirs(LOG_FILE_PATH, exist_ok= True)

    logger.basicConfig(
        filename=logs_path,
        format = "[ %(asctime)s ] %(lineno)d %(name)s - %(levelname)s - %(message)s",
    )

    if True:
        logger.getLogger().setLevel(logger.DEBUG)
    else:
        logger.getLogger().setLevel(logger.INFO)

    if False:
        # TODO: need to find a better way to disable
        logger.disable(2000)

    return logger


# invoke the logger
logger = init_logger()
