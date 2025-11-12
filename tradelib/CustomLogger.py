import os
import sys
from datetime import datetime, date
from logging import Logger, Handler
import logging
from tradelib_global_constants import ROOT_DIR, date_format, DISABLE_DEBUG
from typing import List, Dict

import warnings
warnings.filterwarnings("ignore", message=".*The 'nopython' keyword.*")

PARTIAL_TRADE_MISS = logging.WARNING + 5
logging.addLevelName(PARTIAL_TRADE_MISS, "PARTIAL_TRADE_MISS")
TRADE_MISS = PARTIAL_TRADE_MISS + 5
logging.addLevelName(TRADE_MISS, "TRADE_MISS") 


class CustomLogger(Logger):
    def __init__(self, name: str, enable_debug: bool) -> None:
        self.level = 0
        if enable_debug:
            self.level = (logging.DEBUG)
        else:
            self.level = (logging.INFO)
        super().__init__(name, self.level)
        
    def trade_miss(self, message, *args, **kwargs):
        if self.isEnabledFor(TRADE_MISS):
            self._log(TRADE_MISS, message, args, **kwargs)

    def partial_trade_miss(self, message, *args, **kwargs):
        if self.isEnabledFor(PARTIAL_TRADE_MISS):
            self._log(PARTIAL_TRADE_MISS, message, args, **kwargs)

class CustomLoggerManager:
    def __init__(self, output_dir: str, enable_debug: bool) -> None:
        self.logger_dict: Dict[str, Logger] = {}
        self.enable_debug = enable_debug
        self.output_dir = os.path.join(output_dir, 'log')
        self.handler = None

    def __defaultLogFileHandler(self):
        logfilename = "default.log"
        
        os.makedirs(self.output_dir, exist_ok=True)
        logsfilepath = os.path.join(self.output_dir, logfilename)

        file_handler = logging.FileHandler(logsfilepath, mode='w')
        formatter = logging.Formatter("[ %(asctime)s ] %(lineno)d %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        return file_handler
        
    def __getLoggerFileHandler(self, date: date):
        logfilename = f"{date.strftime(date_format)}.log"
        
        os.makedirs(self.output_dir, exist_ok=True)
        logsfilepath = os.path.join(self.output_dir, logfilename)

        file_handler = logging.FileHandler(logsfilepath, mode='w')
        formatter = logging.Formatter("[ %(asctime)s ] %(lineno)d %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        return file_handler
    
    def getLogger(self, name) -> CustomLogger:
        if name in self.logger_dict:
            return self.logger_dict[name]
        else:
            self.logger_dict[name] = CustomLogger(name, self.enable_debug)
            self.logger_dict[name].addHandler(self.__defaultLogFileHandler() if self.handler == None else self.handler)
            return self.logger_dict[name]

    def setLogFile(self, date):
        self.handler = self.__getLoggerFileHandler(date)
        handlers: List[Handler] = []
        for name, logger in self.logger_dict.items():
            if logger.hasHandlers():
                for handler in logger.handlers:
                    logger.removeHandler(handler)
                    handlers.append(handler)
            logger.addHandler(self.handler)

        for handler in handlers:
            handler.close()




# output_dir = os.path.join(ROOT_DIR, "log_test")
# logger_manager = CustomLoggerManager(output_dir, True)
# logger_manager.setLogFile(date(2022, 1, 1))
# log1 = logger_manager.getLogger("chill")
# log1.info("hi")
# log1.info("2")

# print(lg1.handlers)
# lg2 = logger.getLogger("Hi2")
# lg1.info("test")
# lg1.debug('debug')
# lg1.info("test2")
# lg2.debug('debug')



def get_exception_line_no():
    
    _,_, exception_traceback = sys.exc_info()
    line_number = exception_traceback.tb_lineno
    
    return line_number


# LOG_FILE_PATH = os.path.join(ROOT_DIR, 'log')
# 
# 
# def change_log_file_handler(val=""):
    # dt_now = datetime.now().strftime('%Y%m%d%H%M%S%f')
    # 
    # if val != '':
        # LOG_FILE = f"htf_{dt_now}_{val}.log"
    # else:
        # LOG_FILE = f"hft_{dt_now}.log"
    # 
    # os.makedirs(LOG_FILE_PATH, exist_ok= True)
# 
    # logs_path = os.path.join(LOG_FILE_PATH,LOG_FILE)
# 
    # file_handler = logger.FileHandler(logs_path)
    # formatter = logger.Formatter("[ %(asctime)s ] %(lineno)d %(name)s - %(levelname)s - %(message)s")
    # file_handler.setFormatter(formatter)
    # logger.getLogger().addHandler(file_handler)
# 
    # for handler in logger.getLogger().handlers:
        # logger.getLogger().removeHandler(handler)
# 
    # file_handler.close()
# 
# 
# def init_logger():
    # dt_now = datetime.now().strftime('%Y%m%d%H%M%S%f')
    # LOG_FILE = f"hft_{dt_now}.log"
# 
    # logs_path = os.path.join(LOG_FILE_PATH,LOG_FILE)
# 
    # TODO: need to change the output file when gets bigger
    # os.makedirs(LOG_FILE_PATH, exist_ok= True)
# 
    # logger.basicConfig(
        # filename=logs_path,
        # format = "[ %(asctime)s ] %(lineno)d %(name)s - %(levelname)s - %(message)s",
    # )
# 
    # if True:
        # logger.getLogger().setLevel(logger.DEBUG)
    # else:
        # logger.getLogger().setLevel(logger.INFO)
# 
    # if False:
        # TODO: need to find a better way to disable
        # logger.disable(2000)
# 
    # return logger
# 
# 
# invoke the logger
# logger = init_logger()
