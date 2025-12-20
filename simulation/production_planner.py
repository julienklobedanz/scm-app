"""
Production Planner
Berechnet mögliche Produktion basierend auf verfügbaren Komponenten und Schicht-Kapazität
"""

import math
from typing import Dict, Tuple
from models.inventory import Inventory
from config.master_data import MasterData


class ProductionPlanner:
    """Plant Produktion basierend auf Bottleneck-Logik und Schicht-Kapazitätsbeschränkung"""
    
    def __init__(self, inventory: Inventory):
        self.inventory = inventory
        self.master_data = MasterData
        
        # Schicht-Kapazitäts-Konstanten
        self.MIN_SHIFTS = 1
        self.MAX_SHIFTS = 3
        self.HOURS_PER_SHIFT = 8
        self.CAPACITY_PER_HOUR = self.master_data.GLOBAL_CONFIG['capacity_per_hour']  # 130
        self.CAPACITY_PER_SHIFT = self.HOURS_PER_SHIFT * self.CAPACITY_PER_HOUR  # 1040
    
    def calculate_production_capacity(
        self, 
        daily_target: float,
        frame_demand: Dict[str, float],
        saddle_demand: float
    ) -> Tuple[float, Dict[str, float], int, float]:
        """
        Berechnet die mögliche Produktion basierend auf verfügbaren Komponenten und Schicht-Kapazität.
        
        WICHTIG: Jedes Bike benötigt genau 1 Frame und 1 Saddle.
        Die Produktion ist limitiert durch:
        1. Verfügbare Komponenten (Frames, Saddles)
        2. Schicht-Kapazität (dynamisch basierend auf Nachfrage)
        
        Returns:
            (actual_build, consumed_components, actual_shifts, max_daily_capacity)
        """
        # Verfügbare Komponenten
        available_frames_alu = self.inventory.stock_alu
        available_frames_carbon = self.inventory.stock_carbon
        available_saddles = self.inventory.stock_saddles
        
        # Gesamtnachfrage nach Frames
        total_frame_demand = frame_demand['Alu'] + frame_demand['Carbon']
        
        # Berechne Schicht-Kapazität (Shift Capacity Constraint)
        # Required_Shifts_Float = Daily_Target / Capacity_Per_Shift
        required_shifts_float = daily_target / self.CAPACITY_PER_SHIFT if self.CAPACITY_PER_SHIFT > 0 else 0
        
        # Required_Shifts_Int = ceil(Required_Shifts_Float)
        required_shifts_int = math.ceil(required_shifts_float) if required_shifts_float > 0 else 0
        
        # Actual_Shifts = max(Min_Shifts, min(Max_Shifts, Required_Shifts_Int))
        actual_shifts = max(self.MIN_SHIFTS, min(self.MAX_SHIFTS, required_shifts_int))
        
        # Max_Daily_Capacity = Actual_Shifts * Capacity_Per_Shift
        max_daily_capacity = actual_shifts * self.CAPACITY_PER_SHIFT
        
        # Berechne mögliche Produktion basierend auf verfügbaren Komponenten
        # WICHTIG: Rahmen sind unbegrenzt verfügbar (wie Gabeln)
        # Limitierung nur durch Sättel
        max_from_saddles = available_saddles
        
        # Final Production: min(Daily_Target, Available_Saddles, Max_Daily_Capacity)
        possible_production = min(max_from_saddles, daily_target, max_daily_capacity)
        
        # Gesamtproduktion (Rahmen sind unbegrenzt, daher keine Limitierung)
        actual_build = possible_production
        
        # Verbrauchte Komponenten berechnen
        # Rahmen werden nicht verbraucht (unbegrenzt verfügbar)
        consumed = {
            'frames_alu': 0.0,  # Rahmen sind unbegrenzt
            'frames_carbon': 0.0,  # Rahmen sind unbegrenzt
            'saddles': min(available_saddles, actual_build)  # Jedes Bike braucht 1 Sattel
        }
        
        return actual_build, consumed, actual_shifts, max_daily_capacity
    
    def consume_components(self, consumed: Dict[str, float]) -> None:
        """Verbraucht Komponenten aus dem Lager"""
        self.inventory.stock_alu -= consumed['frames_alu']
        self.inventory.stock_carbon -= consumed['frames_carbon']
        self.inventory.stock_saddles -= consumed['saddles']
    
    def check_stoppage(
        self,
        daily_target: float,
        frame_demand: Dict[str, float],
        saddle_demand: float
    ) -> Tuple[bool, bool]:
        """
        Prüft ob Produktion wegen fehlender Komponenten gestoppt ist
        
        Returns:
            (stopped_frames, stopped_saddles)
        """
        if daily_target == 0:
            return False, False
        
        # WICHTIG: Rahmen sind unbegrenzt verfügbar, daher nie gestoppt
        stopped_frames = False
        
        # Prüfe ob genug Sättel vorhanden sind
        needed_saddles = saddle_demand
        available_saddles = self.inventory.stock_saddles
        
        stopped_saddles = available_saddles < needed_saddles
        
        return stopped_frames, stopped_saddles

