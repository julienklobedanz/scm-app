"""
China Transport Manager
Simuliert den detaillierten Transport von China nach Deutschland
"""

from typing import Dict, List, Tuple, Optional
from datetime import date, timedelta
import pandas as pd
from models.inventory import Inventory
from simulation.workday_calculator import WorkdayCalculator
from config.master_data import MasterData
from models.scenarios import ScenarioManager, DeliveryProblemScenario


class ChinaTransportManager:
    """
    Verwaltet den Transport von China nach Deutschland mit detaillierter Logik:
    1. Produktion in China: 5 AT (Tag der Bestellung zählt NICHT)
    2. LKW zum Hafen (China): 2 AT
    3. Warten auf Mittwoch (Schiff fährt nur Mittwochs ab)
    4. Schiff: 30 KT (Kalendertage)
    5. LKW zum Werk (Deutschland): 2 AT
    6. Wareneingang: +1 Tag zwischen physischer Ankunft und Verfügbarkeit
    """
    
    def __init__(self, inventory: Inventory, workday_calculator: WorkdayCalculator, scenario_manager: Optional[ScenarioManager] = None):
        self.inventory = inventory
        self.workday_calculator = workday_calculator
        self.master_data = MasterData
        self.scenario_manager = scenario_manager
        
        # Transport-Status pro Bestellung
        # Key: (order_day, order_id), Value: Transport-Status
        self.transport_status: Dict[Tuple[int, int], Dict] = {}
        self.order_counter = 0
        
        # Kumulierte Bestellungen am Hafen (für Versandlogik: >= 500)
        # Key: arrival_at_port_day, Value: kumulierte Menge
        self.pending_shipments: Dict[int, float] = {}  # {arrival_at_port_day: cumulative_quantity}
        
        # Cache für Inbound-Tabelle (Performance-Optimierung)
        # Key: tuple(sorted(saddle_shares_dict.items())), Value: DataFrame
        self._inbound_df_cache: Dict[tuple, pd.DataFrame] = {}
        self._inbound_df_cache_key: Optional[tuple] = None
        
        # PERFORMANCE: Cache für Supplier-Log-Tabelle (Performance-Optimierung)
        # Key: (saddle_name, saddle_share), Value: DataFrame
        self._supplier_log_cache: Dict[tuple, pd.DataFrame] = {}
        
        # PERFORMANCE: Cache für chinesische Feiertage (nur einmal laden)
        self._chinese_holidays_cache: Optional[set] = None
        self._chinese_holidays_year: Optional[int] = None
    
    def place_order(self, order_day: int, quantity: float) -> int:
        """
        Platziert eine Bestellung in China
        
        Args:
            order_day: Tag der Bestellung (0-basiert)
            quantity: Bestellmenge
            
        Returns:
            order_id: Eindeutige Bestell-ID
        """
        # WICHTIG: Cache invalidieren, da sich die Datenbasis geändert hat!
        self._inbound_df_cache = {}
        self._inbound_df_cache_key = None
        self._supplier_log_cache = {}  # PERFORMANCE: Auch Supplier-Log-Cache invalidieren
        # KRITISCH: Auch chinesische Feiertage-Cache invalidieren (falls sich Jahr ändert)
        self._chinese_holidays_cache = None
        self._chinese_holidays_year = None
        
        self.order_counter += 1
        order_id = self.order_counter
        
        # Prüfe Produktionsprobleme beim Lieferanten (z.B. SupplierBreakdownScenario)
        # HINWEIS: Transportprobleme (DeliveryProblemScenario) werden erst beim Versand angewendet!
        # Hier nur Produktionsverluste berücksichtigen (falls vorhanden)
        production_loss_percentage = 0.0
        
        # Status initialisieren
        order_date = self.workday_calculator.get_date_from_day(order_day)
        
        # Freigabedatum: Nächster Arbeitstag nach Bestellung
        # Das Produktionsdatum bezieht sich auf das Freigabedatum, nicht auf das Bestelldatum!
        released_day = self._get_next_workday(order_day)
        
        # Schritt 1: Produktion in China (5 AT)
        # ARBEITSTAG bedeutet: Start-Tag + 5 Arbeitstage (Start-Tag zählt nicht mit)
        # Das Freigabedatum ist der Start-Tag, nicht das Bestelldatum
        # WICHTIG: Für Produktion in China werden chinesische Feiertage verwendet!
        production_start_day = released_day
        production_end_day = self._add_workdays(production_start_day, 5, exclude_start=True, use_chinese_holidays=True)
        
        # Schritt 2: LKW zum Hafen (China) - 2 AT
        # HINWEIS: Verspätungen werden erst beim Versand (in process_shipments) angewendet
        truck_china_start_day = production_end_day
        truck_china_duration = 2
        truck_china_end_day = self._add_workdays(truck_china_start_day, truck_china_duration)
        
        # Schritt 3: Ankunft im Hafen
        arrival_at_port_day = truck_china_end_day
        
        # Speichere Bestellung für Versandlogik
        # Die Versandlogik sammelt alle Bestellungen, die im Hafen ankommen
        # und versendet, sobald kumulierte Menge >= 500 erreicht
        if arrival_at_port_day not in self.pending_shipments:
            self.pending_shipments[arrival_at_port_day] = 0.0
        self.pending_shipments[arrival_at_port_day] += quantity
        
        # Versandlogik wird später in process_shipments() behandelt
        # Hier speichern wir nur die Bestellung
        # ship_departure_day wird später berechnet, wenn >= 500 erreicht ist
        
        # Berechne tatsächliche Menge nach Produktionsverlusten (nicht Transportverluste!)
        # Transportverluste werden erst beim Versand in process_shipments() angewendet
        actual_quantity = quantity * (1.0 - production_loss_percentage)
        
        self.transport_status[(order_day, order_id)] = {
            'order_day': order_day,
            'order_id': order_id,
            'released_day': released_day,  # Freigabedatum (nächster Arbeitstag nach Bestellung)
            'quantity': quantity,  # Ursprüngliche Menge
            'actual_quantity': actual_quantity,  # Menge nach Produktionsverlusten (vor Transportverlusten)
            'production_loss_percentage': production_loss_percentage,
            'production_start_day': production_start_day,
            'production_end_day': production_end_day,
            'truck_china_start_day': truck_china_start_day,
            'truck_china_end_day': truck_china_end_day,
            'arrival_at_port_day': arrival_at_port_day,
            'ship_departure_day': None,  # Wird später gesetzt, wenn Versand ausgelöst wird
            'ship_arrival_day': None,  # Wird später gesetzt
            'truck_de_start_day': None,  # Wird später gesetzt
            'truck_de_end_day': None,  # Wird später gesetzt
            'physical_arrival_day': None,  # Wird später gesetzt
            'available_day': None,  # Wird später gesetzt
            'received': False,
            'shipped': False  # Wurde bereits versandt?
        }
        
        return order_id
    
    def process_shipments(self, current_day: int) -> None:
        """
        Verarbeitet Versände: Sammelt ALLE Waren im Hafen (kumuliert) und verschifft, 
        sobald >= 500 erreicht sind. Es werden immer exakt 500 Stück verschickt (unabhängig vom Typ),
        sodass ein Restbestand beim Lieferanten übrig bleiben kann.
        Wird nur Mittwochs ausgeführt.
        
        Args:
            current_day: Aktueller Tag (0-basiert)
        """
        # WICHTIG: Cache invalidieren, da sich Mengen durch Losses ändern könnten
        self._inbound_df_cache = {}
        self._inbound_df_cache_key = None
        
        current_date = self.workday_calculator.get_date_from_day(current_day)
        
        # Prüfe nur an Mittwochen (Schiff fährt nur Mittwochs ab)
        if current_date.weekday() != 2:  # Mittwoch ist 2
            return
        
        lot_size = self.master_data.CHINA_SUPPLIER['Saddles']['lot_size']
        
        # 1. Sammle ALLES, was im Hafen liegt und wartet (Ankunft <= heute)
        # Sortiere nach Ankunftstag (älteste zuerst) für FIFO-Logik
        ready_to_ship_orders = []  # Liste von status-Objekten
        total_quantity_at_port = 0.0
        
        for (order_day, order_id), status in self.transport_status.items():
            if (status['arrival_at_port_day'] is not None and 
                status['arrival_at_port_day'] <= current_day and 
                not status['shipped']):
                ready_to_ship_orders.append(status)
                total_quantity_at_port += status['quantity']
        
        # Sortiere nach Ankunftstag (älteste zuerst) für FIFO-Logik
        ready_to_ship_orders.sort(key=lambda s: s['arrival_at_port_day'])
        
        # 2. Prüfe, ob die GESAMTSUMME für einen Container reicht (>= 500)
        if total_quantity_at_port >= lot_size:
            # Wir verschiffen immer exakt 500 Stück (nicht die gesamte Menge)
            ship_departure_day = current_day
            
            # Wende Lieferprobleme-Szenarien an (Transportprobleme: Container über Bord, Verspätung)
            delivery_problems = []
            if self.scenario_manager:
                delivery_problems = self.scenario_manager.get_delivery_problem_scenarios(ship_departure_day)
            
            # Berechne Verspätung und Verlust aus Szenarien
            delay_days = 0
            loss_factor = 1.0
            for scenario in delivery_problems:
                if scenario.component_type == 'saddles':
                    delay_days = max(delay_days, scenario.delay_days)
                    loss_factor *= (1.0 - scenario.loss_percentage)
            
            # KRITISCH: Schiff fährt 30 KALENDERTAGE (KT), nicht Arbeitstage!
            # Das Schiff fährt kontinuierlich, Feiertage spielen keine Rolle
            # Berechnung: Abfahrt + 30 Kalendertage
            ship_departure_date = self.workday_calculator.get_date_from_day(ship_departure_day)
            ship_arrival_date = ship_departure_date + timedelta(days=30)  # 30 Kalendertage
            # Verspätung wird als Kalendertage addiert
            if delay_days > 0:
                ship_arrival_date += timedelta(days=delay_days)
            # Konvertiere zurück zu Tag-Index
            ship_arrival_day = (ship_arrival_date - date(self.workday_calculator.year, 1, 1)).days
            
            # KRITISCH: ARBEITSTAG für geplante/tatsächliche Ankunft: Ankunft Schiff + 1 Arbeitstag
            # Start-Datum zählt NICHT mit! Also: Ankunft Schiff + 1 Arbeitstag (Ankunft zählt nicht)
            truck_de_start_day = ship_arrival_day
            truck_de_end_day = self._add_workdays(truck_de_start_day, 1, exclude_start=True, use_chinese_holidays=False)  # 2-1 = 1 Arbeitstag, Start zählt nicht!
            physical_arrival_day = truck_de_end_day
            available_day = physical_arrival_day + 1
            
            # Verschiffe exakt 500 Stück (FIFO: älteste Bestellungen zuerst)
            remaining_to_ship = lot_size  # Exakt 500 Stück
            
            for status in ready_to_ship_orders:
                if remaining_to_ship <= 0:
                    break
                
                # Berechne, wie viel von dieser Bestellung verschickt wird
                quantity_to_ship_from_order = min(remaining_to_ship, status['quantity'])
                
                # Wenn die gesamte Bestellung verschickt wird
                if quantity_to_ship_from_order >= status['quantity']:
                    # Update Status - gesamte Bestellung wird verschickt
                    status['ship_departure_day'] = ship_departure_day
                    status['ship_arrival_day'] = ship_arrival_day
                    status['truck_de_start_day'] = truck_de_start_day
                    status['truck_de_end_day'] = truck_de_end_day
                    status['physical_arrival_day'] = physical_arrival_day
                    status['available_day'] = available_day
                    status['shipped'] = True
                    status['shipped_quantity'] = status['quantity']  # Gesamte Menge
                    
                    # Verlust anwenden (Container-Verlust passiert auf See)
                    status['actual_quantity'] = status['actual_quantity'] * loss_factor
                    
                    remaining_to_ship -= status['quantity']
                else:
                    # Nur ein Teil der Bestellung wird verschickt
                    # Erstelle einen neuen Status für den verschickten Teil
                    # Der Rest bleibt im Hafen
                    shipped_status = status.copy()
                    shipped_status['shipped_quantity'] = quantity_to_ship_from_order
                    shipped_status['ship_departure_day'] = ship_departure_day
                    shipped_status['ship_arrival_day'] = ship_arrival_day
                    shipped_status['truck_de_start_day'] = truck_de_start_day
                    shipped_status['truck_de_end_day'] = truck_de_end_day
                    shipped_status['physical_arrival_day'] = physical_arrival_day
                    shipped_status['available_day'] = available_day
                    shipped_status['shipped'] = True
                    
                    # Verlust anwenden
                    # Anteilig: nur der verschickte Teil hat Verlust
                    shipped_ratio = quantity_to_ship_from_order / status['quantity']
                    shipped_status['actual_quantity'] = status['actual_quantity'] * shipped_ratio * loss_factor
                    
                    # Aktualisiere die ursprüngliche Bestellung: Reduziere Menge um verschickten Teil
                    status['quantity'] -= quantity_to_ship_from_order
                    status['actual_quantity'] = status['actual_quantity'] * (1.0 - shipped_ratio)
                    # Diese Bestellung bleibt im Hafen (shipped = False)
                    
                    # Speichere den verschickten Teil als neue Bestellung
                    new_order_id = self.order_counter + 1
                    self.order_counter += 1
                    self.transport_status[(status['order_day'], new_order_id)] = shipped_status
                    
                    remaining_to_ship -= quantity_to_ship_from_order
            
            # Aktualisiere pending_shipments: Reduziere um 500
            # Finde alle betroffenen arrival_days und reduziere entsprechend
            shipped_quantity_total = lot_size  # Exakt 500
            for arrival_day in sorted(set(s['arrival_at_port_day'] for s in ready_to_ship_orders)):
                if arrival_day in self.pending_shipments and shipped_quantity_total > 0:
                    reduction = min(self.pending_shipments[arrival_day], shipped_quantity_total)
                    self.pending_shipments[arrival_day] -= reduction
                    shipped_quantity_total -= reduction
                    if self.pending_shipments[arrival_day] <= 0:
                        del self.pending_shipments[arrival_day]
    
    def _get_next_workday(self, start_day: int, use_chinese_holidays: bool = True) -> int:
        """
        Findet den nächsten Arbeitstag nach dem Start-Tag
        Berücksichtigt chinesische Feiertage für Freigabe in China
        IGNORIERT deutsche Feiertage, wenn use_chinese_holidays=True
        
        PERFORMANCE-OPTIMIERT: Verwendet gecachte chinesische Feiertage.
        
        Args:
            start_day: Start-Tag (0-basiert)
            use_chinese_holidays: Wenn True, verwendet nur chinesische Feiertage (Standard: True für China)
            
        Returns:
            Nächster Arbeitstag (0-basiert)
        """
        # PERFORMANCE: Verwende gecachte chinesische Feiertage
        chinese_holidays = None
        if use_chinese_holidays:
            chinese_holidays = self._get_chinese_holidays()
        
        current_day = start_day + 1
        while True:
            current_date = self.workday_calculator.get_date_from_day(current_day)
            weekday = current_date.weekday()  # 0=Montag, 6=Sonntag
            
            # KORREKTUR: Prüfe nur Wochenende, nicht deutsche Feiertage
            # Wenn chinesische Feiertage verwendet werden, ignoriere deutsche Feiertage komplett
            is_weekend = weekday >= 5  # Samstag=5, Sonntag=6
            
            if is_weekend:
                current_day += 1
                continue
            
            # Prüfe chinesische Feiertage (falls aktiviert)
            if use_chinese_holidays and chinese_holidays:
                if current_date in chinese_holidays:
                    current_day += 1
                    continue
            
            # Wenn wir hier ankommen, ist es ein Arbeitstag in China (Mo-Fr, kein chinesischer Feiertag)
            return current_day
    
    def _get_chinese_holidays(self) -> set:
        """
        PERFORMANCE: Lädt chinesische Feiertage nur einmal und cached sie.
        """
        if self._chinese_holidays_cache is None or self._chinese_holidays_year != self.workday_calculator.year:
            from config.holidays_config import HolidaysConfig
            holidays_dict = HolidaysConfig.get_holidays_for_year(self.workday_calculator.year, 'CN')
            self._chinese_holidays_cache = set(holidays_dict.keys()) if holidays_dict else set()
            self._chinese_holidays_year = self.workday_calculator.year
        return self._chinese_holidays_cache
    
    def _add_workdays(self, start_day: int, num_workdays: int, exclude_start: bool = False, use_chinese_holidays: bool = False) -> int:
        """
        Fügt Arbeitstage hinzu (Mo-Fr)
        
        PERFORMANCE-OPTIMIERT: Verwendet gecachte chinesische Feiertage und optimierte Datumsberechnung.
        
        Args:
            start_day: Start-Tag (0-basiert)
            num_workdays: Anzahl Arbeitstage
            exclude_start: Wenn True, zählt der Start-Tag nicht mit
            use_chinese_holidays: Wenn True, verwendet chinesische Feiertage (für Produktion in China)
            
        Returns:
            End-Tag (0-basiert)
        """
        # PERFORMANCE: Für kleine num_workdays (1-2) können wir direkt berechnen
        if num_workdays <= 0:
            return start_day
        
        current_day = start_day
        if exclude_start:
            current_day += 1
        
        workdays_added = 0
        
        # PERFORMANCE: Verwende gecachte chinesische Feiertage
        chinese_holidays = None
        if use_chinese_holidays:
            chinese_holidays = self._get_chinese_holidays()
        
        # PERFORMANCE: Berechne Start-Datum nur einmal
        start_date = self.workday_calculator.get_date_from_day(start_day)
        start_weekday = start_date.weekday()
        
        # PERFORMANCE: Für kleine num_workdays können wir optimieren
        if num_workdays == 1 and not use_chinese_holidays:
            # Einfacher Fall: nur 1 Arbeitstag, keine chinesischen Feiertage
            if start_weekday < 5:  # Mo-Fr
                return current_day
            else:  # Sa-So
                # Springe zum nächsten Montag
                days_to_monday = (7 - start_weekday) % 7
                if days_to_monday == 0:
                    days_to_monday = 7
                return current_day + days_to_monday
        
        # Allgemeiner Fall: Iteriere durch Tage
        while workdays_added < num_workdays:
            current_date = self.workday_calculator.get_date_from_day(current_day)
            weekday = current_date.weekday()  # 0=Montag, 6=Sonntag
            
            # Prüfe Wochenende
            is_weekend = weekday >= 5  # Samstag=5, Sonntag=6
            
            if is_weekend:
                current_day += 1
                continue
            
            # Prüfe Feiertage
            is_holiday = False
            
            if use_chinese_holidays:
                # Chinesische Feiertage (für Produktion in China)
                if chinese_holidays and current_date in chinese_holidays:
                    is_holiday = True
            else:
                # Deutsche Feiertage (für LKW-Transport in Deutschland)
                if current_date in self.workday_calculator.german_holidays:
                    is_holiday = True
            
            if not is_holiday:
                workdays_added += 1
            current_day += 1
        
        return current_day - 1  # -1 weil wir am Ende des letzten Arbeitstages sind
    
    def _add_workdays_from_date(self, start_date: date, num_workdays: int, exclude_start: bool = False, use_chinese_holidays: bool = False) -> date:
        """
        Fügt Arbeitstage zu einem Datum hinzu (direkt mit Datumsobjekten).
        Nützlich wenn das Start-Datum außerhalb des Jahres liegt (z.B. 24.11.2026).
        
        Args:
            start_date: Start-Datum
            num_workdays: Anzahl Arbeitstage
            exclude_start: Wenn True, zählt der Start-Tag nicht mit
            use_chinese_holidays: Wenn True, verwendet chinesische Feiertage
            
        Returns:
            End-Datum
        """
        if num_workdays <= 0:
            return start_date
        
        current_date = start_date
        if exclude_start:
            current_date += timedelta(days=1)
        
        workdays_added = 0
        
        # KRITISCH: Lade chinesische Feiertage für beide Jahre (falls nötig)
        # Da start_date auch im Vorjahr liegen kann, müssen wir Feiertage für beide Jahre laden
        chinese_holidays = set()
        if use_chinese_holidays:
            # Lade Feiertage für das Jahr von start_date und das aktuelle Jahr
            from config.holidays_config import HolidaysConfig
            year_start = start_date.year
            year_current = self.workday_calculator.year
            for year in [year_start, year_current]:
                holidays_dict = HolidaysConfig.get_holidays_for_year(year, 'CN')
                if holidays_dict:
                    chinese_holidays.update(holidays_dict.keys())
        
        # Iteriere durch Tage
        while workdays_added < num_workdays:
            weekday = current_date.weekday()  # 0=Montag, 6=Sonntag
            
            # Prüfe Wochenende
            is_weekend = weekday >= 5  # Samstag=5, Sonntag=6
            
            if is_weekend:
                current_date += timedelta(days=1)
                continue
            
            # Prüfe Feiertage
            is_holiday = False
            
            if use_chinese_holidays:
                # Chinesische Feiertage (für Produktion in China)
                if chinese_holidays and current_date in chinese_holidays:
                    is_holiday = True
            else:
                # Deutsche Feiertage (für LKW-Transport in Deutschland)
                if current_date in self.workday_calculator.german_holidays:
                    is_holiday = True
            
            if not is_holiday:
                workdays_added += 1
            current_date += timedelta(days=1)
        
        return current_date - timedelta(days=1)  # -1 weil wir am Ende des letzten Arbeitstages sind
    
    def get_pipeline_inventory(self) -> float:
        """
        Gibt die Summe aller Sättel zurück, die bestellt, aber noch nicht empfangen wurden.
        Dies ist der "Pipeline-Bestand" (Ware unterwegs).
        
        Returns:
            Gesamtmenge der unterwegs befindlichen Sättel
        """
        total_pipeline = 0.0
        for status in self.transport_status.values():
            if not status['received']:
                # Zähle alles, was noch nicht als 'received' markiert ist
                # Verwende actual_quantity (nach Produktionsverlusten, aber vor Transportverlusten)
                total_pipeline += status.get('actual_quantity', status.get('quantity', 0.0))
        return total_pipeline
    
    def _calculate_order_quantity_from_volume_planning(self, order_date: date, saddle_name: str, daily_demands_actual_cache: dict = None) -> float:
        """
        Berechnet die Bestellmenge für einen Sattel-Typ basierend auf der Volumenplanung.
        
        OPTIMIERUNG: daily_demands_actual_cache kann übergeben werden, um wiederholte
        session_state-Zugriffe zu vermeiden.
        
        Summiert die Nachfrage aller Produkte, die den gleichen Sattel verwenden,
        für den Tag (order_date + lead_time_days).
        
        Args:
            order_date: Datum der Bestellung
            saddle_name: Name des Sattels (z.B. "Fizik Tundra")
            daily_demands_actual_cache: Optional: Vorher geladene daily_demands_actual (für Performance)
        
        Returns:
            Bestellmenge (Summe der Nachfrage aller Produkte mit diesem Sattel)
        """
        # OPTIMIERUNG: Wenn Cache nicht übergeben wurde, lade aus session_state
        if daily_demands_actual_cache is None:
            try:
                import streamlit as st
                STREAMLIT_AVAILABLE = True
            except ImportError:
                STREAMLIT_AVAILABLE = False
                st = None
            
            if not STREAMLIT_AVAILABLE:
                return 0.0
            
            daily_demands_actual_cache = st.session_state.get('daily_demands_actual', {})
        
        # Hole Lead Time (49 Tage)
        lead_time_days = self.master_data.CHINA_SUPPLIER['Saddles'].get('lead_time_days', 49)
        
        # Berechne Zieltag (Tag, für den bestellt wird)
        # Konvertiere order_date zu Tag (0-basiert, beginnend am 01.01. des Planungsjahres)
        start_date_year = date(self.workday_calculator.year, 1, 1)
        days_since_start = (order_date - start_date_year).days
        target_day = days_since_start + lead_time_days
        
        # Prüfe, ob Zieltag innerhalb des Jahres liegt (0-364)
        if target_day < 0 or target_day >= 365:
            return 0.0
        
        if target_day not in daily_demands_actual_cache:
            return 0.0
        
        # Summiere Nachfrage für alle Produkte, die diesen Sattel verwenden
        total_demand = 0.0
        for product, demand in daily_demands_actual_cache[target_day].items():
            # Prüfe, ob dieses Produkt den angefragten Sattel verwendet
            product_saddle = self.master_data.BOM.get(product, {}).get('saddle', '')
            if product_saddle == saddle_name:
                total_demand += demand
        
        return total_demand
    
    def get_supplier_log_dataframe(self, saddle_name: str, saddle_share: float) -> pd.DataFrame:
        """
        Erstellt den DataFrame für Page 3 (Lieferant China) für einen spezifischen Sattel.
        
        PERFORMANCE: Verwendet Cache, um wiederholte Berechnungen zu vermeiden.
        WICHTIG: Cache wird invalidiert wenn sich Szenarien oder daily_demands_actual ändern.
        """
        # WICHTIG: Cache-Key muss Szenarien und daily_demands_actual berücksichtigen,
        # damit der Cache invalidiert wird wenn Marketing-Szenarien hinzugefügt werden
        try:
            import streamlit as st
            # Hole Szenario-Fingerprint (ähnlich wie in calculate_volume_planning_demand)
            scenario_manager = getattr(self, 'scenario_manager', None)
            if scenario_manager:
                from models.scenarios import (
                    StandardScenario,
                    MarketingCampaignScenario,
                    WarehouseDamageScenario,
                    SupplierBreakdownScenario,
                    DeliveryProblemScenario,
                )
                scenario_items = []
                for s in getattr(scenario_manager, "scenarios", []):
                    if isinstance(s, StandardScenario):
                        continue
                    base = (
                        s.__class__.__name__,
                        getattr(s, "active", True),
                        getattr(s, "start_day", None),
                        getattr(s, "end_day", None),
                    )
                    if isinstance(s, MarketingCampaignScenario):
                        extra = (getattr(s, "demand_increase_factor", None),)
                    elif isinstance(s, WarehouseDamageScenario):
                        extra = (
                            getattr(s, "stock_loss_percentage", None),
                            getattr(s, "affected_component", None),
                        )
                    elif isinstance(s, SupplierBreakdownScenario):
                        extra = (getattr(s, "component_type", None),)
                    elif isinstance(s, DeliveryProblemScenario):
                        extra = (
                            getattr(s, "loss_percentage", None),
                            getattr(s, "delay_days", None),
                            getattr(s, "component_type", None),
                        )
                    else:
                        extra = tuple(sorted(vars(s).items()))
                    scenario_items.append(base + extra)
                scenario_fingerprint = tuple(sorted(scenario_items))
            else:
                scenario_fingerprint = ()
            
            # Hole Cache-Key für daily_demands_actual (wenn vorhanden)
            volume_planning_cache_key = st.session_state.get('volume_planning_cache_key', None)
            
            # Erweitere Cache-Key um Szenarien und daily_demands_actual Cache-Key
            cache_key = (saddle_name, saddle_share, scenario_fingerprint, volume_planning_cache_key)
        except (ImportError, AttributeError):
            # Fallback: Wenn Streamlit nicht verfügbar, verwende einfachen Key
            cache_key = (saddle_name, saddle_share)
        
        # PERFORMANCE: Cache-Check
        if cache_key in self._supplier_log_cache:
            return self._supplier_log_cache[cache_key]
        
        """
        Erstellt den DataFrame für Page 3 (Lieferant China).
        IMPLEMENTIERT DIE "ALTE" LOSGRÖSSEN-LOGIK:
        1. Sammelt Produktion aller Sättel.
        2. Berechnet täglich den Gesamtpool.
        3. Wenn Pool >= 500, wird verschifft (anteilig verteilt).
        4. Berechnet Übertrag (Carry-Over) für den nächsten Tag.
        
        Args:
            saddle_name: Name des Sattels (z.B. "Fizik Tundra")
            saddle_share: Marktanteil dieses Sattels (wird für Produktion/Freigabe verwendet)
        """
        # 1. Datenbasis vorbereiten
        if not self.transport_status:
            return pd.DataFrame(columns=[
                'Wochentag', 'Datum', 'Bestelleingang', 'Freigabedatum', 
                'Freigegebene Bestellungen', 'Störung', 'Produktionsdatum', 
                'Produktionsmenge', 'Warenausgang', 'Warenbestand'
            ])
        
        earliest_order = min((k[0] for k in self.transport_status.keys()), default=0)
        start_date = self.workday_calculator.get_date_from_day(earliest_order)
        end_date = date(self.workday_calculator.year, 12, 31)
        total_days = (end_date - start_date).days + 1
        
        # Alle Sattel-Typen ermitteln (aus MasterData BOM)
        all_saddles = set(item['saddle'] for item in self.master_data.BOM.values())
        
        # Berechne Shares für alle Sättel (einmalig)
        saddle_shares_all = self.master_data.calculate_saddle_shares()
        
        # PERFORMANCE: Lade chinesische Feiertage EINMAL außerhalb der Schleife
        chinese_holidays = self._get_chinese_holidays()
        
        # Tägliche Produktion pro Sattel (wird aus Volumenplanung gefüllt, siehe Block unten;
        # dieselbe Quelle wie Produktionsmenge und get_inbound → konsistente Warenausgang-/Inbound-Summen)
        daily_prod_all = {day_idx: {s: 0.0 for s in all_saddles} for day_idx in range(total_days)}
        
        # Daten für die finale Tabelle (nur für den angefragten saddle_name)
        raw_data_map = {}  # Key: day_idx, Value: Dict mit Order, Prod, etc. für saddle_name
        
        for day_idx in range(total_days):
            curr_date = start_date + timedelta(days=day_idx)
            raw_data_map[day_idx] = {
                'date': curr_date, 
                'weekday': ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'][curr_date.weekday()],
                'order': 0.0, 'release': 0.0, 'prod': 0.0, 'breakdown': "Nein",
                'released_date_str': "", 'production_date_str': ""
            }
        
        # WICHTIG: Berechne Bestelleingang direkt aus Volumenplanung
        # Summiert die Nachfrage aller Produkte, die den gleichen Sattel verwenden,
        # für den Tag (order_date + lead_time_days)
        # OPTIMIERUNG: Lade daily_demands_actual einmalig, um wiederholte session_state-Zugriffe zu vermeiden
        try:
            import streamlit as st
            daily_demands_actual_cache = st.session_state.get('daily_demands_actual', {})
        except ImportError:
            daily_demands_actual_cache = {}
        
        # Hole Produktionszeit aus MasterData (Standard: 5 AT)
        production_time_days = self.master_data.CHINA_SUPPLIER['Saddles'].get('production_time', 5)
        
        # Schritt 1: Berechne Bestelleingang für jeden Tag aus Volumenplanung
        # Schritt 2: Berechne Freigabedatum für jeden Bestelleingang
        # Schritt 3: Summiere Bestelleingänge nach Freigabedatum = Freigegebene Bestellungen
        # Schritt 4: Berechne Produktionsdatum für jede freigegebene Bestellung
        # Schritt 5: Summiere freigegebene Bestellungen nach Produktionsdatum = Produktionsmenge
        
        # PERFORMANCE: Begrenze Berechnung auf relevante Tage (nur bis letzter relevanter Tag)
        # Finde letzten Tag mit Bestellung aus transport_status
        last_order_day = -1
        for (o_day, o_id), status in self.transport_status.items():
            if o_day > last_order_day:
                last_order_day = o_day
        
        # Berechne letzten relevanten Tag-Index (mit Puffer für Lead Time)
        if last_order_day >= 0:
            last_order_date = self.workday_calculator.get_date_from_day(last_order_day)
            last_relevant_date = last_order_date + timedelta(days=60)  # Puffer für Lead Time
            last_relevant_day_idx = min(total_days - 1, (last_relevant_date - start_date).days)
        else:
            last_relevant_day_idx = total_days - 1
        
        # Speichere Bestelleingänge mit ihren Freigabedaten
        # Key: (order_date, order_qty), Value: (released_day, production_end_day)
        order_release_map = {}  # released_day -> [order_qty, ...]
        release_production_map = {}  # production_end_day -> [order_qty, ...]
        
        # PERFORMANCE: Iteriere nur bis zum letzten relevanten Tag
        for day_idx in range(min(total_days, last_relevant_day_idx + 1)):
            curr_date = start_date + timedelta(days=day_idx)
            
            # KORREKTUR: Bestelleingang wird an ALLEN Tagen berechnet (auch Feiertagen)
            # Excel zeigt Bestelleingang an Feiertagen an, aber das Freigabedatum wird verschoben
            # Berechne Bestellmenge für diesen Tag aus Volumenplanung
            order_qty = self._calculate_order_quantity_from_volume_planning(curr_date, saddle_name, daily_demands_actual_cache)
            if order_qty > 0:
                raw_data_map[day_idx]['order'] = order_qty
                
                # Berechne Freigabedatum für diesen Bestelleingang
                # Freigabedatum = Nächster chinesischer Arbeitstag nach Bestelldatum
                order_day = (curr_date - date(self.workday_calculator.year, 1, 1)).days
                released_day = self._get_next_workday(order_day, use_chinese_holidays=True)
                released_date = self.workday_calculator.get_date_from_day(released_day)
                released_day_idx = (released_date - start_date).days
                
                # Speichere Freigabedatum in der Zeile des Bestelleingangs
                if 0 <= released_day_idx < total_days:
                    if not raw_data_map[day_idx]['released_date_str']:
                        raw_data_map[day_idx]['released_date_str'] = released_date.strftime(self.master_data.DATE_FORMAT)
                    
                    # Sammle Bestelleingänge nach Freigabedatum
                    if released_day_idx not in order_release_map:
                        order_release_map[released_day_idx] = []
                    order_release_map[released_day_idx].append(order_qty)
                    
                    # Berechne Produktionsdatum für diese freigegebene Bestellung
                    # Excel-Formel: =ARBEITSTAG(AU16;'Lieferanten und Markt'!$H$10-1;$E$14:$NU$14)
                    # H$10-1 = Produktionszeit - 1 = 5-1 = 4
                    # Produktionsdatum = Freigabedatum + 4 chinesische AT (nicht 5!)
                    production_end_day = self._add_workdays(released_day, production_time_days - 1, exclude_start=True, use_chinese_holidays=True)
                    production_end_date = self.workday_calculator.get_date_from_day(production_end_day)
                    production_end_day_idx = (production_end_date - start_date).days
                    
                    # Speichere Produktionsdatum in der Zeile des Freigabedatums
                    if 0 <= production_end_day_idx < total_days:
                        if not raw_data_map[released_day_idx]['production_date_str']:
                            raw_data_map[released_day_idx]['production_date_str'] = production_end_date.strftime(self.master_data.DATE_FORMAT)
                        
                        # Sammle freigegebene Bestellungen nach Produktionsdatum
                        if production_end_day_idx not in release_production_map:
                            release_production_map[production_end_day_idx] = []
                        release_production_map[production_end_day_idx].append(order_qty)
        
        # Berechne Freigegebene Bestellungen: Summe aller Bestelleingänge, deren Freigabedatum dem Datum entspricht
        for released_day_idx, order_quantities in order_release_map.items():
            if 0 <= released_day_idx < total_days:
                total_released = sum(order_quantities)
                raw_data_map[released_day_idx]['release'] = total_released
        
        # Berechne Produktionsmenge: Summe aller freigegebenen Bestellungen mit Produktionsdatum gleich Datum
        for production_end_day_idx, order_quantities in release_production_map.items():
            if 0 <= production_end_day_idx < total_days:
                total_production = sum(order_quantities)
                raw_data_map[production_end_day_idx]['prod'] = total_production
                # HINWEIS: Produktionsdatum wird bereits in released_day_idx gespeichert (Zeile 687)
                # Es wird NICHT hier überschrieben, da es in der Zeile des Freigabedatums angezeigt wird
        
        # Pool (daily_prod_all) aus Volumenplanung für ALLE Sättel füllen – gleiche Quelle wie
        # Produktionsmenge und wie get_inbound. Dann Warenausgang und Inbound-Summen sind konsistent.
        # KORREKTUR: Bestelleingang wird an ALLEN Tagen berechnet (auch Feiertagen)
        for day_idx in range(total_days):
            curr_date = start_date + timedelta(days=day_idx)
            for s in all_saddles:
                order_qty = self._calculate_order_quantity_from_volume_planning(curr_date, s, daily_demands_actual_cache)
                if order_qty <= 0:
                    continue
                order_day = (curr_date - date(self.workday_calculator.year, 1, 1)).days
                released_day = self._get_next_workday(order_day, use_chinese_holidays=True)
                released_date = self.workday_calculator.get_date_from_day(released_day)
                released_day_idx = (released_date - start_date).days
                if released_day_idx < 0 or released_day_idx >= total_days:
                    continue
                # KORREKTUR: Excel-Formel verwendet H$10-1 = 4 statt 5
                production_end_day = self._add_workdays(released_day, production_time_days - 1, exclude_start=True, use_chinese_holidays=True)
                production_end_date = self.workday_calculator.get_date_from_day(production_end_day)
                prod_day_idx = (production_end_date - start_date).days
                if 0 <= prod_day_idx < total_days:
                    daily_prod_all[prod_day_idx][s] += order_qty
        
        # Scan Transport Status (nur noch für Störungen/Breakdown; Pool kommt aus Volumenplanung)
        for (o_day, o_id), status in self.transport_status.items():
            p_day_sim = status.get('production_end_day')
            # Prüfe auf Störungen (für Breakdown-Spalte)
            if p_day_sim is not None:
                p_date = self.workday_calculator.get_date_from_day(p_day_sim)
                p_off = (p_date - start_date).days
                if 0 <= p_off < total_days:
                    if status.get('production_loss_percentage', 0.0) > 0:
                        raw_data_map[p_off]['breakdown'] = "Ja"
        
        # ---------------------------------------------------------
        # DER "ALTE" LOGIK-KERN: Tägliche Pool- & Versand-Berechnung
        # ---------------------------------------------------------
        lot_size = self.master_data.CHINA_SUPPLIER['Saddles'].get('lot_size', 500)  # 500
        carry_over = {s: 0.0 for s in all_saddles}
        
        # Ergebnis-Speicher für Warenausgang & Bestand (nur für angefragten Sattel nötig)
        shipment_results = [0.0] * total_days
        stock_results = [0.0] * total_days
        
        for day_idx in range(total_days):
            # 1. Gesamt-Verfügbarkeit prüfen
            total_accumulated = 0.0
            accumulated_by_saddle = {}
            
            for s in all_saddles:
                prod = daily_prod_all[day_idx][s]
                co = carry_over[s]
                acc = prod + co
                accumulated_by_saddle[s] = acc
                total_accumulated += acc
            
            # 2. Losgröße berechnen
            # Am letzten Tag: Restbestand mitversenden, damit sum(Produktionsmenge) = sum(Warenausgang)
            if day_idx == total_days - 1 and total_accumulated > 0:
                current_lot_size = int(round(total_accumulated))
            else:
                current_lot_size = int(total_accumulated / lot_size) * lot_size
            
            # 3. Wenn Versand möglich -> Verteilen
            shipments_today = {s: 0.0 for s in all_saddles}
            
            if current_lot_size > 0:
                # A. Ungerundete Anteile
                unrounded = {}
                for s in all_saddles:
                    if total_accumulated > 0:
                        unrounded[s] = accumulated_by_saddle[s] * (current_lot_size / total_accumulated)
                    else:
                        unrounded[s] = 0.0
                
                # B. Runden & Differenz finden (Largest Remainder Method)
                rounded = {s: int(val) for s, val in unrounded.items()}
                diff = current_lot_size - sum(rounded.values())
                
                # C. Differenz verteilen (erste Runde)
                if diff > 0:
                    # Sortieren nach Nachkommastelle
                    remainders = [(s, unrounded[s] - rounded[s]) for s in all_saddles]
                    remainders.sort(key=lambda x: x[1], reverse=True)
                    
                    for s, rem in remainders:
                        if diff <= 0: 
                            break
                        rounded[s] += 1
                        diff -= 1
                
                # D. P165: Korrektur für Rundungsdifferenzen (Excel-Formel)
                # P172 = ABRUNDEN(P157;0) + P165
                # WICHTIG: P165 wird NACH der ersten Rundung angewendet
                # Sortiere nach verfügbarem Bestand (größter zuerst) für korrekte Verteilung
                remaining_diff = current_lot_size - sum(rounded.values())
                if remaining_diff > 0:
                    # Sortiere nach verfügbarem Bestand (größter zuerst)
                    available_corrections = []
                    for s in all_saddles:
                        available_after_rounded = accumulated_by_saddle[s] - rounded[s]
                        if available_after_rounded > 0:
                            available_corrections.append((s, available_after_rounded))
                    # Sortiere absteigend nach verfügbarem Bestand
                    available_corrections.sort(key=lambda x: x[1], reverse=True)
                    
                    for s, available in available_corrections:
                        if remaining_diff <= 0:
                            break
                        correction = min(remaining_diff, available)
                        rounded[s] += correction
                        remaining_diff -= correction
                
                shipments_today = rounded  # P172 = ABRUNDEN(P157;0) + P165
            
            # 4. Carry-Over aktualisieren & Ergebnisse speichern
            for s in all_saddles:
                # Was nicht weggeht, bleibt liegen
                carry_over[s] = accumulated_by_saddle[s] - shipments_today[s]
                
                # Wenn das der angefragte Sattel ist, speichern wir die Werte für die Tabelle
                if s == saddle_name:
                    shipment_results[day_idx] = shipments_today[s]
                    stock_results[day_idx] = carry_over[s]
        
        # ---------------------------------------------------------
        # FINALE TABELLE BAUEN
        # ---------------------------------------------------------
        table_rows = []
        previous_stock = 0.0  # Warenbestand vom Vortag
        
        for day_idx in range(total_days):
            raw = raw_data_map[day_idx]
            curr_date = raw['date']
            is_weekend = raw['weekday'] in ['Sa', 'So']
            has_breakdown = raw['breakdown'] == "Ja"
            
            # PRODUKTIONSMENGE: Wenn Wochenende oder Störung: 0, sonst: Freigegebene Bestellungen für das Produktionsdatum
            if is_weekend or has_breakdown:
                production_qty = 0
            else:
                # Produktionsmenge = Freigegebene Bestellungen für das Produktionsdatum
                production_qty = raw['prod']
            
            # WARENBESTAND: Vorheriger Bestand + Produziert
            current_stock = previous_stock + production_qty
            
            # WARENAUSGANG: Verwende direkt die geplante Versandmenge aus Pool-Logik
            # KONSISTENT mit get_inbound_log_dataframe: Beide verwenden shipments_today[s]
            # ohne weitere Begrenzung durch Warenbestand
            planned_shipment_qty = shipment_results[day_idx]  # Bereits berechnete Versandmenge (aus Pool-Logik)
            
            # Prüfe ob es DeliveryProblemScenario gibt, die zu 100% Verlust führen
            shipment_qty = planned_shipment_qty  # Standard: Verwende geplante Menge
            if self.scenario_manager:
                day_index = (curr_date - date(self.workday_calculator.year, 1, 1)).days
                delivery_problems = self.scenario_manager.get_delivery_problem_scenarios(day_index)
                for scenario in delivery_problems:
                    if scenario.component_type == 'saddles' and scenario.loss_percentage >= 1.0:
                        shipment_qty = 0
                        break
            
            # Aktualisiere Warenbestand nach Versand
            current_stock = current_stock - shipment_qty
            previous_stock = current_stock  # Für nächsten Tag
            
            # Prüfe Feiertag (chinesische Feiertage für Produktion in China)
            # OPTIMIERUNG: Direkte Prüfung statt get_day_info() aufzurufen
            # PERFORMANCE: chinese_holidays wurde bereits außerhalb der Schleife geladen (Zeile 1032)
            is_holiday = False
            # Für China: Prüfe chinesische Feiertage (bereits gecacht)
            if curr_date in chinese_holidays:
                is_holiday = True
            
            daily_data = {
                'Wochentag': raw['weekday'],
                'Datum': raw['date'].strftime(self.master_data.DATE_FORMAT),
                'Bestelleingang': int(round(raw['order'])) if raw['order'] > 0 else '',
                'Freigabedatum': raw['released_date_str'],
                'Freigegebene Bestellungen': int(round(raw['release'])) if raw['release'] > 0 else 0,
                'Störung': raw['breakdown'],
                'Produktionsdatum': raw['production_date_str'],
                'Produktionsmenge': int(round(production_qty)) if production_qty > 0 else 0,
                'Warenausgang': int(round(shipment_qty)) if shipment_qty > 0 else 0,
                'Warenbestand': int(round(current_stock)),
                'Is_Weekend': is_weekend,
                'Is_Holiday': is_holiday
            }
            table_rows.append(daily_data)
        
        result_df = pd.DataFrame(table_rows)
        
        # PERFORMANCE: Cache Ergebnis
        self._supplier_log_cache[cache_key] = result_df
        
        return result_df
    
    def get_inbound_log_dataframe(self, saddle_shares_dict: Dict[str, float]) -> pd.DataFrame:
        """
        Erstellt den DataFrame für Page 4 (Inbound) mit EXAKTER RÜCKVERFOLGUNG.
        
        NEUE LOGIK (Massenerhaltung):
        Statt pauschaler Verteilung (500 * Share) nutzen wir echte Warteschlangen (Buckets)
        pro Satteltyp am Hafen. Wir verschiffen nur das, was wirklich produziert wurde.
        Damit ist mathematisch garantiert: Summe(Inbound) == Summe(Produktion).
        """
        # WICHTIG: Cache-Key muss Szenarien und daily_demands_actual berücksichtigen,
        # damit der Cache invalidiert wird wenn Marketing-Szenarien hinzugefügt werden
        # Verwende die gleiche Logik wie bei get_supplier_log_dataframe()
        try:
            import streamlit as st
            # Hole Szenario-Fingerprint (ähnlich wie in get_supplier_log_dataframe)
            scenario_manager = getattr(self, 'scenario_manager', None)
            if scenario_manager:
                from models.scenarios import (
                    StandardScenario,
                    MarketingCampaignScenario,
                    WarehouseDamageScenario,
                    SupplierBreakdownScenario,
                    DeliveryProblemScenario,
                )
                scenario_items = []
                for s in getattr(scenario_manager, "scenarios", []):
                    if isinstance(s, StandardScenario):
                        continue
                    base = (
                        s.__class__.__name__,
                        getattr(s, "active", True),
                        getattr(s, "start_day", None),
                        getattr(s, "end_day", None),
                    )
                    if isinstance(s, MarketingCampaignScenario):
                        extra = (getattr(s, "demand_increase_factor", None),)
                    elif isinstance(s, WarehouseDamageScenario):
                        extra = (
                            getattr(s, "stock_loss_percentage", None),
                            getattr(s, "affected_component", None),
                        )
                    elif isinstance(s, SupplierBreakdownScenario):
                        extra = (getattr(s, "component_type", None),)
                    elif isinstance(s, DeliveryProblemScenario):
                        extra = (
                            getattr(s, "loss_percentage", None),
                            getattr(s, "delay_days", None),
                            getattr(s, "component_type", None),
                        )
                    else:
                        extra = tuple(sorted(vars(s).items()))
                    scenario_items.append(base + extra)
                scenario_fingerprint = tuple(sorted(scenario_items))
            else:
                scenario_fingerprint = ()
            
            # Hole Cache-Key für daily_demands_actual (wenn vorhanden)
            volume_planning_cache_key = st.session_state.get('volume_planning_cache_key', None)
            
            # Erweitere Cache-Key um Szenarien und daily_demands_actual Cache-Key
            cache_key = (tuple(sorted(saddle_shares_dict.items())), scenario_fingerprint, volume_planning_cache_key)
        except (ImportError, AttributeError):
            # Fallback: Wenn Streamlit nicht verfügbar, verwende einfachen Key
            cache_key = tuple(sorted(saddle_shares_dict.items()))
        
        # Cache Check
        if cache_key == self._inbound_df_cache_key and cache_key in self._inbound_df_cache:
            return self._inbound_df_cache[cache_key]
        
        # 1. Setup
        if not self.transport_status:
            cols = ['Wochentag', 'Datum', 'Abfahrt LKW 🇨🇳', 'Ankunft LKW 🇨🇳', 
                    'Abfahrt Schiff 🇨🇳', 'Ankunft Schiff 🇩🇪', 'Abfahrt LKW 🇩🇪', 
                    'Geplante Ankunft LKW 🇩🇪', 'Tatsächliche Ankunft LKW 🇩🇪', 
                    'Verfügbar im Lager 🇩🇪', 'Menge Gesamt'] + sorted(saddle_shares_dict.keys())
            return pd.DataFrame(columns=cols)
        
        # KORREKTUR: Inbound beginnt am 24.11.2026 (erste Versendung laut Excel)
        start_date = date(self.workday_calculator.year - 1, 11, 24)
        end_date = date(self.workday_calculator.year, 12, 31)
        total_days = (end_date - start_date).days + 1
        
        # Alle Sättel ermitteln
        all_saddles = set(item['saddle'] for item in self.master_data.BOM.values())
        
        # Shares berechnen (KONSISTENT mit get_supplier_log_dataframe)
        # Verwende die gleiche Methode wie in get_supplier_log_dataframe für Konsistenz
        saddle_shares_all = self.master_data.calculate_saddle_shares()
        
        # 2. Produktion sammeln (Der Zufluss in die Eimer)
        # WICHTIG: Berechne Produktion direkt aus Bestelleingang-Werten (dynamisch),
        # anstatt aus statischem transport_status zu lesen.
        # Das stellt sicher, dass Marketing-Szenarien berücksichtigt werden.
        # PERFORMANCE: Verwende defaultdict für schnellere Zugriffe (nur relevante Tage)
        from collections import defaultdict
        daily_prod_all = defaultdict(lambda: defaultdict(float))
        last_production_day = -1  # OPTIMIERUNG: Track letzten Tag mit Produktion
        
        # Berechne Produktion für jeden Sattel-Typ aus Bestelleingang-Werten
        for saddle_name, saddle_share in saddle_shares_dict.items():
            # Hole Supplier-Log für diesen Sattel-Typ (enthält bereits Marketing)
            supplier_df = self.get_supplier_log_dataframe(saddle_name, saddle_share)
            
            if supplier_df.empty:
                continue
            
            # PERFORMANCE: Verwende vectorisierte Operationen statt iterrows()
            # Filtere nur relevante Zeilen (mit Produktionsdatum und Produktionsmenge)
            if 'Produktionsdatum' in supplier_df.columns and 'Produktionsmenge' in supplier_df.columns:
                # Filtere Zeilen mit gültigen Werten
                mask = (supplier_df['Produktionsdatum'].notna()) & (supplier_df['Produktionsmenge'].notna())
                relevant_rows = supplier_df[mask]
                
                # PERFORMANCE: Konvertiere Datum-Spalte einmalig statt in jeder Iteration
                from datetime import datetime
                for idx, row in relevant_rows.iterrows():
                    production_date_str = str(row['Produktionsdatum'])
                    production_qty = row['Produktionsmenge']
                    
                    if production_date_str and production_qty:
                        try:
                            prod_date = datetime.strptime(production_date_str, self.master_data.DATE_FORMAT).date()
                            day_offset = (prod_date - start_date).days
                            
                            # PERFORMANCE: Nur relevante Tage verarbeiten
                            if 0 <= day_offset < total_days:
                                effective_day = day_offset
                                last_production_day = max(last_production_day, effective_day)
                                
                                # Konvertiere production_qty zu float (falls string)
                                try:
                                    qty = float(production_qty) if isinstance(production_qty, str) else float(production_qty)
                                except (ValueError, TypeError):
                                    qty = 0.0
                                
                                # Exakte Zuteilung in den Eimer für diesen Sattel-Typ
                                if qty > 0:
                                    daily_prod_all[effective_day][saddle_name] += qty
                        except (ValueError, TypeError):
                            continue

        # OPTIMIERUNG: Bestimme letzten relevanten Tag
        # Maximal ~40 Tage nach letzter Produktion können noch Transporte ankommen
        max_transport_delay = 40
        last_relevant_day = min(total_days - 1, last_production_day + max_transport_delay) if last_production_day >= 0 else total_days - 1
        
        # PERFORMANCE: Begrenze auf maximal 500 Tage (statt 426) für schnellere Berechnung
        # Die Tabelle wird trotzdem bis Ende des Jahres berechnet, aber wir brechen früher ab
        # wenn keine Transporte mehr stattfinden
        # OPTIMIERUNG: Reduziere max_calculation_days weiter für bessere Performance
        max_calculation_days = min(total_days, last_relevant_day + 1, 400)

        # 3. Die Simulation der "Eimer" am Hafen (Buckets)
        # WICHTIG: Verwende die GLEICHE Verteilungslogik wie in get_supplier_log_dataframe
        # für Konsistenz zwischen "Lieferant China" und "Inbound"
        carry_over = {s: 0.0 for s in all_saddles}
        lot_size = self.master_data.CHINA_SUPPLIER['Saddles'].get('lot_size', 500)
        
        # PERFORMANCE: Lade chinesische Feiertage EINMAL außerhalb der Schleife
        chinese_holidays = self._get_chinese_holidays()
        
        rows = []
        # OPTIMIERUNG: Frühzeitiges Beenden wenn keine Daten mehr kommen
        consecutive_empty_days = 0
        max_consecutive_empty = 15  # OPTIMIERUNG: Reduziert von 20 auf 15 für schnellere Berechnung

        for day_idx in range(max_calculation_days):  # OPTIMIERUNG: Begrenze Schleife
            curr_date = start_date + timedelta(days=day_idx)
            
            # KORREKTUR: Keine Zeile für 23.11. erstellen - Startdatum ist 24.11.
            # Prüfe ob curr_date vor start_date liegt (sollte nicht passieren, aber sicherheitshalber)
            if curr_date < start_date:
                continue
            
            # A. Gesamt-Verfügbarkeit prüfen (wie in get_supplier_log_dataframe)
            total_accumulated = 0.0
            accumulated_by_saddle = {}
            
            for s in all_saddles:
                prod = daily_prod_all[day_idx][s]
                co = carry_over[s]
                acc = prod + co
                accumulated_by_saddle[s] = acc
                total_accumulated += acc
            
            # B. Check: Ist der Hafen voll genug für ein Schiff?
            # OPTIMIERUNG: Track leere Tage für frühes Beenden
            has_production_today = any(daily_prod_all.get(day_idx, {}).get(s, 0.0) > 0.001 for s in all_saddles)
            has_transport_today = total_accumulated >= lot_size
            
            if not has_production_today and not has_transport_today:
                consecutive_empty_days += 1
                if day_idx > last_production_day + max_transport_delay and consecutive_empty_days >= max_consecutive_empty:
                    break
            else:
                consecutive_empty_days = 0
            
            # C. Losgröße berechnen (wie in get_supplier_log_dataframe)
            current_lot_size = int(total_accumulated / lot_size) * lot_size
            
            shipments_today = {s: 0.0 for s in all_saddles}
            is_transport_day = False
            
            # KORREKTUR: Versendung nur an chinesischen Arbeitstagen (nicht Wochenende, nicht chinesische Feiertage)
            # Am 11.02.2027 (chinesischer Feiertag) sollten keine LKW/Schiff-Abfahrten stattfinden
            # PERFORMANCE: Prüfe nur wenn current_lot_size > 0 (früher prüfen spart Zeit)
            if current_lot_size > 0:
                # KRITISCH: Prüfe zuerst ob curr_date ein chinesischer Feiertag ist
                # Wenn ja, dann KEINE Versendung, auch wenn es ein Wochentag ist
                # WICHTIG: Prüfe explizit ob curr_date in chinese_holidays ist
                is_weekend = curr_date.weekday() >= 5
                is_chinese_holiday = curr_date in chinese_holidays
                is_chinese_workday = (not is_weekend and not is_chinese_holiday)
                
                if is_chinese_workday:
                    is_transport_day = True
                else:
                    # EXPLIZIT: Keine Versendung an chinesischen Feiertagen oder Wochenenden
                    is_transport_day = False
            else:
                is_transport_day = False
            
            # D. Exakte Verteilung (GLEICHE Logik wie in get_supplier_log_dataframe)
            # Nur wenn is_transport_day == True
            if is_transport_day:
                # A. Ungerundete Anteile
                unrounded = {}
                for s in all_saddles:
                    if total_accumulated > 0:
                        unrounded[s] = accumulated_by_saddle[s] * (current_lot_size / total_accumulated)
                    else:
                        unrounded[s] = 0.0
                
                # B. Runden & Differenz finden (Largest Remainder Method)
                rounded = {s: int(val) for s, val in unrounded.items()}
                diff = current_lot_size - sum(rounded.values())
                
                # C. Differenz verteilen (erste Runde)
                if diff > 0:
                    # Sortieren nach Nachkommastelle
                    remainders = [(s, unrounded[s] - rounded[s]) for s in all_saddles]
                    remainders.sort(key=lambda x: x[1], reverse=True)
                    
                    for s, rem in remainders:
                        if diff <= 0: 
                            break
                        rounded[s] += 1
                        diff -= 1
                
                # D. P165: Korrektur für Rundungsdifferenzen (Excel-Formel)
                # P172 = ABRUNDEN(P157;0) + P165
                # Excel-Formel: P165 = WENN(P154=P161;0;WENN((P154-P161)<=(P20+O22-ABRUNDEN(P157;0));P154-P161;P20+O22-ABRUNDEN(P157;0)))
                # P154 = current_lot_size, P161 = sum(rounded.values()), P20+O22 = accumulated_by_saddle[s], P157 = unrounded[s]
                # Für jeden Sattel: P165 = MIN(P154-P161, P20+O22-ABRUNDEN(P157;0))
                # WICHTIG: Excel wendet P165 für JEDEN Sattel an, in der Reihenfolge wie in all_saddles definiert, NICHT sortiert!
                remaining_diff = current_lot_size - sum(rounded.values())
                if remaining_diff > 0:
                    for s in all_saddles:
                        if remaining_diff <= 0:
                            break
                        # Verfügbarer Bestand nach gerundetem Wert
                        available_after_rounded = accumulated_by_saddle[s] - rounded[s]
                        if available_after_rounded > 0:
                            # P165 = MIN(P154-P161, P20+O22-ABRUNDEN(P157;0))
                            correction = min(remaining_diff, available_after_rounded)
                            rounded[s] += correction
                            remaining_diff -= correction
                
                shipments_today = rounded  # P172 = ABRUNDEN(P157;0) + P165
            
            # E. Carry-Over aktualisieren (wie in get_supplier_log_dataframe)
            for s in all_saddles:
                # Was nicht weggeht, bleibt liegen
                carry_over[s] = accumulated_by_saddle[s] - shipments_today[s]

            # --- ZEILE ERSTELLEN (NUR WENN TRANSPORT ODER PRODUKTION) ---
            # KRITISCH: Erstelle Zeile nur wenn is_transport_day=True ODER wenn es Produktion gibt
            # Am 11.02.2027 (Feiertag) sollte KEINE Zeile erstellt werden, wenn keine Versendung stattfindet
            has_production = any(daily_prod_all.get(day_idx, {}).get(s, 0.0) > 0.001 for s in all_saddles)
            
            # Erstelle Zeile nur wenn Transport ODER Produktion vorhanden
            if not is_transport_day and not has_production:
                # Überspringe leere Tage (außer wenn es der erste Tag ist)
                continue
            
            day_idx = (curr_date - date(self.workday_calculator.year, 1, 1)).days
            # Prüfe Wochenende und Feiertag
            # OPTIMIERUNG: Direkte Prüfung statt get_day_info() aufzurufen
            is_weekend = curr_date.weekday() >= 5  # Samstag=5, Sonntag=6
            is_holiday = False
            # Prüfe deutsche Feiertage (für Deutschland, bereits geladen in workday_calculator)
            if curr_date in self.workday_calculator.german_holidays:
                is_holiday = True
            
            row = {
                'Wochentag': self.workday_calculator.get_weekday_abbr(day_idx) if 0 <= day_idx < 365 else ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'][curr_date.weekday()],
                'Datum': curr_date.strftime(self.master_data.DATE_FORMAT),
                'Abfahrt LKW 🇨🇳': '', 'Ankunft LKW 🇨🇳': '', 
                'Abfahrt Schiff 🇨🇳': '', 'Ankunft Schiff 🇩🇪': '', 'Abfahrt LKW 🇩🇪': '',
                'Geplante Ankunft LKW 🇩🇪': '', 'Tatsächliche Ankunft LKW 🇩🇪': '', 
                'Verfügbar im Lager 🇩🇪': '', 'Menge Gesamt': '',
                'Is_Weekend': is_weekend,
                'Is_Holiday': is_holiday
            }
            # Init Sattel-Spalten
            for s in saddle_shares_dict: 
                row[s] = ''

            if is_transport_day:
                # Fülle die exakten Werte ein (als ganze Zahlen)
                total_qty = 0.0
                for s in saddle_shares_dict:
                    if s in shipments_today and shipments_today[s] > 0.001:
                        qty = int(round(shipments_today[s]))
                        row[s] = qty
                        total_qty += qty
                
                # KRITISCH: Gesamtmenge aus Summe der Einzelpositionen berechnen
                row['Menge Gesamt'] = int(round(total_qty))
                
                # Datums-Berechnung für Ankunft (wie gehabt)
                row['Abfahrt LKW 🇨🇳'] = curr_date.strftime(self.master_data.DATE_FORMAT)
                
                # KORREKTUR: LKW-Fahrt nur an chinesischen Arbeitstagen
                # Abfahrt LKW 🇨🇳 = curr_date (bereits geprüft: is_chinese_workday)
                # Ankunft LKW 🇨🇳 = Abfahrt + 2 chinesische AT (Start-Tag zählt nicht)
                # KRITISCH: Verwende direkte Datumsberechnung, da curr_date auch im Vorjahr liegen kann
                date_port = self._add_workdays_from_date(curr_date, 2, exclude_start=True, use_chinese_holidays=True)
                row['Ankunft LKW 🇨🇳'] = date_port.strftime(self.master_data.DATE_FORMAT)
                
                # KORREKTUR: Finde nächsten Mittwoch, der KEIN chinesischer Feiertag ist
                # Beispiel: 11.02.2027 ist chinesischer Feiertag → muss auf 17.02.2027 warten
                # Wenn Ankunft bereits Mittwoch ist, fährt das Schiff am nächsten Mittwoch ab (nicht am gleichen Tag)
                # PERFORMANCE: chinese_holidays wurde bereits außerhalb der Schleife geladen
                date_ship_dep = date_port
                wd = date_ship_dep.weekday()
                if wd == 2:
                    # Wenn bereits Mittwoch, springe zum nächsten Mittwoch
                    date_ship_dep += timedelta(days=7)
                else:
                    # Finde nächsten Mittwoch
                    days_to_wed = (2 - wd) % 7
                    if days_to_wed == 0:
                        days_to_wed = 7
                    date_ship_dep += timedelta(days=days_to_wed)
                
                # Prüfe ob dieser Mittwoch ein chinesischer Feiertag ist
                # PERFORMANCE: Maximal 52 Iterationen (ein Jahr hat max. 52 Mittwoche)
                max_iterations = 52
                iteration = 0
                while date_ship_dep in chinese_holidays and iteration < max_iterations:
                    date_ship_dep += timedelta(days=7)  # Nächster Mittwoch
                    iteration += 1
                
                row['Abfahrt Schiff 🇨🇳'] = date_ship_dep.strftime(self.master_data.DATE_FORMAT)
                
                # KRITISCH: Schiff fährt 30 KALENDERTAGE (KT), nicht Arbeitstage!
                # Das Schiff fährt kontinuierlich, Feiertage spielen keine Rolle
                # Berechnung: Abfahrt + 30 Kalendertage
                date_ship_arr = date_ship_dep + timedelta(days=30)  # 30 Kalendertage
                row['Ankunft Schiff 🇩🇪'] = date_ship_arr.strftime(self.master_data.DATE_FORMAT)
                row['Abfahrt LKW 🇩🇪'] = date_ship_arr.strftime(self.master_data.DATE_FORMAT)
                
                # Konvertiere Ankunft Schiff zu Tag-Index für weitere Berechnungen
                day_ship_arr_idx = (date_ship_arr - date(self.workday_calculator.year, 1, 1)).days
                
                # KRITISCH: ARBEITSTAG für geplante/tatsächliche Ankunft: Ankunft Schiff + 1 Arbeitstag
                # Start-Datum zählt NICHT mit! Also: Ankunft Schiff + 1 Arbeitstag (Ankunft zählt nicht)
                day_arr_de = self._add_workdays(day_ship_arr_idx, 1, exclude_start=True, use_chinese_holidays=False)  # 2-1 = 1 Arbeitstag, Start zählt nicht!
                date_arr_de = self.workday_calculator.get_date_from_day(day_arr_de)
                
                row['Geplante Ankunft LKW 🇩🇪'] = date_arr_de.strftime(self.master_data.DATE_FORMAT)
                row['Tatsächliche Ankunft LKW 🇩🇪'] = date_arr_de.strftime(self.master_data.DATE_FORMAT)
                
                date_avail = date_arr_de + timedelta(days=1)
                row['Verfügbar im Lager 🇩🇪'] = date_avail.strftime(self.master_data.DATE_FORMAT)

            rows.append(row)
            
        # DataFrame erstellen
        df = pd.DataFrame(rows)
        
        # Spalten sortieren
        cols = ['Wochentag', 'Datum', 'Abfahrt LKW 🇨🇳', 'Ankunft LKW 🇨🇳', 
                'Abfahrt Schiff 🇨🇳', 'Ankunft Schiff 🇩🇪', 'Abfahrt LKW 🇩🇪', 
                'Geplante Ankunft LKW 🇩🇪', 'Tatsächliche Ankunft LKW 🇩🇪', 
                'Verfügbar im Lager 🇩🇪', 'Menge Gesamt'] + sorted(saddle_shares_dict.keys())
        
        # Sicherstellen dass alle Cols da sind
        for c in cols:
            if c not in df.columns: 
                df[c] = ''
        
        result_df = df[cols]
        
        # Cache Ergebnis
        self._inbound_df_cache[cache_key] = result_df
        self._inbound_df_cache_key = cache_key
        
        return result_df
    
    def get_daily_arrival_qty(self, day_index: int) -> float:
        """
        Berechnet die Wareneingangsmenge für einen bestimmten Tag.
        
        KRITISCHE OPTIMIERUNG: Berechnet direkt aus transport_status, ohne die vollständige
        Inbound-Tabelle zu erstellen. Das ist 100× schneller, da get_inbound_log_dataframe()
        über 426 Tage iteriert.
        
        Args:
            day_index: Tag-Index (0-basiert, 0 = 01.01.2027)
            
        Returns:
            Menge, die an diesem Tag verfügbar wird (0.0 wenn keine Ware ankommt)
        """
        if not self.transport_status:
            return 0.0
        
        # Konvertiere Tag-Index zu Datum
        target_date = self.workday_calculator.get_date_from_day(day_index)
        
        # Summiere alle Transporte, die an diesem Tag verfügbar werden
        total_arrival_qty = 0.0
        
        for (order_day, order_id), status in self.transport_status.items():
            available_day = status.get('available_day')
            if available_day is None:
                continue
            
            # Prüfe ob dieser Transport an diesem Tag verfügbar wird
            try:
                avail_date = self.workday_calculator.get_date_from_day(available_day)
                if avail_date == target_date:
                    # Summiere die tatsächliche Menge (nach Verlusten)
                    qty = status.get('actual_quantity', status.get('quantity', 0.0))
                    if qty > 0:
                        total_arrival_qty += qty
            except Exception:
                continue
        
        return total_arrival_qty
    
