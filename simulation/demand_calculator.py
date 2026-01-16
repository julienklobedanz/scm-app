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
        start_date = date(self.workday_calculator.year, 1, 1)
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
        # Jahresvolumen * Verkaufsanteil * Saisonalität / Arbeitstage_im_Monat
        # WICHTIG: Verkaufsanteile werden direkt verwendet, ohne durch total_share zu teilen
        base_daily_float = {}
        
        for product in self.master_data.BOM.keys():
            sales_share = self.master_data.PRODUCT_SALES_SHARES.get(product, 0.0)
            # Jahresvolumen * Verkaufsanteil * Saisonalität / Arbeitstage_im_Monat
            # Dies entspricht: monthly_target_global * sales_share / num_workdays
            # Aber monthly_target_global = yearly_volume * monthly_factor
            # Also: yearly_volume * monthly_factor * sales_share / num_workdays
            monthly_target_product = monthly_target_global * sales_share
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
        
        Berechnungslogik:
        - Wenn Wochenende oder Feiertag: 0 (Rest bleibt unverändert vom letzten Arbeitstag)
        - Sonst: ABRUNDEN((Base * Share / AT) + Rest; 0) + Marketing-Add-on
        - Rest für nächsten Tag: (Base + Rest) - ABRUNDEN(Base + Rest; 0)
        - Wenn vorheriger Tag 0 war: Rest vom Vortag übernommen (nicht neu berechnet)
        
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
        
        # Wenn Wochenende oder Feiertag: 0
        # Wenn Wochenende oder Feiertag: 0 (Rest bleibt unverändert)
        if not is_workday:
            # Rest bleibt unverändert vom letzten Arbeitstag (wird nicht aktualisiert)
            return 0
        
        # Hole Base_Daily_Float für dieses Produkt
        base_daily_float = self.monthly_base_daily_float[month].get(product, 0.0)
        
        # Apply Carry-Over: Add remainder from previous workday
        # Rest wird vom VORHERIGEN Arbeitstag übernommen
        # Wenn der vorherige Tag ein Feiertag/Wochenende war, bleibt der Rest unverändert
        remainder = self.product_remainders.get(product, 0.0)
        
        # ABRUNDEN((Base * Share / AT) + Rest; 0) + Marketing-Add-on
        # 1. Base + Rest zusammenfassen
        # WICHTIG: Runde auf 12 Dezimalstellen, um Floating-Point-Fehler zu vermeiden
        # Verwende hohe Präzision für korrekte Berechnung
        base_with_remainder = round(base_daily_float + remainder, 12)
        
        # 2. Abrunden (ABRUNDEN(..., 0))
        # WICHTIG: math.floor() für korrekte Abrundung (int() rundet bei negativen Zahlen falsch)
        import math
        # ABRUNDEN rundet immer ab (auch bei negativen Zahlen)
        # math.floor() macht das korrekt
        # WICHTIG: Prüfe ob base_with_remainder sehr nahe an einer ganzen Zahl ist (Floating-Point-Fehler)
        # Wenn abs(base_with_remainder - round(base_with_remainder)) < 1e-10, dann ist es praktisch eine ganze Zahl
        if abs(base_with_remainder - round(base_with_remainder)) < 1e-10:
            # Praktisch eine ganze Zahl, runde auf diese ganze Zahl
            rounded_base = int(round(base_with_remainder))
        else:
            rounded_base = math.floor(base_with_remainder)  # Round down to nearest integer
        
        # 3. Marketing-Add-on addieren (NACH der Rundung)
        # Marketing-Add-on wird als Float addiert
        daily_target_float = rounded_base + marketing_add_on
        
        # 4. Marketing-Add-on addieren (NACH der Rundung)
        # Marketing-Add-on wird als Float addiert
        daily_target_float = rounded_base + marketing_add_on
        
        # 5. Am letzten Arbeitstag des Jahres: Reste aufsummieren
        # WICHTIG: Am letzten Arbeitstag müssen ALLE Reste aufsummiert werden
        # Am letzten Arbeitstag wird der Rest nicht verworfen, sondern addiert
        if is_last_workday_of_year:
            # Addiere den Rest vom Base+Rest (wird normalerweise verworfen)
            # Dies stellt sicher, dass alle Reste am Jahresende aufsummiert werden
            remainder_to_add = base_with_remainder - rounded_base
            daily_target_float = rounded_base + remainder_to_add + marketing_add_on
        
        # 6. Ergebnis abrunden (da wir Integer zurückgeben müssen)
        # WICHTIG: math.floor() für korrekte Abrundung
        # ABER: Am letzten Arbeitstag sollte das Ergebnis bereits ganzzahlig sein (Rest wurde addiert)
        daily_target_int = math.floor(daily_target_float)
        
        # 6. Berechne neuen Rest (nur aus Base + Rest, Marketing-Add-on wird nicht in Rest übernommen)
        # (Base + Rest) - ABRUNDEN(Base + Rest; 0)
        # WICHTIG: Verwende math.floor() für konsistente Berechnung
        # Wenn Ergebnis < 0, dann 0 (sollte nicht vorkommen, aber sicherheitshalber)
        if is_last_workday_of_year:
            new_remainder = 0.0
        else:
            # Berechne Rest: (Base + Rest) - ABRUNDEN(Base + Rest; 0)
            # Verwende math.floor() für konsistente Abrundung
            # WICHTIG: Verwende die gleiche rounded_base wie oben, um Konsistenz zu gewährleisten
            new_remainder = base_with_remainder - rounded_base
            # Runde auf 12 Dezimalstellen, um Floating-Point-Fehler zu vermeiden
            new_remainder = round(new_remainder, 12)
            if new_remainder < 0:
                new_remainder = 0.0
        
        # Update remainder (nur an Arbeitstagen)
        self.product_remainders[product] = new_remainder
        
        return daily_target_int
    
    def get_demand_for_future_day(self, day_index: int, marketing_add_ons: Dict[str, float] = None) -> Dict[str, int]:
        """
        Berechnet die Nachfrage für einen zukünftigen Tag.
        STRENGE LOGIK: Nur für Jahr 2027 (0 <= day_index <= 364).
        Für Tag > 364 (Jahr 2027): Gib 0 zurück (keine Bestellung für nächstes Jahr).
        
        Args:
            day_index: Tag-Index (0-basiert, 0 = 01.01.2027)
            marketing_add_ons: Optional dict mit Marketing-Add-ons pro Produkt
        
        Returns:
            Dict mit Produktname -> Ganzzahlige Nachfrage (0 wenn außerhalb 2027)
        """
        # KORREKTUR: Keine Zyklik am Ende - nur für Jahr 2027 bestellen
        if day_index < 0 or day_index > 364:
            # Außerhalb des Jahres 2027: Kein Bedarf
            return {product: 0 for product in self.master_data.BOM.keys()}
        
        # Innerhalb des Jahres 2027: Normaler Bedarf
        return self.calculate_daily_demand_per_product_dict(day_index, marketing_add_ons)
    
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
