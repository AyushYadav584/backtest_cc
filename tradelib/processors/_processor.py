'''
this module is the parent class for all the processors such as backtest_processor
'''

from abc import ABC, abstractclassmethod

from .controllers import Algo

class Processor(ABC):

    def __init__(self, algo: Algo) -> None:
        super().__init__()
        self._algo = algo


    @abstractclassmethod
    def process(self):
        pass