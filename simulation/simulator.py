"""
Hauptsimulations-Engine
Koordiniert alle Simulationskomponenten
"""

import pandas as pd
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    st = None
from typing import Dict, Any, Optional
from models.inventory import Inventory
from models.backlog import MarketBacklog
from models.scenarios import ScenarioManager
from simulation.demand_calculator import DemandCalculator
from simulation.production_planner import ProductionPlanner
from simulation.procurement_manager import ProcurementManager
from simulation.workday_calculator import WorkdayCalculator
from simulation.china_transport import ChinaTransportManager
from config.master_data import MasterData


class Simulator:
    """Hauptsimulations-Engine"""
    
    def __init__(
        self,
        yearly_volume: float,
        initial_stock_frames_alu: float,
        initial_stock_frames_carbon: float,
        initial_stock_saddles: float,
        scenario_manager: Optional[ScenarioManager] = None
    ):
        self.yearly_volume = yearly_volume
        self.master_data = MasterData
        self.scenario_manager = scenario_manager or ScenarioManager()
        
        # Initialisiere Modelle
        # WICHTIG: Für Sättel setzen wir den Initialbestand auf 0, damit alles über die
        # Inbound-Logik (get_daily_arrival_qty) läuft und Datenkonsistenz gewährleistet ist.
        # Der Bestand baut sich durch die Vorlauf-Bestellungen (_place_initial_orders) auf.
        self.inventory = Inventory(
            stock_alu=initial_stock_frames_alu,
            stock_carbon=initial_stock_frames_carbon,
            stock_saddles=0.0  # Start mit 0, Bestand baut sich über Inbound-Logik auf
        )
        self.backlog = MarketBacklog()
        self.backlog.initialize_markets(self.master_data.MARKETS)
        
        # Initialisiere Services
        # Hole Jahr aus Session State, falls verfügbar (für Streamlit)
        try:
            import streamlit as st
            planning_year = st.session_state.get('planning_year', 2027)
        except (ImportError, RuntimeError):
            planning_year = 2027  # Fallback wenn Streamlit nicht verfügbar
        self.workday_calculator = WorkdayCalculator(year=planning_year)
        self.demand_calculator = DemandCalculator(yearly_volume, self.workday_calculator)
        # WICHTIG: china_transport_manager muss VOR production_planner erstellt werden,
        # damit production_planner Zugriff darauf hat
        self.china_transport_manager = ChinaTransportManager(self.inventory, self.workday_calculator, self.scenario_manager)
        self.production_planner = ProductionPlanner(
            self.inventory,
            demand_calculator=self.demand_calculator,
            workday_calculator=self.workday_calculator,
            china_transport_manager=self.china_transport_manager
        )
        self.procurement_manager = ProcurementManager(
            self.inventory, 
            self.china_transport_manager,
            workday_calculator=self.workday_calculator
        )
        
        # Platziere initiale Bestellungen vor Simulationsbeginn (49 Tage vor dem ersten Bedarf)
        self._place_initial_orders()
        
        # Warm-Up Phase: Simuliere Logistik für Tage vor Simulationsbeginn
        # Damit Schiffe bereits im Dezember abfahren können
        self._warmup_logistics()
        
        # Initial-Betankung: Setze Initialbestand aus transport_status
        # OPTIMIERUNG: Berechnet direkt aus transport_status, nicht aus vollständiger Tabelle
        # Dies ist viel schneller und wird sofort nach _place_initial_orders() ausgeführt
        self._initialize_stock_from_inbound()
    
    def _initialize_stock_from_inbound(self) -> None:
        """
        Initialisiert den Sattel-Bestand aus der Inbound-Tabelle.
        
        OPTIMIERUNG: Berechnet nur die benötigten Daten bis zum 31.12.2026,
        nicht die gesamte Tabelle bis 31.12.2027. Das spart erheblich Zeit.
        
        Diese Methode stellt sicher, dass der Simulator am 01.01.2027 mit dem exakt
        gleichen Bestand startet, den auch die Materiallager-Seite anzeigt.
        """
        from datetime import date
        
        # OPTIMIERUNG: Berechne Initialbestand direkt aus transport_status,
        # ohne die gesamte Inbound-Tabelle zu erstellen
        # Das ist viel schneller, da wir nur bis 31.12.2025 benötigen
        
        cutoff_date = date(2026, 12, 31)
        initial_stock = 0.0
        
        # Iteriere über alle Transporte und berechne nur die, die bis 31.12.2026 ankommen
        for (order_day, order_id), status in self.china_transport_manager.transport_status.items():
            # Prüfe ob die Ware bis 31.12.2026 verfügbar ist
            available_day = status.get('available_day')
            if available_day is None:
                continue
            
            # Konvertiere Tag-Index zu Datum
            try:
                avail_date = self.workday_calculator.get_date_from_day(available_day)
                
                if avail_date <= cutoff_date:
                    # Summiere die tatsächliche Menge (nach Verlusten)
                    qty = status.get('actual_quantity', status.get('quantity', 0.0))
                    if qty > 0:
                        initial_stock += qty
            except Exception:
                continue
        
        # Setze inventory.stock_saddles auf den berechneten Initialbestand
        self.inventory.stock_saddles = initial_stock
    
    def _warmup_logistics(self) -> None:
        """
        Warm-Up Phase: Simuliert die Logistik für Tage vor Simulationsbeginn (-49 bis -1).
        Damit werden Schiffe bereits im Dezember abfahren, wenn >= 500 erreicht sind.
        OPTIMIERT: Nur Mittwoche verarbeiten (Schiffe fahren nur Mittwochs).
        """
        warmup_start = -49  # 49 Tage vor Tag 0
        
        # OPTIMIERUNG: Nur Mittwoche verarbeiten (Schiffe fahren nur Mittwochs)
        for sim_day in range(warmup_start, 0):
            date_obj = self.workday_calculator.get_date_from_day(sim_day)
            if date_obj.weekday() == 2:  # Mittwoch
                self.china_transport_manager.process_shipments(sim_day)
    
    def _place_initial_orders(self) -> None:
        """
        Platziert initiale Bestellungen vor Simulationsbeginn.
        Bestellt täglich basierend auf dem täglichen Bedarf, 49 Tage vor dem jeweiligen Bedarfstag.
        
        OPTIMIERUNG: Verwendet Nachfrage aus Volumenplanung, falls verfügbar.
        Das ist schneller als eigene Berechnung.
        
        Beispiel: Für Bedarf am 04.01.2027 (Tag 3) wird am 16.11.2026 (Tag -46) bestellt.
        """
        # WICHTIG: Wir müssen den Bedarf für die gesamte Lead-Time vorbestellen,
        # damit am Tag 0 (Start der run-Schleife) nahtlos weitergemacht wird.
        # Die Schleife muss mindestens lead_time_days lang sein, um alle Bedarfstage 0-48 abzudecken.
        lead_time_days = 49
        
        # OPTIMIERUNG: Versuche Nachfrage aus Volumenplanung zu holen
        daily_demands_actual = None
        if STREAMLIT_AVAILABLE:
            try:
                daily_demands_actual = st.session_state.get('daily_demands_actual', {})
            except Exception:
                pass
        
        for day in range(lead_time_days):  # KORREKTUR: lead_time_days statt 30
            # KORREKTUR: Bestellung findet an jedem Wochentag (Mo-Fr) statt, auch an deutschen Feiertagen
            if not self.workday_calculator.is_weekend(day):
                # OPTIMIERUNG: Verwende Nachfrage aus Volumenplanung, falls verfügbar
                if daily_demands_actual and day in daily_demands_actual:
                    # Summiere Nachfrage aller Produkte (jedes Bike braucht 1 Sattel)
                    daily_saddle_demand = sum(daily_demands_actual[day].values())
                else:
                    # Fallback: Berechne täglichen Bedarf (ohne Carry-Over, da wir nur Base_Daily_Float brauchen)
                    month = self.master_data.get_month_from_day(day)
                    base_daily_floats = self.demand_calculator._calculate_monthly_base_daily_float(month)
                    
                    # Summiere Base_Daily_Float für alle Produkte (jedes Bike braucht 1 Sattel)
                    daily_saddle_demand = sum(base_daily_floats.values())
                
                # Bestelldatum = Bedarfstag - Lead Time
                order_day = day - lead_time_days
                
                # Bestelle genau den täglichen Bedarf (nicht mehr, nicht weniger)
                if daily_saddle_demand > 0:
                    self.china_transport_manager.place_order(order_day, daily_saddle_demand)
    
    def run(self) -> tuple[pd.DataFrame, Dict[str, Any]]:
        """Führt die Simulation über 365 Tage aus"""
        days = 365
        results = []
        
        # KPIs
        total_demand = 0.0
        total_produced = 0.0
        days_stopped_frames = 0
        days_stopped_saddles = 0
        days_stopped_both = 0
        
        for day in range(days):
            # 0. Wasserschaden im Lager (muss zuerst geprüft werden, da es den Lagerbestand reduziert)
            warehouse_damages = self.scenario_manager.get_warehouse_damage_scenarios(day)
            for scenario in warehouse_damages:
                if scenario.affected_component == "saddles":
                    # Reduziere Sattel-Lagerbestand um den Verlustprozentsatz
                    loss_amount = self.inventory.stock_saddles * scenario.stock_loss_percentage
                    self.inventory.stock_saddles -= loss_amount
            
            # 1. China Inbound: Empfange Bestellungen (mit detaillierter Transport-Logik)
            # WICHTIG: Rahmen sind unbegrenzt verfügbar, daher keine Bestellungen mehr
            
            # 1. Wareneingang verarbeiten (Inbound -> Inventory)
            # WICHTIG: Wareneingänge müssen IMMER verarbeitet werden, auch wenn der Lieferant blockiert ist
            # (Blockierung betrifft nur neue Bestellungen, nicht bereits unterwegs befindliche Ware)
            # NEU: Verwende get_daily_arrival_qty für Datenkonsistenz mit Inbound-Tabelle
            # Diese Methode verwendet exakt dieselbe Logik wie get_inbound_log_dataframe
            arrived_qty = self.china_transport_manager.get_daily_arrival_qty(day)
            
            if arrived_qty > 0:
                # Buche den Zugang in den globalen Sattel-Bestand
                # WICHTIG: Der ProductionPlanner verteilt diesen Pool später virtuell auf die Typen.
                # Wir müssen hier nur sicherstellen, dass 'stock_saddles' erhöht wird.
                self.inventory.add_stock('saddles', arrived_qty)
            
            # WICHTIG: Speichere den verfügbaren Bestand VOR der Produktion (aber NACH Inbound)
            # Das entspricht dem "Bestand morgens" (inkl. Zugang) im Materiallager
            stock_saddles_morning = self.inventory.stock_saddles
            received_quantity = arrived_qty  # Für Reporting
            
            # Prüfe Lieferantenausfall (für neue Bestellungen)
            supplier_breakdowns = self.scenario_manager.get_supplier_breakdown_scenarios(day)
            supplier_blocked_saddles = any(
                s.component_type in ['saddles', 'all'] for s in supplier_breakdowns
            )
            
            # 2. Berechne tägliche Nachfrage mit Carry-Over-Logik
            # Marketing-Add-ons berechnen (pro Produkt) - auf Float-Basis
            marketing_add_ons = {}
            marketing_scenarios = self.scenario_manager.get_marketing_scenarios(day)
            
            if marketing_scenarios:
                # Berechne Marketing-Add-ons auf Float-Basis (vor Rundung)
                month = self.master_data.get_month_from_day(day)
                # KORREKTUR: Marketing wird auch an deutschen Feiertagen berücksichtigt, wenn es ein Wochentag ist
                is_weekend = self.workday_calculator.is_weekend(day)
                
                if not is_weekend:
                    # Hole Base_Daily_Float für Add-on-Berechnung
                    base_daily_floats = self.demand_calculator._calculate_monthly_base_daily_float(month)
                    
                    for scenario in marketing_scenarios:
                        factor = scenario.demand_increase_factor
                        for product in self.master_data.BOM.keys():
                            base_float = base_daily_floats.get(product, 0.0)
                            # Marketing-Add-on = zusätzliche Nachfrage durch Marketing (auf Float-Basis)
                            # Add-on = Base * (Factor - 1.0), z.B. bei Factor 1.5: Add-on = Base * 0.5
                            add_on = base_float * (factor - 1.0)
                            if product not in marketing_add_ons:
                                marketing_add_ons[product] = 0.0
                            marketing_add_ons[product] += add_on
            
            # Prüfe, ob es der letzte Arbeitstag des Jahres ist (für Rest-Aufsummierung)
            is_last_workday_of_year = False
            if self.workday_calculator.is_workday(day):
                # Prüfe, ob es nach diesem Tag noch Arbeitstage gibt
                has_future_workdays = False
                for future_day in range(day + 1, days):
                    if self.workday_calculator.is_workday(future_day):
                        has_future_workdays = True
                        break
                is_last_workday_of_year = not has_future_workdays
            
            # WICHTIG: Verwende Nachfrage aus Volumenplanung, falls vorhanden
            # Die Volumenplanung ist die Basis, der Simulator verarbeitet diese Daten weiter
            # Prüfe ob Nachfrage aus Volumenplanung verfügbar ist
            product_demands = None
            if STREAMLIT_AVAILABLE:
                try:
                    # Versuche Nachfrage aus Volumenplanung zu holen (tatsächliche Nachfrage mit Marketing)
                    daily_demands_actual = st.session_state.get('daily_demands_actual', {})
                    if day in daily_demands_actual and daily_demands_actual[day]:
                        # Verwende Nachfrage aus Volumenplanung
                        product_demands = daily_demands_actual[day].copy()
                    else:
                        # Fallback: Berechne Nachfrage selbst (wenn Volumenplanung noch nicht ausgeführt wurde)
                        product_demands = self.demand_calculator.calculate_daily_demand_per_product_dict(
                            day, 
                            marketing_add_ons,
                            is_last_workday_of_year
                        )
                except Exception:
                    # Fallback: Berechne Nachfrage selbst (wenn Streamlit nicht verfügbar oder Fehler)
                    product_demands = self.demand_calculator.calculate_daily_demand_per_product_dict(
                        day, 
                        marketing_add_ons,
                        is_last_workday_of_year
                    )
            else:
                # Fallback: Berechne Nachfrage selbst (wenn Streamlit nicht verfügbar)
                product_demands = self.demand_calculator.calculate_daily_demand_per_product_dict(
                    day, 
                    marketing_add_ons,
                    is_last_workday_of_year
                )
            
            # Gesamtnachfrage (ganzzahlig)
            daily_target = sum(product_demands.values())
            total_demand += daily_target
            
            # 3. Aggregiere BOM-Anforderungen (für Stoppage-Tracking)
            frame_demand, saddle_demand = self.demand_calculator.aggregate_bom_demand(product_demands)
            
            # 4. Produktionsplanung (NEU: Intelligenter Planer)
            # Der ProductionPlanner plant jetzt die Produktion pro Produkt mit Priorisierung
            production_by_product = self.production_planner.plan_daily_production(
                day,
                marketing_add_ons=marketing_add_ons,
                scenario_manager=self.scenario_manager
            )
            
            # Berechne Gesamtproduktion
            actual_build = sum(production_by_product.values())
            
            # Hole Materialverbrauch aus dem Plan
            consumed = self.production_planner.get_consumed_components(production_by_product)
            
            # Verbrauche Material
            self.production_planner.consume_components(consumed)
            total_produced += actual_build
            
            # Stoppage-Tracking
            stopped_frames, stopped_saddles = self.production_planner.check_stoppage(
                daily_target, frame_demand, saddle_demand
            )
            
            if stopped_frames and stopped_saddles:
                days_stopped_both += 1
            elif stopped_frames:
                days_stopped_frames += 1
            elif stopped_saddles:
                days_stopped_saddles += 1
            
            # 5. Procurement (nur wenn Lieferant nicht ausgefallen ist)
            # WICHTIG: Rahmen sind unbegrenzt verfügbar, daher keine Bestellungen für Rahmen
            if not supplier_blocked_saddles:
                self.procurement_manager.update_demand_history(
                    0.0,  # Rahmen-Nachfrage nicht mehr relevant
                    0.0,  # Rahmen-Nachfrage nicht mehr relevant
                    saddle_demand
                )
                
                # PROAKTIVE LOGIK (Look-Ahead wie Excel): Schauen in die Zukunft statt in die Vergangenheit
                # Bestelle heute für den Bedarf in 49 Tagen (Lead Time)
                lead_time = 49
                future_day = day + lead_time
                
                # Berechne erwartete Nachfrage für den Zukunftstag
                # KORREKTUR: Keine Zyklik - nur für Jahr 2027 (0 <= future_day <= 364)
                # Für future_day > 364 (Jahr 2027): Bedarf = 0 (keine Bestellung für nächstes Jahr)
                expected_future_demand = 0.0
                
                # Prüfe, ob der Zukunftstag noch im Jahr 2027 liegt
                if 0 <= future_day <= 364:
                    # 1. Prüfe, ob Marketing an diesem Zukunftstag aktiv ist
                    future_marketing_add_ons = {}
                    future_marketing_scenarios = self.scenario_manager.get_marketing_scenarios(future_day)
                    
                    # KORREKTUR: Marketing wird auch an deutschen Feiertagen berücksichtigt, wenn es ein Wochentag ist
                    if future_marketing_scenarios and not self.workday_calculator.is_weekend(future_day):
                        month = self.master_data.get_month_from_day(future_day)
                        base_daily_floats = self.demand_calculator._calculate_monthly_base_daily_float(month)
                        
                        for scenario in future_marketing_scenarios:
                            factor = scenario.demand_increase_factor
                            for product in self.master_data.BOM.keys():
                                base_float = base_daily_floats.get(product, 0.0)
                                add_on = base_float * (factor - 1.0)
                                if product not in future_marketing_add_ons:
                                    future_marketing_add_ons[product] = 0.0
                                future_marketing_add_ons[product] += add_on
                    
                    # 2. WICHTIG: Verwende Nachfrage aus Volumenplanung (Basis), falls verfügbar
                    # Die Volumenplanung ist die Basis, der Simulator verarbeitet diese Daten weiter
                    future_product_demands = None
                    if STREAMLIT_AVAILABLE:
                        try:
                            # Versuche Nachfrage aus Volumenplanung zu holen (tatsächliche Nachfrage mit Marketing)
                            daily_demands_actual = st.session_state.get('daily_demands_actual', {})
                            if future_day in daily_demands_actual and daily_demands_actual[future_day]:
                                # Verwende Nachfrage aus Volumenplanung
                                future_product_demands = daily_demands_actual[future_day].copy()
                            else:
                                # Fallback: Berechne Nachfrage selbst (wenn Volumenplanung noch nicht ausgeführt wurde)
                                future_product_demands = self.demand_calculator.get_demand_for_future_day(
                                    future_day, future_marketing_add_ons
                                )
                        except Exception:
                            # Fallback: Berechne Nachfrage selbst (wenn Streamlit nicht verfügbar oder Fehler)
                            future_product_demands = self.demand_calculator.get_demand_for_future_day(
                                future_day, future_marketing_add_ons
                            )
                    else:
                        # Fallback: Berechne Nachfrage selbst (wenn Streamlit nicht verfügbar)
                        future_product_demands = self.demand_calculator.get_demand_for_future_day(
                            future_day, future_marketing_add_ons
                        )
                    
                    # 3. Aggregiere BOM-Anforderungen für Sättel
                    _, future_saddle_demand = self.demand_calculator.aggregate_bom_demand(future_product_demands)
                    
                    # 4. Übergib den täglichen Bedarf des Zukunftstags (nicht kumulativ)
                    # Der ProcurementManager bestellt täglich basierend auf diesem Bedarf
                    # Analog zur Excel-Formel: Wir schauen auf den Bedarf in 49 Tagen und bestellen heute dafür
                    # WICHTIG: Dieser Bedarf stammt jetzt aus der Volumenplanung (Basis)
                    expected_future_demand = future_saddle_demand
                
                # KORREKTUR: Bestellung findet an jedem Wochentag (Mo-Fr) statt, auch an deutschen Feiertagen
                # WICHTIG: Auch im Vorlauf (2026, negative Tage) wird bestellt, damit Start 2027 volle Lager hat
                # Übergebe den proaktiven Bedarf an den Procurement Manager
                if not self.workday_calculator.is_weekend(day):
                    self.procurement_manager.check_and_order(day, expected_future_demand)
            
            # 6. Customer Distribution
            shipped_qty = actual_build
            self.backlog.ship_to_markets(day, shipped_qty, self.master_data.MARKETS)
            self.backlog.receive_shipments(day, daily_target, self.master_data.MARKETS)
            
            # Speichere Tagesergebnisse
            current_date = self.workday_calculator.get_date_from_day(day)
            month = self.master_data.get_month_from_day(day)
            weekday_name = self.workday_calculator.get_weekday_name(day)
            # KORREKTUR: is_workday für Reporting (echter Arbeitstag in DE, nicht nur Wochentag)
            is_workday = self.workday_calculator.is_workday(day)
            results.append({
                'Day': day + 1,
                'Date': current_date,
                'Month': month,
                'Weekday': weekday_name,
                'Is_Workday': 1 if is_workday else 0,
                'Daily_Target': daily_target,
                'Actual_Build': actual_build,
                'Stock_Frames_Alu': self.inventory.stock_alu,
                'Stock_Frames_Carbon': self.inventory.stock_carbon,
                'Stock_Saddles': self.inventory.stock_saddles,  # Bestand Abend (nach Produktion)
                'Stock_Saddles_Morning': stock_saddles_morning,  # Bestand Morgen (inkl. Zugang)
                'Inbound_Saddles': received_quantity,  # Zugang heute (für Materiallager-Seite)
                'Backlog_DE': self.backlog.backlog['DE'],
                'Backlog_USA': self.backlog.backlog['USA'],
                'Backlog_FR': self.backlog.backlog['FR'],
                'Backlog_CN': self.backlog.backlog['CN'],
                'Backlog_CH': self.backlog.backlog['CH'],
                'Backlog_AT': self.backlog.backlog['AT'],
                'Stopped_Frames': 1 if stopped_frames else 0,
                'Stopped_Saddles': 1 if stopped_saddles else 0,
                'Stopped_Both': 1 if (stopped_frames and stopped_saddles) else 0
            })
        
        # Berechne Service Level
        service_level = (total_produced / total_demand * 100) if total_demand > 0 else 0.0
        
        kpis = {
            'service_level': service_level,
            'days_stopped_frames': days_stopped_frames,
            'days_stopped_saddles': days_stopped_saddles,
            'days_stopped_both': days_stopped_both,
            'total_demand': total_demand,
            'total_produced': total_produced
        }
        
        # Speichere auch den ChinaTransportManager für spätere Verwendung
        # (z.B. für China Supplier Log Seite)
        kpis['china_transport_manager'] = self.china_transport_manager
        
        return pd.DataFrame(results), kpis

