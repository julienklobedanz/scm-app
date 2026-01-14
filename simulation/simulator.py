"""
Hauptsimulations-Engine
Koordiniert alle Simulationskomponenten
"""

import pandas as pd
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
        self.workday_calculator = WorkdayCalculator(year=2026)
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
        
        # Initial-Betankung: Setze Initialbestand aus Inbound-Tabelle
        # WICHTIG: Dies muss NACH _place_initial_orders() und _warmup_logistics() erfolgen,
        # damit die Inbound-Tabelle bereits alle Vorlauf-Lieferungen enthält
        self._initialize_stock_from_inbound()
    
    def _initialize_stock_from_inbound(self) -> None:
        """
        Initialisiert den Sattel-Bestand aus der Inbound-Tabelle.
        
        OPTIMIERUNG: Baut die Inbound-Tabelle nur einmal und filtert dann.
        Das ist schneller als get_daily_arrival_qty für jeden Tag aufzurufen (O(n²) Problem).
        
        Diese Methode stellt sicher, dass der Simulator am 01.01.2026 mit dem exakt
        gleichen Bestand startet, den auch die Materiallager-Seite anzeigt.
        """
        from datetime import date
        
        # Berechne Sattel-Shares (für get_inbound_log_dataframe benötigt)
        saddle_shares = self.master_data.calculate_saddle_shares()
        
        # Hole Inbound-Tabelle (einmalig, wird gecacht)
        try:
            inbound_df = self.china_transport_manager.get_inbound_log_dataframe(saddle_shares)
        except Exception:
            # Bei Fehler: behalte stock_saddles = 0.0
            return
        
        if inbound_df.empty:
            # Keine Daten verfügbar, behalte stock_saddles = 0.0
            return
        
        # Filtere alle Zeilen mit "Verfügbar im Lager" <= 31.12.2025
        cutoff_date = date(2025, 12, 31)
        initial_stock = 0.0
        
        for _, row in inbound_df.iterrows():
            avail_str = row.get('Verfügbar im Lager', '')
            if avail_str and isinstance(avail_str, str) and len(avail_str.strip()) > 0:
                try:
                    from datetime import datetime
                    avail_date = datetime.strptime(avail_str, self.master_data.DATE_FORMAT).date()
                    
                    if avail_date <= cutoff_date:
                        # Summiere "Menge Gesamt" (Pool-Menge aller Sättel)
                        menge_gesamt = row.get('Menge Gesamt', 0)
                        if menge_gesamt and str(menge_gesamt).strip() != '':
                            try:
                                initial_stock += float(menge_gesamt)
                            except (ValueError, TypeError):
                                pass
                except (ValueError, TypeError):
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
        
        Beispiel: Für Bedarf am 04.01.2026 (Tag 3) wird am 16.11.2025 (Tag -46) bestellt.
        """
        # WICHTIG: Wir müssen den Bedarf für die gesamte Lead-Time vorbestellen,
        # damit am Tag 0 (Start der run-Schleife) nahtlos weitergemacht wird.
        # Die Schleife muss mindestens lead_time_days lang sein, um alle Bedarfstage 0-48 abzudecken.
        lead_time_days = 49
        
        for day in range(lead_time_days):  # KORREKTUR: lead_time_days statt 30
            # KORREKTUR: Bestellung findet an jedem Wochentag (Mo-Fr) statt, auch an deutschen Feiertagen
            if not self.workday_calculator.is_weekend(day):
                # Berechne täglichen Bedarf (ohne Carry-Over, da wir nur Base_Daily_Float brauchen)
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
            
            # Berechne Nachfrage mit Carry-Over-Logik (inkl. Marketing-Add-ons)
            # Diese Methode führt die Rundung durch und aktualisiert Remainders
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
                # KORREKTUR: Keine Zyklik - nur für Jahr 2026 (0 <= future_day <= 364)
                # Für future_day > 364 (Jahr 2027): Bedarf = 0 (keine Bestellung für nächstes Jahr)
                expected_future_demand = 0.0
                
                # Prüfe, ob der Zukunftstag noch im Jahr 2026 liegt
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
                    
                    # 2. Berechne den EXAKTEN Bedarf für diesen Zukunftstag (inkl. Marketing)
                    # Methode gibt 0 zurück, wenn future_day außerhalb 2026 liegt
                    future_product_demands = self.demand_calculator.get_demand_for_future_day(
                        future_day, future_marketing_add_ons
                    )
                    
                    # 3. Aggregiere BOM-Anforderungen für Sättel
                    _, future_saddle_demand = self.demand_calculator.aggregate_bom_demand(future_product_demands)
                    
                    # 4. Übergib den täglichen Bedarf des Zukunftstags (nicht kumulativ)
                    # Der ProcurementManager bestellt täglich basierend auf diesem Bedarf
                    # Analog zur Excel-Formel: Wir schauen auf den Bedarf in 49 Tagen und bestellen heute dafür
                    expected_future_demand = future_saddle_demand
                
                # KORREKTUR: Bestellung findet an jedem Wochentag (Mo-Fr) statt, auch an deutschen Feiertagen
                # WICHTIG: Auch im Vorlauf (2025, negative Tage) wird bestellt, damit Start 2026 volle Lager hat
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

