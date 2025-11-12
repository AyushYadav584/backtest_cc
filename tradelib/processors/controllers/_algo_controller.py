'''
    This module will control the intra-day trading algorithm execution.
    It is expected to go over all the available time steps for a day 
    and delegate the corresponding responsibility.
'''

from datetime import datetime

from tradelib.strategies import TradeStrategy
from tradelib.strategies import OptionStrategyBuilder as strategy_builder
from modules._logger import logger,get_exception_line_no

logger = logger.getLogger('algo')


class Algo():

    def __init__(self) -> None:
        self._strategy = None


    def process_single_timestep(self):
        '''
        responsible for processing a single timestep
        '''

        logger.info(f"executing strategy")
        self._strategy.execute()
        logger.info(f"strategy executed")


    def driver(self, time_steps:list()):
        """
            The main driver method which will run over the time windows provided for a day.
        """

        try:
            self._strategy = strategy_builder.build()
            
            for time_step in time_steps:
                logger.info(f"{'+'*30} processing time step {time_step} {'+'*30}")
                self.process_single_timestep()
                logger.info(f"{'+'*30} processed time step {time_step} {'+'*30}")

        except Exception as ex:
            logger.critical(f"error within driver() at line={get_exception_line_no()}. {ex}")