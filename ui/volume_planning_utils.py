"""
Volume Planning Utilities
Berechnet Nachfrage aus Volumenplanung für Verwendung im Simulator
"""

import streamlit as st
from simulation.workday_calculator import WorkdayCalculator
from simulation.demand_calculator import DemandCalculator
from config.master_data import MasterData
from models.scenarios import ScenarioManager


def calculate_volume_planning_demand():
    """
    Berechnet die Nachfrage aus Volumenplanung für alle 365 Tage.
    Diese Funktion wird beim Start der App ausgeführt, damit die Daten für den Simulator verfügbar sind.
    
    Returns:
        Tuple (daily_demands_planned, daily_demands_actual)
        - daily_demands_planned: dict[day] -> dict[product] -> demand (ohne Marketing)
        - daily_demands_actual: dict[day] -> dict[product] -> demand (mit Marketing)
    """
    # Prüfe ob bereits berechnet
    if st.session_state.get('volume_planning_calculated', False):
        daily_demands_planned = st.session_state.get('daily_demands_planned', {})
        daily_demands_actual = st.session_state.get('daily_demands_actual', {})
        if daily_demands_planned and daily_demands_actual:
            return daily_demands_planned, daily_demands_actual
    
    # Berechne Nachfrage
    yearly_volume = st.session_state.get('yearly_volume', 370000)
    workday_calc = WorkdayCalculator(year=2027)
    
    # Zwei separate DemandCalculator-Instanzen: eine für geplant, eine für tatsächlich
    demand_calculator_planned = DemandCalculator(yearly_volume, workday_calc)
    demand_calculator_actual = DemandCalculator(yearly_volume, workday_calc)
    
    daily_demands_planned = {}  # day -> {product -> demand}
    daily_demands_actual = {}   # day -> {product -> demand}
    
    # Finde letzten Arbeitstag des Jahres (für korrekte Rest-Aufsummierung)
    last_workday_of_year = None
    for day in range(364, -1, -1):
        if workday_calc.is_workday(day):
            last_workday_of_year = day
            break
    
    # Berechne Nachfrage für alle 365 Tage sequenziell
    scenario_manager = st.session_state.get('scenario_manager', ScenarioManager())
    
    for day in range(365):
        daily_demands_planned[day] = {}
        daily_demands_actual[day] = {}
        
        is_workday = workday_calc.is_workday(day)
        is_last_workday = (day == last_workday_of_year)
        
        if is_workday:
            # Berechne Marketing-Add-ons (wenn vorhanden)
            marketing_add_ons = {}
            marketing_scenarios = scenario_manager.get_marketing_scenarios(day)
            
            if marketing_scenarios:
                month = MasterData.get_month_from_day(day)
                base_daily_floats = demand_calculator_actual._calculate_monthly_base_daily_float(month)
                
                for scenario in marketing_scenarios:
                    factor = scenario.demand_increase_factor
                    for product in MasterData.BOM.keys():
                        base_float = base_daily_floats.get(product, 0.0)
                        add_on = base_float * (factor - 1.0)
                        if product not in marketing_add_ons:
                            marketing_add_ons[product] = 0.0
                        marketing_add_ons[product] += add_on
            
            # Berechne Nachfrage für alle Produkte gleichzeitig (wichtig für korrekte Carry-Over-Logik)
            # Geplante Nachfrage (ohne Marketing)
            planned_demands = demand_calculator_planned.calculate_daily_demand_per_product_dict(
                day, {}, is_last_workday_of_year=is_last_workday
            )
            # Tatsächliche Nachfrage (mit Marketing)
            actual_demands = demand_calculator_actual.calculate_daily_demand_per_product_dict(
                day, marketing_add_ons, is_last_workday_of_year=is_last_workday
            )
            
            for product in MasterData.BOM.keys():
                daily_demands_planned[day][product] = planned_demands.get(product, 0)
                daily_demands_actual[day][product] = actual_demands.get(product, 0)
        else:
            # An Feiertagen/Wochenenden: Alle Nachfragen sind 0
            for product in MasterData.BOM.keys():
                daily_demands_planned[day][product] = 0
                daily_demands_actual[day][product] = 0
    
    # Speichere im Session State
    st.session_state.daily_demands_planned = daily_demands_planned
    st.session_state.daily_demands_actual = daily_demands_actual
    st.session_state.volume_planning_calculated = True
    
    return daily_demands_planned, daily_demands_actual

