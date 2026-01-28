"""
Production Planner
Intelligenter Produktionsplaner mit Backlog-Tracking und Priorisierung
"""

import math
from typing import Dict, Tuple, Optional
from datetime import datetime, date
from models.inventory import Inventory
from config.master_data import MasterData
from simulation.demand_calculator import DemandCalculator
from simulation.workday_calculator import WorkdayCalculator


class ProductionPlanner:
    """Plant Produktion basierend auf Bottleneck-Logik, Priorisierung und Backlog-Tracking"""
    
    def __init__(
        self, 
        inventory: Inventory,
        demand_calculator: Optional[DemandCalculator] = None,
        workday_calculator: Optional[WorkdayCalculator] = None,
        china_transport_manager = None
    ):
        self.inventory = inventory
        self.master_data = MasterData
        self.demand_calculator = demand_calculator
        self.workday_calculator = workday_calculator
        self.china_transport_manager = china_transport_manager  # Für Inbound-Tabelle-Zugriff
        
        # Gedächtnis: Backlog pro Produkt
        self.backlog: Dict[str, float] = {product: 0.0 for product in self.master_data.BOM.keys()}
        
        # Produktionsplan: Dict[day, Dict[product, quantity]]
        self.production_plan: Dict[int, Dict[str, int]] = {}
        
        # Produktionslogs für UI: Dict[product, List[Dict]]
        self.production_logs: Dict[str, list] = {product: [] for product in self.master_data.BOM.keys()}
        
        # Cache für Inbound-Tabelle (Performance-Optimierung)
        # Key: day, Value: Dict[saddle_name, stock_morning]
        self._inbound_stock_cache: Dict[int, Dict[str, float]] = {}
        
        # PERFORMANCE: Cache für Verteilung pro Tag und Sattel-Typ (wird einmal berechnet)
        # Key: day, Value: Dict[saddle_name, qty]
        # Wird einmal berechnet aus get_inbound_log_dataframe(), dann wiederverwendet
        self._inbound_distribution_cache: Dict[int, Dict[str, float]] = {}
        self._inbound_distribution_initialized: bool = False
        
        # Kumulierter Verbrauch pro Sattel-Typ (für Bestandsreduktion in UI)
        # Key: saddle_name, Value: kumulierter Verbrauch bis Tag X
        self._consumption_by_saddle: Dict[str, float] = {}
        
        # "zu produzierende Mengen" mit Fertigstellungsdatum
        # Key: (completion_day, product), Value: quantity
        # Wird für "Tatsächliche PM" verwendet (1-Tag-Verzögerung)
        self._scheduled_production: Dict[Tuple[int, str], float] = {}
    
    def plan_daily_production(
        self, 
        day: int,
        marketing_add_ons: Dict[str, float] = None,
        scenario_manager = None
    ) -> Dict[str, int]:
        """
        Plant die tägliche Produktion mit intelligenter Priorisierung.
        
        Args:
            day: Tag (0-basiert)
            marketing_add_ons: Optional dict mit Marketing-Add-ons pro Produkt
            scenario_manager: Optional ScenarioManager für Marketing-Szenarien
        
        Returns:
            Dict[product_name, quantity] - Produktionsplan für diesen Tag
        """
        if marketing_add_ons is None:
            marketing_add_ons = {}
        
        # Prüfe ob Arbeitstag (nicht Wochenende und nicht Feiertag)
        is_workday = False
        if self.workday_calculator:
            is_workday = self.workday_calculator.is_workday(day)
        
        if not is_workday:
            # Keine Produktion an Wochenenden oder Feiertagen
            production_by_product = {product: 0 for product in self.master_data.BOM.keys()}
            self.production_plan[day] = production_by_product
            # Logge mit leeren Werten für Wochenende/Feiertag
            empty_zeros = {product: 0 for product in self.master_data.BOM.keys()}
            empty_floats = {product: 0.0 for product in self.master_data.BOM.keys()}
            self._log_production(day, production_by_product, empty_zeros, empty_floats, empty_floats, empty_zeros, 0, 0.0)
            return production_by_product
        
        # 1. Hole Tagesbedarf pro Produkt aus Volumenplanung (Single Source of Truth)
        # WICHTIG: calculate_volume_planning_demand() wird VOR plan_daily_production() aufgerufen,
        # daher sollte daily_demands_actual IMMER verfügbar sein
        product_demands = {}
        
        # Versuche aus Cache zu lesen (Single Source of Truth)
        try:
            import streamlit as st
            daily_demands_actual = st.session_state.get('daily_demands_actual', {})
            if day in daily_demands_actual and daily_demands_actual[day]:
                # Verwende Nachfrage aus Volumenplanung (mit Marketing bereits enthalten)
                product_demands = daily_demands_actual[day].copy()
            else:
                # Cache fehlt - das sollte nicht passieren
                raise ValueError(
                    f"daily_demands_actual fehlt für Tag {day}. "
                    f"Bitte rufen Sie calculate_volume_planning_demand() auf, bevor Sie plan_daily_production() aufrufen."
                )
        except ImportError:
            # Streamlit nicht verfügbar (z.B. Unit-Tests) - verwende DemandCalculator als Fallback
            if self.demand_calculator:
                is_last_workday_of_year = False
                if self.workday_calculator.is_workday(day):
                    has_future_workdays = False
                    for future_day in range(day + 1, 365):
                        if self.workday_calculator.is_workday(future_day):
                            has_future_workdays = True
                            break
                    is_last_workday_of_year = not has_future_workdays
                
                product_demands = self.demand_calculator.calculate_daily_demand_per_product_dict(
                    day, marketing_add_ons, is_last_workday_of_year
                )
            else:
                # Fallback für Unit-Tests ohne DemandCalculator
                total_share = sum(self.master_data.PRODUCT_SALES_SHARES.values())
                estimated_daily_target = self.master_data.GLOBAL_CONFIG.get('total_volume', 370000) / 365
                for product in self.master_data.BOM.keys():
                    share = self.master_data.PRODUCT_SALES_SHARES.get(product, 0.0) / total_share if total_share > 0 else 0
                    product_demands[product] = int(estimated_daily_target * share)
        
        # 2. Addiere Backlog zum Bedarf
        production_demand_by_product = {}
        for product in self.master_data.BOM.keys():
            planned_demand = product_demands.get(product, 0)
            backlog = self.backlog.get(product, 0.0)
            production_demand_by_product[product] = planned_demand + backlog
        
        # 3. Berechne verfügbare Kapazität
        working_hours = self.master_data.GLOBAL_CONFIG.get('working_hours_per_shift', 8)
        capacity_per_hour = self.master_data.GLOBAL_CONFIG.get('capacity_per_hour', 130)
        capacity_per_shift = working_hours * capacity_per_hour
        
        # AGGRESSIVE BACKLOG-RECOVERY: Berechne benötigte Schichten basierend auf Gesamtbedarf (inkl. Backlog!)
        total_demand = sum(production_demand_by_product.values())
        total_backlog = sum(self.backlog.values())
        
        if total_demand > 0:
            # AGGRESSIVE BACKLOG-RECOVERY: Wenn Backlog vorhanden ist, nutze IMMER MAXIMALE Kapazität (3 Schichten)
            if total_backlog > 0:
                # Aggressive Strategie: Fahre IMMER 3 Schichten, wenn Backlog vorhanden ist
                # Dies stellt sicher, dass der Backlog so schnell wie möglich abgearbeitet wird
                shifts = 3  # Maximale Kapazität für Backlog-Aufholung
            else:
                # Normal: Berechne Schichten basierend auf Bedarf
                shifts_needed = math.ceil(total_demand / capacity_per_shift)
                shifts = min(3, max(1, shifts_needed))
        else:
            shifts = 0
        
        daily_capacity = shifts * capacity_per_shift
        
        # 4. Initialisiere Materialverfügbarkeit
        current_saddle_stock = max(0.0, self.inventory.stock_saddles)
        stock_saddles_morning = current_saddle_stock
        
        # Berechne tatsächlichen Bestand pro Sattel-Typ (für Materialprüfung)
        saddle_shares = self.master_data.calculate_saddle_shares()
        
        # Hole tatsächlichen Bestand pro Sattel-Typ aus Inbound-Tabelle (mit Verbrauch)
        stock_by_saddle_type = {}
        if self.china_transport_manager and self.workday_calculator:
            inbound_stocks = self._get_all_stocks_from_inbound_table(day, saddle_shares)
            for s_type in saddle_shares.keys():
                inbound_stock = inbound_stocks.get(s_type, 0.0) or 0.0
                consumption = self._consumption_by_saddle.get(s_type, 0.0)
                stock_by_saddle_type[s_type] = max(0.0, inbound_stock - consumption)
        else:
            for s_type, share in saddle_shares.items():
                stock_by_saddle_type[s_type] = current_saddle_stock * share

        # 5. Anteilige Produktion berechnen
        # FIX: Garantiere deterministische Reihenfolge durch sorted()
        products_list = sorted(self.master_data.BOM.keys())
        total_production_demand = sum(production_demand_by_product.values())
        
        proportional_production_by_product = {}
        for product in products_list:
            demand = production_demand_by_product.get(product, 0.0)
            if total_production_demand > 0:
                # ABRUNDEN(Produktionsbedarf * Kapazität / Gesamtbedarf; 0)
                proportional = math.floor(demand * daily_capacity / total_production_demand)
            else:
                proportional = 0
            proportional_production_by_product[product] = proportional
        
        # 6. Rang Unterstützung und Rang berechnen
        rank_support_by_product = {}
        for idx, product in enumerate(products_list):
            row_number = idx + 1
            proportional = proportional_production_by_product.get(product, 0)
            # Rang_Unterstützung = Anteilige_Produktion + Zeile/1000000
            rank_support = (row_number / 1000000.0) + proportional
            rank_support_by_product[product] = rank_support
        
        # Sortiere Produkte nach Rang (Höchster Support-Wert zuerst = Rang 1)
        sorted_products = sorted(products_list, key=lambda p: rank_support_by_product[p], reverse=True)
        
        # Berechne Rangnummer für Reporting
        rank_by_product = {}
        for i, p in enumerate(sorted_products):
            rank_by_product[p] = i + 1

        # 7. zu produzierende Mengen berechnen (mit dynamischer Materialreduktion)
        # Für Rang 1-4: MIN(Produktionsbedarf, Anteilige_Produktion, Minimale_Produktion)
        # Für Rang 5-8: Zusätzlich + Rest mögliche Produktion
        # WICHTIG: Material wird dynamisch reduziert während der Berechnung
        scheduled_production_by_product = {}
        total_scheduled_so_far = 0.0
        
        # Speichere initiale Materialverfügbarkeit für Anzeige (vor Produktion)
        material_availability_report = {}
        for product in products_list:
            required_saddle_type = self.master_data.BOM[product]['saddle']
            material_availability_report[product] = stock_by_saddle_type.get(required_saddle_type, 0.0)
        
        for product in sorted_products:
            demand = production_demand_by_product.get(product, 0.0)
            proportional = proportional_production_by_product.get(product, 0)
            rank = rank_by_product.get(product, 999)
            
            if demand <= 0:
                scheduled_production_by_product[product] = 0.0
                continue
            
            # KRITISCH: Berechne "Minimale Produktion" dynamisch (nach Materialverbrauch vorheriger Produkte)
            # MIN(Frame_Verfügbar, Sattel_Verfügbar, Gabel_Verfügbar)
            required_saddle_type = self.master_data.BOM[product]['saddle']
            saddle_available = stock_by_saddle_type.get(required_saddle_type, 0.0)
            # Frames und Gabeln sind unbegrenzt (∞), daher nur Sattel-Limit
            minimal = max(0.0, saddle_available)
            
            # Für Rang 1-4: MIN(Bedarf, Anteilige, Minimale)
            if rank <= 4:
                scheduled_qty = min(demand, proportional, minimal)
            else:
                # Für Rang 5-8: MIN(Bedarf, Anteilige, Minimale) + Rest-Verteilung
                base_qty = min(demand, proportional, minimal)
                
                # Wenn Summe < Kapazität: MIN(Rest_Kapazität, Minimale, Rest_Bedarf), sonst 0
                remaining_capacity = daily_capacity - total_scheduled_so_far
                remaining_demand = max(0.0, demand - base_qty)  # Stelle sicher, dass es nicht negativ ist
                
                if total_scheduled_so_far < daily_capacity and remaining_capacity > 0:
                    rest_production = min(remaining_capacity, minimal, remaining_demand)
                    scheduled_qty = base_qty + rest_production
                else:
                    scheduled_qty = base_qty
            
            # KRITISCH: Stelle sicher, dass scheduled_qty nicht größer ist als demand
            # Dies verhindert, dass mehr produziert wird als der Produktionsbedarf erlaubt
            scheduled_qty = min(max(0.0, scheduled_qty), demand)
            scheduled_production_by_product[product] = scheduled_qty
            total_scheduled_so_far += scheduled_qty
            
            # KRITISCH: Reduziere Material SOFORT (dynamisch)
            # Dies stellt sicher, dass nachfolgende Produkte den reduzierten Bestand sehen
            if scheduled_qty > 0:
                stock_by_saddle_type[required_saddle_type] = max(0.0, stock_by_saddle_type[required_saddle_type] - scheduled_qty)
                # Aktualisiere kumulierten Verbrauch
                self._consumption_by_saddle[required_saddle_type] = self._consumption_by_saddle.get(required_saddle_type, 0.0) + float(scheduled_qty)
        
        # Sicherheitsprüfung 1: Stelle sicher, dass die Summe nicht die Kapazität überschreitet
        total_scheduled = sum(scheduled_production_by_product.values())
        if total_scheduled > daily_capacity:
            # Proportionale Reduktion, falls die Summe die Kapazität überschreitet
            scale_factor = daily_capacity / total_scheduled if total_scheduled > 0 else 0
            # WICHTIG: Bei Reduktion muss auch Material zurückgegeben werden
            for product in sorted_products:
                old_qty = scheduled_production_by_product.get(product, 0.0)
                new_qty = old_qty * scale_factor
                reduction = old_qty - new_qty
                scheduled_production_by_product[product] = new_qty
                
                # Gebe reduziertes Material zurück
                if reduction > 0:
                    required_saddle_type = self.master_data.BOM[product]['saddle']
                    stock_by_saddle_type[required_saddle_type] = stock_by_saddle_type.get(required_saddle_type, 0.0) + reduction
                    self._consumption_by_saddle[required_saddle_type] = max(0.0, self._consumption_by_saddle.get(required_saddle_type, 0.0) - reduction)
        
        # Sicherheitsprüfung 2: Stelle sicher, dass die Summe nicht den Produktionsbedarf überschreitet
        total_production_demand = sum(production_demand_by_product.values())
        total_scheduled = sum(scheduled_production_by_product.values())
        if total_scheduled > total_production_demand:
            # Proportionale Reduktion auf Produktionsbedarf
            scale_factor = total_production_demand / total_scheduled if total_scheduled > 0 else 0
            # WICHTIG: Bei Reduktion muss auch Material zurückgegeben werden
            for product in sorted_products:
                old_qty = scheduled_production_by_product.get(product, 0.0)
                new_qty = old_qty * scale_factor
                reduction = old_qty - new_qty
                scheduled_production_by_product[product] = new_qty
                
                # Gebe reduziertes Material zurück
                if reduction > 0:
                    required_saddle_type = self.master_data.BOM[product]['saddle']
                    stock_by_saddle_type[required_saddle_type] = stock_by_saddle_type.get(required_saddle_type, 0.0) + reduction
                    self._consumption_by_saddle[required_saddle_type] = max(0.0, self._consumption_by_saddle.get(required_saddle_type, 0.0) - reduction)
        
        # 8. Finale Prüfung - Stelle sicher, dass jedes Produkt nicht mehr produziert als sein Produktionsbedarf
        # Diese Prüfung ist kritisch, um sicherzustellen, dass niemals mehr produziert wird als geplant (wenn Backlog = 0)
        # WICHTIG: Wenn die Produktion reduziert wird, muss auch Material zurückgegeben werden
        for product in products_list:
            demand = production_demand_by_product.get(product, 0.0)
            scheduled_qty = scheduled_production_by_product.get(product, 0.0)
            
            # KRITISCH: Stelle sicher, dass scheduled_qty nicht größer ist als demand
            # Dies verhindert, dass mehr produziert wird als der Produktionsbedarf erlaubt
            if scheduled_qty > demand:
                old_qty = scheduled_production_by_product[product]
                scheduled_production_by_product[product] = demand
                reduction = old_qty - demand
                
                # Gebe reduziertes Material zurück
                if reduction > 0:
                    required_saddle_type = self.master_data.BOM[product]['saddle']
                    stock_by_saddle_type[required_saddle_type] = stock_by_saddle_type.get(required_saddle_type, 0.0) + reduction
                    self._consumption_by_saddle[required_saddle_type] = max(0.0, self._consumption_by_saddle.get(required_saddle_type, 0.0) - reduction)
        
        # 9. Tatsächliche PM = "zu produzierende Mengen" die HEUTE geplant werden
        # WICHTIG: "Tatsächliche PM" sind die "zu produzierende Mengen", die heute geplant werden
        # (NICHT die von gestern - das wäre "fertiggestellte PM")
        production_by_product = {}
        actual_pm_by_product = {}
        
        for product in products_list:
            scheduled_qty = scheduled_production_by_product.get(product, 0.0)
            actual_pm_by_product[product] = int(scheduled_qty)
            production_by_product[product] = int(scheduled_qty)
        
        # Speichere "zu produzierende Mengen" mit Fertigstellungsdatum (für "fertiggestellte PM" am nächsten Tag)
        completion_day = day + 1  # Fertigstellungsdatum = morgen (nächster Arbeitstag)
        
        # Finde nächsten Arbeitstag für Fertigstellung
        if self.workday_calculator:
            while completion_day < 365 and not self.workday_calculator.is_workday(completion_day):
                completion_day += 1
        
        # Speichere "zu produzierende Mengen" mit Fertigstellungsdatum (für "fertiggestellte PM")
        for product in products_list:
            scheduled_qty = scheduled_production_by_product.get(product, 0.0)
            if scheduled_qty > 0:
                # Speichere mit Fertigstellungsdatum (wird morgen als "fertiggestellte PM" angezeigt)
                self._scheduled_production[(completion_day, product)] = scheduled_qty
        
        # Speichere Bestand pro Produkt für Anzeige
        material_availability_report = {}
        for product in products_list:
            required_saddle_type = self.master_data.BOM[product]['saddle']
            material_availability_report[product] = stock_by_saddle_type.get(required_saddle_type, 0.0)
        
        # WICHTIG: Berechne fertiggestellte PM VOR Backlog-Berechnung
        # Fertiggestellte PM = Produktion vom vorherigen ARBEITSTAG, die heute fertiggestellt wird
        finished_pm_by_product = {}
        if day > 0 and self.workday_calculator:
            prev_day = day - 1
            # Prüfe, ob der vorherige Tag ein Arbeitstag war
            if self.workday_calculator.is_workday(prev_day):
                # Vorheriger Tag war ein Arbeitstag: Hole tatsächliche PM vom vorherigen Tag
                for product in self.master_data.BOM.keys():
                    prev_logs = self.production_logs.get(product, [])
                    if prev_logs and len(prev_logs) > 0:
                        # Letzter Eintrag = vorheriger Tag (da wir täglich loggen)
                        finished_pm_by_product[product] = prev_logs[-1].get('tatsächliche PM', 0)
                    else:
                        finished_pm_by_product[product] = 0
            else:
                # Vorheriger Tag war kein Arbeitstag: Finde den letzten Arbeitstag
                prev_workday = prev_day
                while prev_workday >= 0 and not self.workday_calculator.is_workday(prev_workday):
                    prev_workday -= 1
                
                if prev_workday >= 0:
                    # Suche den Log-Eintrag für den letzten Arbeitstag
                    for product in self.master_data.BOM.keys():
                        prev_logs = self.production_logs.get(product, [])
                        # Durchsuche Logs rückwärts, um den Eintrag für prev_workday zu finden
                        found = False
                        for log_entry in reversed(prev_logs):
                            log_date_str = log_entry.get('Datum', '')
                            if log_date_str:
                                try:
                                    from datetime import datetime
                                    log_date = datetime.strptime(log_date_str, self.master_data.DATE_FORMAT).date()
                                    log_day = (log_date - self.workday_calculator.get_date_from_day(0)).days
                                    if log_day == prev_workday:
                                        finished_pm_by_product[product] = log_entry.get('tatsächliche PM', 0)
                                        found = True
                                        break
                                except (ValueError, TypeError):
                                    pass
                        if not found:
                            finished_pm_by_product[product] = 0
                else:
                    # Kein vorheriger Arbeitstag gefunden
                    for product in self.master_data.BOM.keys():
                        finished_pm_by_product[product] = 0
        else:
            # Tag 0 oder kein WorkdayCalculator: keine fertiggestellte PM (noch nichts produziert)
            for product in self.master_data.BOM.keys():
                finished_pm_by_product[product] = 0
        
        # 7. Aktualisiere Backlog
        # KRITISCH: Backlog wird basierend auf der HEUTE GESTARTETEN Produktion reduziert, nicht erst bei Fertigstellung
        # Dies verhindert den "Echo-Effekt", bei dem der Backlog nicht reduziert wird, obwohl produziert wurde
        # Backlog = (geplante PM + Backlog gestern) - tatsächliche PM (heute gestartet)
        # Backlog ist das, was wir heute NICHT in die Produktion geben konnten
        for product in self.master_data.BOM.keys():
            # Geplante PM heute (Tagesbedarf OHNE Backlog)
            planned_pm = product_demands.get(product, 0)
            # Backlog gestern
            old_backlog = self.backlog.get(product, 0.0)
            # Tatsächliche PM heute (Produktion, die HEUTE gestartet wird)
            actual_started = production_by_product.get(product, 0)
            # Neuer Backlog = (geplante PM + Backlog gestern) - tatsächliche PM (heute gestartet)
            # Dies stellt sicher, dass der Backlog sofort reduziert wird, wenn produziert wird
            self.backlog[product] = max(0.0, (planned_pm + old_backlog) - actual_started)
        
        # 8. Speichere Produktionsplan
        self.production_plan[day] = production_by_product
        
        # 11. Logge für UI
        self._log_production(
            day, 
            production_by_product,
            product_demands,
            production_demand_by_product,
            material_availability_report, # Start-Verfügbarkeit
            rank_by_product,
            shifts,
            daily_capacity,
            stock_saddles_morning,  # Bestand zu Beginn des Tages (für proportionale Anzeige)
            proportional_production_by_product,  # Anteilige Produktion
            scheduled_production_by_product,  # zu produzierende Mengen
            finished_pm_by_product  # Fertiggestellte PM (bereits berechnet)
        )
        
        return production_by_product
    
    def _log_production(
        self,
        day: int,
        production_by_product: Dict[str, int],
        product_demands: Dict[str, int],
        production_demand_by_product: Dict[str, float],
        material_availability_by_product: Dict[str, float],
        rank_by_product: Dict[str, int],
        shifts: int,
        daily_capacity: float,
        stock_saddles_morning: float = None,
        proportional_production_by_product: Dict[str, int] = None,
        scheduled_production_by_product: Dict[str, float] = None,
        finished_pm_by_product: Dict[str, int] = None
    ) -> None:
        """Loggt Produktionsdaten für UI-Anzeige"""
        if not self.workday_calculator:
            return
        
        current_date = self.workday_calculator.get_date_from_day(day)
        # Hole alle Tag-Informationen auf einmal
        day_info = self.workday_calculator.get_day_info(day) if self.workday_calculator else {
            'weekday_name': 'Unbekannt',
            'weekday_abbr': '??',
            'is_workday': False,
            'is_weekend': False,
            'is_holiday': False
        }
        weekday_name = day_info['weekday_name']
        is_workday = day_info['is_workday']
        is_holiday = day_info['is_holiday']
        is_weekend = day_info['is_weekend']
        
        actual_build_total = sum(production_by_product.values())
        utilization = (actual_build_total / daily_capacity * 100) if daily_capacity > 0 else 0
        
        # Berechne Sattel-Shares für proportionale Anzeige (konsistent mit Materiallager)
        saddle_shares = self.master_data.calculate_saddle_shares()
        
        # OPTIMIERUNG: Berechne Bestände für alle Sattel-Typen auf einmal (Caching)
        # Dies vermeidet mehrfache Berechnung der Inbound-Tabelle
        stock_by_saddle = self._get_all_stocks_from_inbound_table(day, saddle_shares)
        
        # WICHTIG: Verwende fertiggestellte PM, die bereits in plan_daily_production berechnet wurde
        # Falls nicht übergeben, berechne es hier (Fallback)
        if finished_pm_by_product is None:
            finished_pm_by_product = {}
            for product in self.master_data.BOM.keys():
                finished_pm_by_product[product] = 0
        
        # Berechne Bestand morgens (vor der Produktion)
        # Bestand morgens = Inbound-Bestand - kumulierter Verbrauch bis zum VORHERIGEN Tag
        # WICHTIG: Der Verbrauch des aktuellen Tages wurde bereits in plan_daily_production aktualisiert
        stock_morning_by_saddle = {}
        for saddle_name in saddle_shares.keys():
            inbound_stock = stock_by_saddle.get(saddle_name, 0.0) or 0.0
            # Verbrauch bis zum VORHERIGEN Tag (noch ohne heutige Produktion)
            # WICHTIG: Der heutige Verbrauch wurde bereits in plan_daily_production hinzugefügt,
            # daher müssen wir ihn hier abziehen, um den Bestand morgens zu erhalten
            consumption_total = self._consumption_by_saddle.get(saddle_name, 0.0)
            # Berechne Verbrauch bis zum VORHERIGEN Tag
            consumption_before_today = consumption_total
            for product, qty in production_by_product.items():
                if qty > 0:
                    required_saddle = self.master_data.BOM[product]['saddle']
                    if required_saddle == saddle_name:
                        consumption_before_today -= float(qty)
            stock_morning_by_saddle[saddle_name] = max(0.0, inbound_stock - consumption_before_today)
        
        for product in self.master_data.BOM.keys():
            saddle_name = self.master_data.BOM[product]['saddle']
            
            # Verfügbarkeit für Anzeige: Hole Bestand morgens (vor der Produktion)
            stock_saddle_specific = stock_morning_by_saddle.get(saddle_name)
            
            # Fallback: Wenn Inbound-Tabelle nicht verfügbar, verwende proportionale Aufteilung
            if stock_saddle_specific is None:
                if stock_saddles_morning is None:
                    stock_saddles_morning = 0.0
                    for p in self.master_data.BOM.keys():
                        if p in material_availability_by_product:
                            stock_saddles_morning = material_availability_by_product[p]
                            break
                saddle_share = saddle_shares.get(saddle_name, 0.0)
                stock_saddle_specific = stock_saddles_morning * saddle_share
                # Ziehe auch hier den Verbrauch bis zum VORHERIGEN Tag ab
                consumption_before_today = self._consumption_by_saddle.get(saddle_name, 0.0)
                stock_saddle_specific = max(0.0, stock_saddle_specific - consumption_before_today)
            
            planned_pm = product_demands.get(product, 0)
            actual_qty = production_by_product.get(product, 0)
            # WICHTIG: Fertiggestellte PM nur anzeigen, wenn der aktuelle Tag ein Arbeitstag ist
            # An Wochenenden/Feiertagen wird keine fertiggestellte PM angezeigt
            if is_workday:
                finished_pm = finished_pm_by_product.get(product, 0)
            else:
                finished_pm = 0
            backlog = self.backlog.get(product, 0.0)
            
            # Zusätzliche Felder für Debugging/Validierung
            proportional_pm = proportional_production_by_product.get(product, 0) if proportional_production_by_product else 0
            scheduled_pm = scheduled_production_by_product.get(product, 0.0) if scheduled_production_by_product else 0.0
            
            log_entry = {
                'Wochentag': day_info['weekday_abbr'],
                'Datum': current_date.strftime(self.master_data.DATE_FORMAT),
                'Schichtanzahl': shifts,
                'Auslastung (%)': round(utilization, 2),
                saddle_name: int(round(stock_saddle_specific)) if stock_saddle_specific > 0 else 0,
                'geplante PM': int(round(planned_pm)),
                'tatsächliche PM': int(round(actual_qty)),
                'fertiggestellte PM': int(round(finished_pm, 0)),
                'Backlog': int(round(backlog, 0)),
                '_Produktionsbedarf': production_demand_by_product.get(product, 0),
                '_Rang': rank_by_product.get(product, 0),
                '_Anteilige_Produktion': int(round(proportional_pm)),
                '_zu_produzierende_Mengen': int(round(scheduled_pm)),
                'Is_Weekend': is_weekend,
                'Is_Holiday': is_holiday
            }
            
            self.production_logs[product].append(log_entry)
    
    def _initialize_inbound_distribution_cache(self, saddle_shares: Dict[str, float]):
        """
        Initialisiert den Cache für die Verteilung pro Tag und Sattel-Typ.
        Wird nur einmal aufgerufen, um get_inbound_log_dataframe() nicht mehrfach aufzurufen.
        
        Args:
            saddle_shares: Dictionary mit Sattel-Shares (für get_inbound_log_dataframe)
        """
        if self._inbound_distribution_initialized:
            return
        
        if not self.china_transport_manager or not self.workday_calculator:
            self._inbound_distribution_initialized = True
            return
        
        try:
            # PERFORMANCE: Berechne Verteilung einmal aus get_inbound_log_dataframe()
            # Dies ist teuer beim ersten Aufruf, aber dann gecacht
            inbound_df = self.china_transport_manager.get_inbound_log_dataframe(saddle_shares)
            
            if inbound_df.empty:
                self._inbound_distribution_initialized = True
                return
            
            # Parse alle Daten einmal und speichere Verteilung pro Tag
            avail_col = 'Tatsächliche Ankunft LKW 🇩🇪'
            if avail_col in inbound_df.columns:
                import pandas as pd
                from datetime import datetime
                
                # Filtere gültige Zeilen
                valid_rows = inbound_df[inbound_df[avail_col].notna() & (inbound_df[avail_col].astype(str).str.strip() != '')]
                if not valid_rows.empty:
                    valid_rows = valid_rows.copy()
                    # Parse Datum vektorisiert
                    valid_rows['_parsed_date'] = pd.to_datetime(valid_rows[avail_col], format=self.master_data.DATE_FORMAT, errors='coerce').dt.date
                    valid_rows = valid_rows[valid_rows['_parsed_date'].notna()]
                    
                    # Gruppiere nach Datum und summiere Mengen pro Sattel-Typ
                    for _, row in valid_rows.iterrows():
                        avail_date = row['_parsed_date']
                        day_idx = (avail_date - date(self.workday_calculator.year, 1, 1)).days
                        
                        if 0 <= day_idx < 365:
                            if day_idx not in self._inbound_distribution_cache:
                                self._inbound_distribution_cache[day_idx] = {s: 0.0 for s in saddle_shares.keys()}
                            
                            for saddle_name in saddle_shares.keys():
                                if saddle_name in row:
                                    qty_val = row[saddle_name]
                                    try:
                                        if isinstance(qty_val, str):
                                            qty_val = qty_val.strip()
                                            if qty_val == '' or qty_val == '-':
                                                continue
                                        qty = float(qty_val) if qty_val else 0.0
                                        if qty > 0:
                                            self._inbound_distribution_cache[day_idx][saddle_name] += qty
                                    except (ValueError, TypeError):
                                        continue
            
            self._inbound_distribution_initialized = True
        except Exception:
            self._inbound_distribution_initialized = True
    
    def _get_all_stocks_from_inbound_table(self, day: int, saddle_shares: Dict[str, float]) -> Dict[str, float]:
        """
        Holt die Bestände für ALLE Sattel-Typen für einen bestimmten Tag aus der Inbound-Tabelle.
        
        OPTIMIERUNG: Berechnet die Inbound-Tabelle nur einmal pro Tag und cached das Ergebnis.
        Dies vermeidet mehrfache Berechnung (8 Produkte = 8x Aufruf).
        
        PERFORMANCE: Verwendet gecachte Verteilung statt get_inbound_log_dataframe() jedes Mal aufzurufen.
        
        Args:
            day: Tag-Index (0-basiert, 0 = 01.01.2027)
            saddle_shares: Dictionary mit Sattel-Shares (für get_inbound_log_dataframe)
            
        Returns:
            Dictionary mit Beständen pro Sattel-Typ: {saddle_name: stock_morning}
        """
        # Prüfe Cache
        if day in self._inbound_stock_cache:
            return self._inbound_stock_cache[day]
        
        # Initialisiere Ergebnis-Dictionary
        stock_by_saddle = {saddle_name: None for saddle_name in saddle_shares.keys()}
        
        if not self.china_transport_manager or not self.workday_calculator:
            # Cache leeres Ergebnis
            self._inbound_stock_cache[day] = stock_by_saddle
            return stock_by_saddle
        
        try:
            # PERFORMANCE: Initialisiere Verteilungs-Cache einmal (wenn noch nicht geschehen)
            self._initialize_inbound_distribution_cache(saddle_shares)
            
            # Verwende gecachte Verteilung für kumulativen Bestand
            # Summiere alle Zugänge bis einschließlich heute
            manager = self.china_transport_manager
            if manager and hasattr(manager, 'get_daily_arrival_qty'):
                # Verwende kumulativen Cache - berechne nur die Differenz zum vorherigen Tag
                prev_day = day - 1
                if prev_day >= 0 and prev_day in self._inbound_stock_cache:
                    # Verwende vorherigen Tag als Basis
                    prev_stock = self._inbound_stock_cache[prev_day]
                    # Addiere Zugang von heute aus Verteilungs-Cache
                    today_distribution = self._inbound_distribution_cache.get(day, {})
                    
                    for saddle_name in saddle_shares.keys():
                        prev_qty = prev_stock.get(saddle_name, 0.0) or 0.0
                        today_qty = today_distribution.get(saddle_name, 0.0) or 0.0
                        stock_by_saddle[saddle_name] = prev_qty + today_qty
                else:
                    # Erster Tag oder Cache fehlt: Berechne kumulativen Bestand bis heute
                    for saddle_name in saddle_shares.keys():
                        total_qty = 0.0
                        for d in range(day + 1):  # Bis einschließlich heute
                            day_distribution = self._inbound_distribution_cache.get(d, {})
                            total_qty += day_distribution.get(saddle_name, 0.0) or 0.0
                        stock_by_saddle[saddle_name] = total_qty if total_qty > 0 else None
            else:
                # Fallback: Verwende get_inbound_log_dataframe() wenn get_daily_arrival_qty() nicht verfügbar
                inbound_df = self.china_transport_manager.get_inbound_log_dataframe(saddle_shares)
            
            if inbound_df.empty:
                # Cache leeres Ergebnis
                self._inbound_stock_cache[day] = stock_by_saddle
                return stock_by_saddle
            
            # Konvertiere Tag-Index zu Datum
            target_date = self.workday_calculator.get_date_from_day(day)
            
            # PERFORMANCE: Vektorisierte Berechnung statt iterrows()
            # Berechne Bestand morgens für ALLE Sattel-Typen auf einmal
            # Bestand morgens = Summe aller Verfügbar <= target_date
            avail_col = 'Tatsächliche Ankunft LKW 🇩🇪'
            if avail_col in inbound_df.columns:
                try:
                    import pandas as pd
                    # Filtere gültige Zeilen
                    valid_rows = inbound_df[inbound_df[avail_col].notna() & (inbound_df[avail_col].astype(str).str.strip() != '')]
                    if not valid_rows.empty:
                        valid_rows = valid_rows.copy()
                        # Parse Datum vektorisiert
                        valid_rows['_parsed_date'] = pd.to_datetime(valid_rows[avail_col], format=self.master_data.DATE_FORMAT, errors='coerce').dt.date
                        valid_rows = valid_rows[valid_rows['_parsed_date'].notna()]
                        # Filtere nur Zeilen <= target_date
                        valid_rows = valid_rows[valid_rows['_parsed_date'] <= target_date]
                        
                        # Summiere Mengen pro Sattel-Typ vektorisiert
                        for saddle_name in saddle_shares.keys():
                            if saddle_name in valid_rows.columns:
                                qty_series = pd.to_numeric(valid_rows[saddle_name], errors='coerce').fillna(0.0)
                                stock_morning = float(qty_series.sum())
                                stock_by_saddle[saddle_name] = stock_morning if stock_morning > 0 else None
                            else:
                                stock_by_saddle[saddle_name] = None
                except Exception:
                    # Fallback auf alte Methode bei Fehler
                    for saddle_name in saddle_shares.keys():
                        stock_morning = 0.0
                        
                        for _, row in inbound_df.iterrows():
                            avail_str = row.get(avail_col, '')
                            if avail_str and isinstance(avail_str, str) and len(avail_str.strip()) > 0:
                                try:
                                    avail_date = datetime.strptime(avail_str, self.master_data.DATE_FORMAT).date()
                                    
                                    if avail_date <= target_date:
                                        qty_val = row.get(saddle_name, 0)
                                        if qty_val and str(qty_val).strip() != '':
                                            try:
                                                stock_morning += float(qty_val)
                                            except (ValueError, TypeError):
                                                pass
                                except (ValueError, TypeError):
                                    continue
                        
                        stock_by_saddle[saddle_name] = stock_morning if stock_morning > 0 else None
            else:
                # Keine Spalte vorhanden - setze alle auf None
                for saddle_name in saddle_shares.keys():
                    stock_by_saddle[saddle_name] = None
            
            # Cache Ergebnis
            self._inbound_stock_cache[day] = stock_by_saddle
            return stock_by_saddle
            
        except Exception:
            # Bei Fehler: Cache leeres Ergebnis
            self._inbound_stock_cache[day] = stock_by_saddle
            return stock_by_saddle
    
    def get_consumed_components(self, production_by_product: Dict[str, int]) -> Dict[str, float]:
        consumed = {'frames_alu': 0.0, 'frames_carbon': 0.0, 'saddles': 0.0}
        for product, qty in production_by_product.items():
            if qty > 0 and product in self.master_data.BOM:
                consumed['saddles'] += float(qty)
                frame_type = self.master_data.BOM[product]['frame']
                frame_category = self.master_data.get_frame_category(frame_type)
                consumed[f'frames_{frame_category.lower()}'] += float(qty)
        return consumed
    
    def consume_components(self, consumed: Dict[str, float]) -> None:
        """Verbraucht Komponenten aus dem Lager"""
        self.inventory.stock_alu -= consumed['frames_alu']
        self.inventory.stock_carbon -= consumed['frames_carbon']
        # WICHTIG: Stelle sicher, dass stock_saddles nie negativ wird
        # Wenn mehr verbraucht wird als vorhanden, setze auf 0
        # Dies verhindert "Geisterproduktion" ohne Material
        self.inventory.stock_saddles = max(0.0, self.inventory.stock_saddles - consumed['saddles'])
    
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
