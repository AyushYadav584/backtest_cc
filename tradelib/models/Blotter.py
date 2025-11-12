from models.BlotterPacket import BlotterPacket
from typing import List, Dict
from models.Trade import Trade
from datetime import datetime
from tradelib_utils import get_blotter_filename, serialiseInstrument
import os
import csv
from tradelib_logger import logger
from tradelib_global_constants import unit_size
from tradelib_global_constants import unit_size, strategy_trade_side, hedge_trade_side, unwind_trade_side, transaction_fee
import numpy as np
from models.Instrument import Instrument
 

_logger = logger.getLogger("blotter")
class Blotter:
    def __init__(self, output_dir:str):
        self.blotter_list: List[BlotterPacket] = []
        self.packet_id = 1
        self.trade_id = 1
        self.blotter_dir = os.path.join(output_dir, 'blotter')
        os.makedirs(self.blotter_dir, exist_ok=True)
        self.component_trade_id: Dict[str, int] = {}

        #gamma hedge
        self.accumulated_money = 0
        self.spent_money = 0

    def addTradeList(self, trade_list:List[Trade], trade_component: str, timestamp: datetime):
        for trade in trade_list:

            #? For Money Spent on OTM buy during GH
            if trade.trade_sub_type == "otm_trade":
                self.spent_money += (trade.instrument.mid * abs(unit_size))

            if trade.trade_sub_type == 'trade' and trade.position < 0:
                self.accumulated_money += (trade.instrument.mid * abs(trade.position))

            if trade_component not in self.component_trade_id:
                self.component_trade_id[trade_component] = 1
            self.blotter_list.append(BlotterPacket(trade, self.trade_id, self.packet_id, self.component_trade_id[trade_component], trade_component, timestamp))
            self.trade_id += 1
        self.packet_id += 1
        self.component_trade_id[trade_component] += 1

        # for otm trade
        # for trade in otm_trade_list:
            # print('Otm', timestamp, trade.instrument.mid, trade.position)
            # self.spent_money += (trade.instrument.mid * abs(trade.position))

    def saveToCsvAndClear(self, start_timestamp: datetime, end_timestamp: datetime):
        '''
        saves current state of portfolio in a csv
        '''
        file_path = os.path.join(self.blotter_dir, get_blotter_filename(start_timestamp, end_timestamp))
        with open(file_path, "w") as fp:
            writer = csv.writer(fp)
            writer.writerow(['timestamp', 'trade_id', 'packet_id', 'component_trade_id', 'trade_component', 'instrument_id', 'instrument_id_key ', 'position', 'price', 'trade_sub_type','instrument_object', 'exchange_fee','transaction_fee'])
            for blotter_packet in self.blotter_list:
                price = self.getPriceOption(detailedIns=blotter_packet.trade.instrument, position=blotter_packet.trade.position, trade_type=blotter_packet.trade.trade_sub_type)
                exchange_fee = 0 # price * abs(blotter_packet.trade.position) * exchange_fee_rate
                
                writer.writerow([blotter_packet.timestamp, blotter_packet.trade_id, blotter_packet.packet_id, blotter_packet.component_trade_id, blotter_packet.trade_component, blotter_packet.trade.instrument.id, blotter_packet.trade.instrument.idKey(), blotter_packet.trade.position, price, blotter_packet.trade.trade_sub_type, serialiseInstrument(blotter_packet.trade.instrument), exchange_fee, transaction_fee])
        self.trade_id = 1
        self.packet_id = 1
        self.component_trade_id.clear()
        self.blotter_list.clear()

    def get_accumulated_money(self, update=False):
        accumulated_money = self.accumulated_money
        spent_money = self.spent_money

        if update:
            self.accumulated_money = 0
            self.spent_money = 0

        return spent_money, accumulated_money
    
    def getPriceOption(self, detailedIns:Instrument, position:int, trade_type:str):
        market_side = unwind_trade_side if trade_type == "unwind" else hedge_trade_side if trade_type == "hedge" else strategy_trade_side
        
        if market_side == 'market_maker':
            if np.sign(position) < 0: # Sell
                return detailedIns.ask
            else:
                return detailedIns.bid
 
        elif market_side.lower()=="customer":
            if np.sign(position) < 0: # sell
                return detailedIns.bid
            else:
                return detailedIns.ask
 
        elif market_side.lower()=="customer+":
            if np.sign(position) < 0: # sell
                return (detailedIns.bid +detailedIns.mid)/2
            else:
                return (detailedIns.ask +detailedIns.mid)/2
 
        elif market_side.lower()=="market_maker-":
            if np.sign(position) < 0: # sell
                return (detailedIns.ask +detailedIns.mid)/2
            else:
                return (detailedIns.bid +detailedIns.mid)/2
 
        elif market_side.lower()=="mid":
            return detailedIns.mid
 
        else:
            raise Exception(f"{market_side=} is not implemented into the codebase")