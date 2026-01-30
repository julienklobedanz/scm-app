"""
Procurement Manager
Verwaltet Bestellungen basierend auf Reorder Points
"""

from typing import Deque, Optional
from collections import deque
from models.inventory import Inventory
from config.master_data import MasterData
from simulation.china_transport import ChinaTransportManager
from simulation.workday_calculator import WorkdayCalculator


class ProcurementManager:
    """Verwaltet Bestellungen beim chinesischen Lieferanten"""
    
    # Feiertage 2027 (Deutschland)
    HOLIDAYS_2027 = [
        "01.01.2027", "26.03.2027", "29.03.2027", "01.05.2027",
        "06.05.2027", "17.05.2027", "03.10.2027",
        "01.11.2027", "25.12.2027", "26.12.2027"
    ]
    
    def __init__(
        self, 
        inventory: Inventory, 
        china_transport_manager: ChinaTransportManager,
        workday_calculator: Optional[WorkdayCalculator] = None,
        window_size: int = 30
    ):
        self.inventory = inventory
        self.china_transport_manager = china_transport_manager
        self.workday_calculator = workday_calculator
        self.master_data = MasterData
        self.window_size = window_size
        
        # Gleitender Durchschnitt für Nachfrage
        self.demand_history_frames_alu: Deque[float] = deque(maxlen=window_size)
        self.demand_history_frames_carbon: Deque[float] = deque(maxlen=window_size)
        self.demand_history_saddles: Deque[float] = deque(maxlen=window_size)
    
    def update_demand_history(
        self,
        frame_demand_alu: float,
        frame_demand_carbon: float,
        saddle_demand: float
    ) -> None:
        """Aktualisiert die Nachfragehistorie"""
        self.demand_history_frames_alu.append(frame_demand_alu)
        self.demand_history_frames_carbon.append(frame_demand_carbon)
        self.demand_history_saddles.append(saddle_demand)
    
    def calculate_avg_demand(self, history: Deque[float]) -> float:
        """Berechnet den durchschnittlichen Bedarf aus der Historie"""
        if len(history) == 0:
            return 0.0
        return sum(history) / len(history)
    
    def check_and_order(self, day: int, expected_demand: float = None) -> None:
        """
        Prüft Reorder Points und platziert Bestellungen.
        Berücksichtigt Pipeline-Bestand (Ware unterwegs), um Endlos-Bestellungen zu vermeiden.
        
        PROAKTIVE LOGIK: Wenn expected_demand übergeben wird (Look-Ahead vom Simulator),
        wird dieser als primärer Treiber verwendet. Sonst Fallback auf historische Durchschnitte.
        
        Args:
            day: Aktueller Tag (0-basiert)
            expected_demand: Erwartete Nachfrage für die Lead Time (proaktiv berechnet, optional)
        """
        # WICHTIG: Rahmen sind unbegrenzt verfügbar, daher keine Bestellungen für Rahmen
        
        # NEU: Hole Ware, die schon unterwegs ist (Pipeline-Bestand)
        pipeline_stock = self.china_transport_manager.get_pipeline_inventory()
        
        # Der "Verfügbare Bestand" ist Lager + Pipeline
        effective_inventory = self.inventory.stock_saddles + pipeline_stock
        
        # PROAKTIVE LOGIK: Wenn expected_demand übergeben wurde (Look-Ahead vom Simulator)
        # expected_demand ist der tägliche Bedarf für den Tag (day + 49)
        if expected_demand is not None and expected_demand > 0:
            # Prüfe, ob das Ankunftsdatum ein Feiertag ist
            if self.workday_calculator:
                lead_time = self.master_data.CHINA_SUPPLIER['Saddles'].get('lead_time', 49)
                target_day = day + lead_time
                target_date = self.workday_calculator.get_date_from_day(target_day)
                target_date_str = target_date.strftime(self.master_data.DATE_FORMAT)
                
                # Wenn Ankunft an Feiertag -> keine Bestellung
                if target_date_str in self.HOLIDAYS_2027:
                    return  # Bestellung abbrechen
            
            # Bestelle genau den täglichen Bedarf für den Zukunftstag
            # Bestelle heute für den Bedarf in 49 Tagen
            # Der Simulator ruft diese Methode täglich auf, daher bestellen wir täglich
            # den Bedarf des jeweiligen Zukunftstags
            self.china_transport_manager.place_order(day, expected_demand)
        else:
            # FALLBACK: Reaktive Logik (wenn kein expected_demand übergeben wurde)
            # Durchschnittliche tägliche Nachfrage (nur für Sättel)
            avg_demand_saddles = self.calculate_avg_demand(self.demand_history_saddles)
            
            # Reorder Point = Durchschnittliche Nachfrage * Threshold-Tage
            threshold_days_saddles = self.master_data.CHINA_SUPPLIER['Saddles']['reorder_threshold_days']
            reorder_point_saddles = avg_demand_saddles * threshold_days_saddles
            
            # Prüfe gegen den effektiven Bestand
            if effective_inventory < reorder_point_saddles:
                # Auffüllen auf Reorder Point + Puffer
                safety_buffer = avg_demand_saddles * 7
                target_inventory = reorder_point_saddles + safety_buffer
                order_quantity = max(0, target_inventory - effective_inventory)
                
                if order_quantity > 0:
                    self.china_transport_manager.place_order(day, order_quantity)

