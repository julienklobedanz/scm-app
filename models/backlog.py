"""
Backlog Model
Verwaltet Backlogs pro Markt und Transit-Pipeline
"""

from typing import Dict
from dataclasses import dataclass, field


@dataclass
class MarketBacklog:
    """Backlog für alle Märkte"""
    backlog: Dict[str, float] = field(default_factory=dict)
    in_transit: Dict[int, Dict[str, float]] = field(default_factory=dict)
    
    def initialize_markets(self, markets: Dict[str, Dict]) -> None:
        """Initialisiert Backlog für alle Märkte"""
        for market in markets.keys():
            self.backlog[market] = 0.0
    
    def ship_to_markets(self, day: int, shipped_qty: float, markets: Dict[str, Dict]) -> None:
        """Versendet Produkte an Märkte"""
        for market, params in markets.items():
            arrival_day = day + params['transit_days']
            if arrival_day not in self.in_transit:
                self.in_transit[arrival_day] = {}
            if market not in self.in_transit[arrival_day]:
                self.in_transit[arrival_day][market] = 0.0
            self.in_transit[arrival_day][market] += shipped_qty * params['share']
    
    def receive_shipments(self, day: int, daily_target: float, markets: Dict[str, Dict]) -> None:
        """Empfängt Lieferungen und aktualisiert Backlog"""
        if day in self.in_transit:
            for market, qty in self.in_transit[day].items():
                market_demand = daily_target * markets[market]['share']
                # Backlog kann negativ werden (Überbestand)
                self.backlog[market] += (qty - market_demand)
            del self.in_transit[day]

