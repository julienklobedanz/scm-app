"""
Demand Calculator
Berechnet tägliche Nachfrage mit Carry-Over-Logik für präzise Ganzzahl-Produktion
"""

from typing import Dict, Tuple
from datetime import date, timedelta
from config.master_data import MasterData
from simulation.workday_calculator import WorkdayCalculator


class DemandCalculator:
    """Berechnet Nachfrage basierend auf Saisonalität und BOM mit Carry-Over-Logik"""
    
    def __init__(self, yearly_volume: float, workday_calculator: WorkdayCalculator):
        self.yearly_volume = yearly_volume
        self.master_data = MasterData
        self.workday_calculator = workday_calculator
        
        # Remainder-Speicher pro Produkt (für Carry-Over-Logik)
        self.product_remainders: Dict[str, float] = {}
        for product in self.master_data.BOM.keys():
            self.product_remainders[product] = 0.0
        
        # Monatliche Base_Daily_Float pro Produkt (wird bei Monatswechsel neu berechnet)
        self.monthly_base_daily_float: Dict[int, Dict[str, float]] = {}
        self.current_month = None
    
    def _calculate_monthly_base_daily_float(self, month: int) -> Dict[str, float]:
        """
        Pre-Calculation (Monthly Basis)
        Berechnet Base_Daily_Float für alle Produkte im Monat
        """
        if month in self.monthly_base_daily_float:
            return self.monthly_base_daily_float[month]
        
        # Monatliches Ziel pro Produkt
        monthly_factor = self.master_data.SEASONALITY[month]
        monthly_target_global = self.yearly_volume * monthly_factor
        
        # Zähle Arbeitstage im Monat
        num_workdays = 0
        start_date = date(2026, 1, 1)
        days_in_month = self.master_data.DAYS_PER_MONTH[month]
        
        # Finde ersten Tag des Monats
        month_start_day = sum(self.master_data.DAYS_PER_MONTH[m] for m in range(1, month))
        
        for day_offset in range(days_in_month):
            day = month_start_day + day_offset
            if self.workday_calculator.is_workday(day):
                num_workdays += 1
        
        if num_workdays == 0:
            # Fallback falls kein Arbeitstag (sollte nicht vorkommen)
            num_workdays = 1
        
        # Base_Daily_Float pro Produkt
        base_daily_float = {}
        total_share = sum(self.master_data.PRODUCT_SALES_SHARES.values())
        
        for product in self.master_data.BOM.keys():
            sales_share = self.master_data.PRODUCT_SALES_SHARES.get(product, 0.0)
            if total_share > 0:
                monthly_target_product = monthly_target_global * (sales_share / total_share)
            else:
                monthly_target_product = monthly_target_global / len(self.master_data.BOM)
            
            base_daily_float[product] = monthly_target_product / num_workdays
        
        self.monthly_base_daily_float[month] = base_daily_float
        return base_daily_float
    
    def calculate_daily_demand_per_product(
        self, 
        day: int, 
        product: str,
        marketing_add_on: float = 0.0,
        is_last_workday_of_year: bool = False
    ) -> int:
        """
        Berechnet tägliche Nachfrage für ein spezifisches Produkt mit Carry-Over-Logik
        
        Args:
            day: Tag (0-basiert)
            product: Produktname
            marketing_add_on: Marketing-Add-on (Float)
            is_last_workday_of_year: Wenn True, werden Reste am Jahresende aufsummiert
        
        Returns:
            Ganzzahlige Nachfrage (int)
        """
        month = self.master_data.get_month_from_day(day)
        is_workday = self.workday_calculator.is_workday(day)
        
        # Wenn Monat gewechselt, berechne neue Base_Daily_Float
        if self.current_month != month:
            self._calculate_monthly_base_daily_float(month)
            self.current_month = month
        
        # Wenn kein Arbeitstag: Daily_Target = 0, Remainder bleibt unverändert
        if not is_workday:
            return 0
        
        # Hole Base_Daily_Float für dieses Produkt
        base_daily_float = self.monthly_base_daily_float[month].get(product, 0.0)
        
        # Apply Carry-Over: Add remainder from previous day
        remainder = self.product_remainders.get(product, 0.0)
        
        # Excel-Formel: Marketing-Add-on + ABRUNDEN(Base + Rest; 0)
        # 1. Base + Rest zusammenfassen
        base_with_remainder = base_daily_float + remainder
        
        # 2. Abrunden (wie Excel ABRUNDEN(..., 0))
        rounded_base = int(base_with_remainder)  # Round down to nearest integer
        
        # 3. Marketing-Add-on addieren (NACH der Rundung, wie in Excel)
        # Marketing-Add-on wird als Float addiert (kann auch Float sein in Excel)
        daily_target_float = rounded_base + marketing_add_on
        
        # 4. Am letzten Arbeitstag des Jahres: Reste aufsummieren
        if is_last_workday_of_year:
            # Addiere den Rest vom Base+Rest (wird normalerweise verworfen)
            daily_target_float += (base_with_remainder - rounded_base)
        
        # 5. Ergebnis abrunden (da wir Integer zurückgeben müssen)
        daily_target_int = int(daily_target_float)
        
        # 6. Berechne neuen Rest (nur aus Base + Rest, Marketing-Add-on wird nicht in Rest übernommen)
        # Am letzten Tag: Rest wird auf 0 gesetzt, da er bereits produziert wurde
        if is_last_workday_of_year:
            new_remainder = 0.0
        else:
            new_remainder = base_with_remainder - rounded_base
        
        # Update remainder
        self.product_remainders[product] = new_remainder
        
        return daily_target_int
    
    def calculate_daily_demand(self, day: int, marketing_add_ons: Dict[str, float] = None) -> float:
        """
        Berechnet die gesamte tägliche Nachfrage (Summe aller Produkte)
        
        Args:
            day: Tag (0-basiert)
            marketing_add_ons: Optional dict mit Marketing-Add-ons pro Produkt
        """
        if marketing_add_ons is None:
            marketing_add_ons = {}
        
        total_demand = 0.0
        for product in self.master_data.BOM.keys():
            add_on = marketing_add_ons.get(product, 0.0)
            product_demand = self.calculate_daily_demand_per_product(day, product, add_on)
            total_demand += product_demand
        
        return total_demand
    
    def calculate_daily_demand_per_product_dict(
        self, 
        day: int,
        marketing_add_ons: Dict[str, float] = None,
        is_last_workday_of_year: bool = False
    ) -> Dict[str, int]:
        """
        Berechnet tägliche Nachfrage für alle Produkte als Dictionary
        
        Args:
            day: Tag (0-basiert)
            marketing_add_ons: Optional dict mit Marketing-Add-ons pro Produkt
            is_last_workday_of_year: Wenn True, werden Reste am Jahresende aufsummiert
        
        Returns:
            Dict mit Produktname -> Ganzzahlige Nachfrage
        """
        if marketing_add_ons is None:
            marketing_add_ons = {}
        
        product_demands = {}
        for product in self.master_data.BOM.keys():
            add_on = marketing_add_ons.get(product, 0.0)
            product_demands[product] = self.calculate_daily_demand_per_product(
                day, product, add_on, is_last_workday_of_year
            )
        
        return product_demands
    
    def aggregate_bom_demand(self, product_demands: Dict[str, int]) -> Tuple[Dict[str, float], float]:
        """
        Aggregiert die BOM-Anforderungen für Frames und Saddles basierend auf Produkt-Nachfragen
        
        Args:
            product_demands: Dict mit Produktname -> Nachfrage (int)
        
        Returns:
            (frame_demand, saddle_demand)
        """
        frame_demand = {'Alu': 0.0, 'Carbon': 0.0}
        saddle_demand = 0.0
        
        for product, demand_qty in product_demands.items():
            components = self.master_data.BOM.get(product, {})
            frame_type = components.get('frame', '')
            frame_category = self.master_data.get_frame_category(frame_type)
            
            frame_demand[frame_category] += demand_qty
            saddle_demand += demand_qty  # Jedes Bike braucht 1 Sattel
        
        return frame_demand, saddle_demand
