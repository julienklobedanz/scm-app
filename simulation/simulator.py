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
        self.inventory = Inventory(
            stock_alu=initial_stock_frames_alu,
            stock_carbon=initial_stock_frames_carbon,
            stock_saddles=initial_stock_saddles
        )
        self.backlog = MarketBacklog()
        self.backlog.initialize_markets(self.master_data.MARKETS)
        
        # Initialisiere Services
        self.workday_calculator = WorkdayCalculator(year=2027)
        self.demand_calculator = DemandCalculator(yearly_volume, self.workday_calculator)
        self.production_planner = ProductionPlanner(self.inventory)
        self.china_transport_manager = ChinaTransportManager(self.inventory, self.workday_calculator, self.scenario_manager)
        self.procurement_manager = ProcurementManager(self.inventory, self.china_transport_manager)
        
        # Platziere initiale Bestellungen vor Simulationsbeginn (49 Tage vor dem ersten Bedarf)
        self._place_initial_orders()
        
        # Warm-Up Phase: Simuliere Logistik für Tage vor Simulationsbeginn
        # Damit Schiffe bereits im Dezember abfahren können
        self._warmup_logistics()
    
    def _warmup_logistics(self) -> None:
        """
        Warm-Up Phase: Simuliert die Logistik für Tage vor Simulationsbeginn (-49 bis -1).
        Damit werden Schiffe bereits im Dezember abfahren, wenn >= 500 erreicht sind.
        """
        warmup_start = -49  # 49 Tage vor Tag 0
        
        # Simuliere jeden Tag von -49 bis -1
        for sim_day in range(warmup_start, 0):
            # Prüfe, ob an diesem Tag ein Schiff fahren würde (nur Mittwochs)
            # Das triggert process_shipments an Mittwochen im Dez 2026
            self.china_transport_manager.process_shipments(sim_day)
    
    def _place_initial_orders(self) -> None:
        """
        Platziert initiale Bestellungen vor Simulationsbeginn.
        Bestellt täglich basierend auf dem täglichen Bedarf, 49 Tage vor dem jeweiligen Bedarfstag.
        
        Beispiel: Für Bedarf am 04.01.2027 (Tag 3) wird am 16.11.2026 (Tag -46) bestellt.
        """
        # Berechne tägliche Bestellungen für die ersten ~30 Tage
        # (danach übernimmt der Procurement Manager die täglichen Bestellungen)
        lead_time_days = 49
        
        for day in range(30):  # Erste 30 Tage
            if self.workday_calculator.is_workday(day):
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
            
            # Prüfe Lieferantenausfall (muss vor Bestellempfang geprüft werden)
            supplier_breakdowns = self.scenario_manager.get_supplier_breakdown_scenarios(day)
            supplier_blocked_saddles = any(
                s.component_type in ['saddles', 'all'] for s in supplier_breakdowns
            )
            
            # Empfange nur Sattel-Bestellungen (nur wenn Lieferant nicht ausgefallen ist)
            if not supplier_blocked_saddles:
                # Verwende detaillierte Transport-Logik (Verspätung und Verlust sind bereits berücksichtigt)
                received_quantity = self.china_transport_manager.receive_orders(day)
                
                # Füge zum Lagerbestand hinzu
                if received_quantity > 0:
                    self.inventory.stock_saddles += received_quantity
            
            # 2. Berechne tägliche Nachfrage mit Carry-Over-Logik
            # Marketing-Add-ons berechnen (pro Produkt) - auf Float-Basis
            marketing_add_ons = {}
            marketing_scenarios = self.scenario_manager.get_marketing_scenarios(day)
            
            if marketing_scenarios:
                # Berechne Marketing-Add-ons auf Float-Basis (vor Rundung)
                month = self.master_data.get_month_from_day(day)
                is_workday = self.workday_calculator.is_workday(day)
                
                if is_workday:
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
            
            # Berechne Nachfrage mit Carry-Over-Logik (inkl. Marketing-Add-ons)
            # Diese Methode führt die Rundung durch und aktualisiert Remainders
            product_demands = self.demand_calculator.calculate_daily_demand_per_product_dict(
                day, 
                marketing_add_ons
            )
            
            # Gesamtnachfrage (ganzzahlig)
            daily_target = sum(product_demands.values())
            total_demand += daily_target
            
            # 3. Aggregiere BOM-Anforderungen
            frame_demand, saddle_demand = self.demand_calculator.aggregate_bom_demand(product_demands)
            
            # 4. Produktionsplanung
            # Prüfe ob Arbeitstag
            is_workday = self.workday_calculator.is_workday(day)
            
            if is_workday:
                # Produktion nur an Arbeitstagen
                # WICHTIG: Nachfrage bleibt gleich (Kunden bestellen auch an Wochenenden)
                # Die Produktionskapazität wird durch verfügbare Komponenten und Schicht-Kapazität begrenzt
                actual_build, consumed, actual_shifts, max_daily_capacity = self.production_planner.calculate_production_capacity(
                    daily_target, frame_demand, saddle_demand
                )
            else:
                # Keine Produktion an Wochenenden/Feiertagen
                actual_build = 0.0
                consumed = {
                    'frames_alu': 0.0,
                    'frames_carbon': 0.0,
                    'saddles': 0.0
                }
                actual_shifts = 0
                max_daily_capacity = 0.0
            
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
                expected_future_demand = 0.0
                
                # Prüfe, ob der Zukunftstag noch im Jahr liegt
                if future_day < days:
                    # 1. Prüfe, ob Marketing an diesem Zukunftstag aktiv ist
                    future_marketing_add_ons = {}
                    future_marketing_scenarios = self.scenario_manager.get_marketing_scenarios(future_day)
                    
                    if future_marketing_scenarios and self.workday_calculator.is_workday(future_day):
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
                    future_product_demands = self.demand_calculator.calculate_daily_demand_per_product_dict(
                        future_day, future_marketing_add_ons
                    )
                    
                    # 3. Aggregiere BOM-Anforderungen für Sättel
                    _, future_saddle_demand = self.demand_calculator.aggregate_bom_demand(future_product_demands)
                    
                    # 4. Übergib den täglichen Bedarf des Zukunftstags (nicht kumulativ)
                    # Der ProcurementManager bestellt täglich basierend auf diesem Bedarf
                    # Analog zur Excel-Formel: Wir schauen auf den Bedarf in 49 Tagen und bestellen heute dafür
                    expected_future_demand = future_saddle_demand
                
                # Übergebe den proaktiven Bedarf an den Procurement Manager
                self.procurement_manager.check_and_order(day, expected_future_demand)
            
            # 6. Customer Distribution
            shipped_qty = actual_build
            self.backlog.ship_to_markets(day, shipped_qty, self.master_data.MARKETS)
            self.backlog.receive_shipments(day, daily_target, self.master_data.MARKETS)
            
            # Speichere Tagesergebnisse
            current_date = self.workday_calculator.get_date_from_day(day)
            month = self.master_data.get_month_from_day(day)
            weekday_name = self.workday_calculator.get_weekday_name(day)
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
                'Stock_Saddles': self.inventory.stock_saddles,
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

