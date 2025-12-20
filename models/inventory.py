"""
Inventory Model
Verwaltet Lagerbestände und Bestellungen
"""

from typing import Dict
from dataclasses import dataclass, field


@dataclass
class Inventory:
    """Lagerbestand für eine Komponente"""
    stock_alu: float = 0.0
    stock_carbon: float = 0.0
    stock_saddles: float = 0.0
    
    # Offene Bestellungen: {arrival_day: quantity}
    open_orders_alu: Dict[int, float] = field(default_factory=dict)
    open_orders_carbon: Dict[int, float] = field(default_factory=dict)
    open_orders_saddles: Dict[int, float] = field(default_factory=dict)
    
    def receive_orders_frames(self, day: int, lead_time: int) -> None:
        """Empfängt Frame-Bestellungen, die heute ankommen"""
        arrival_day = day - lead_time
        if arrival_day >= 0:
            if arrival_day in self.open_orders_alu:
                self.stock_alu += self.open_orders_alu[arrival_day]
                del self.open_orders_alu[arrival_day]
            if arrival_day in self.open_orders_carbon:
                self.stock_carbon += self.open_orders_carbon[arrival_day]
                del self.open_orders_carbon[arrival_day]
    
    def receive_orders_saddles(self, day: int, lead_time: int) -> None:
        """Empfängt Saddle-Bestellungen, die heute ankommen"""
        arrival_day = day - lead_time
        if arrival_day >= 0:
            if arrival_day in self.open_orders_saddles:
                self.stock_saddles += self.open_orders_saddles[arrival_day]
                del self.open_orders_saddles[arrival_day]
    
    def place_order(self, component_type: str, day: int, lead_time: int, lot_size: float) -> None:
        """Platziert eine Bestellung"""
        arrival_day = day + lead_time
        if component_type == 'frame_alu':
            if arrival_day not in self.open_orders_alu:
                self.open_orders_alu[arrival_day] = 0
            self.open_orders_alu[arrival_day] += lot_size
        elif component_type == 'frame_carbon':
            if arrival_day not in self.open_orders_carbon:
                self.open_orders_carbon[arrival_day] = 0
            self.open_orders_carbon[arrival_day] += lot_size
        elif component_type == 'saddles':
            if arrival_day not in self.open_orders_saddles:
                self.open_orders_saddles[arrival_day] = 0
            self.open_orders_saddles[arrival_day] += lot_size

