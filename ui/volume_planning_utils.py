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
    # Prüfe ob bereits berechnet (mit strikter Prüfung, um Endlosschleifen zu vermeiden)
    # WICHTIG: Prüfe auch, ob das Jahr übereinstimmt (Cache ist jahr-spezifisch)
    planning_year = st.session_state.get('planning_year', 2027)
    cached_year = st.session_state.get('volume_planning_year', None)
    
    if (st.session_state.get('volume_planning_calculated', False) and 
        cached_year == planning_year):
        daily_demands_planned = st.session_state.get('daily_demands_planned', {})
        daily_demands_actual = st.session_state.get('daily_demands_actual', {})
        # WICHTIG: Prüfe nicht nur ob die Dictionaries existieren, sondern auch ob sie vollständig sind
        if daily_demands_planned and daily_demands_actual and len(daily_demands_planned) == 365 and len(daily_demands_actual) == 365:
            return daily_demands_planned, daily_demands_actual
    
    # Berechne Nachfrage
    yearly_volume = st.session_state.get('yearly_volume', 370000)
    planning_year = st.session_state.get('planning_year', 2027)
    workday_calc = WorkdayCalculator(year=planning_year)
    
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
    
    # KRITISCH: Korrigiere Summe pro Produkt auf exakt yearly_volume * sales_share (unabhängig von Feiertagsverteilung)
    # Dies stellt sicher, dass jedes Produkt seine exakte Zielsumme erreicht, auch wenn Reste durch Rundung verloren gehen
    # WICHTIG: Die Korrektur muss pro Produkt erfolgen, nicht nur für die Gesamtsumme!
    # OPTIMIERUNG: Berechne Summen effizienter (nur einmal über alle Tage iterieren)
    if last_workday_of_year is not None:
        for demands_dict in [daily_demands_planned, daily_demands_actual]:
            # Berechne alle Produktsummen in einem Durchgang (effizienter)
            product_sums = {product: 0 for product in MasterData.BOM.keys()}
            for day in range(365):
                for product in MasterData.BOM.keys():
                    product_sums[product] += demands_dict[day].get(product, 0)
            
            # Korrigiere jedes Produkt
            for product in MasterData.BOM.keys():
                # Berechne Zielsumme für dieses Produkt: yearly_volume * sales_share
                sales_share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)
                target_sum = int(yearly_volume * sales_share)
                
                # Berechne Differenz
                difference = target_sum - product_sums[product]
                
                # Wenn Differenz != 0, korrigiere am letzten Arbeitstag
                if difference != 0:
                    demands_dict[last_workday_of_year][product] = demands_dict[last_workday_of_year].get(product, 0) + difference
    
    # Speichere im Session State (mit Jahr-Information für Cache-Validierung)
    st.session_state.daily_demands_planned = daily_demands_planned
    st.session_state.daily_demands_actual = daily_demands_actual
    st.session_state.volume_planning_calculated = True
    st.session_state.volume_planning_year = planning_year  # Speichere Jahr für Cache-Validierung
    
    return daily_demands_planned, daily_demands_actual

