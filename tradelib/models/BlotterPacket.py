from models.Trade import Trade
from datetime import datetime

class BlotterPacket:
    def __init__(self, trade: Trade, trade_id: int, packet_id: int, component_trade_id:int,  trade_component: str, timestamp: datetime) -> None:
        self.trade = trade
        self.packet_id = packet_id
        self.component_trade_id = component_trade_id
        self.timestamp = timestamp
        self.trade_id = trade_id
        self.trade_component = trade_component