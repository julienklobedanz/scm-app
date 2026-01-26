"""
Volume Planning Utilities
Berechnet Nachfrage aus Volumenplanung für Verwendung im Simulator
"""

import streamlit as st
from simulation.workday_calculator import WorkdayCalculator
from simulation.demand_calculator import DemandCalculator
from config.master_data import MasterData
from models.scenarios import (
    ScenarioManager,
    StandardScenario,
    MarketingCampaignScenario,
    WarehouseDamageScenario,
    SupplierBreakdownScenario,
    DeliveryProblemScenario,
)


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
    # WICHTIG: Cache ist abhängig von Jahr, yearly_volume und aktiven Szenarien
    planning_year = st.session_state.get('planning_year', 2027)
    yearly_volume = st.session_state.get('yearly_volume', 370000)

    def _scenario_fingerprint(scenario_manager: ScenarioManager) -> tuple:
        """
        Erzeugt einen stabilen Fingerprint der aktiven Szenarien.
        Wichtig für Cache-Invalidierung: Wenn sich Szenarien ändern, muss neu berechnet werden.
        """
        items: list[tuple] = []
        for s in getattr(scenario_manager, "scenarios", []):
            if isinstance(s, StandardScenario):
                continue
            # Basisschlüssel
            base = (
                s.__class__.__name__,
                getattr(s, "active", True),
                getattr(s, "start_day", None),
                getattr(s, "end_day", None),
            )

            # Szenario-spezifische Parameter
            if isinstance(s, MarketingCampaignScenario):
                # affected_products muss in den Fingerprint, damit Cache invalidiert wird
                affected_products = getattr(s, "affected_products", None)
                # Konvertiere Liste zu Tuple für Hashbarkeit, sortiere für Konsistenz
                affected_products_tuple = tuple(sorted(affected_products)) if affected_products else None
                extra = (getattr(s, "demand_increase_factor", None), affected_products_tuple)
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
                # Fallback für zukünftige Szenarien
                extra = tuple(sorted(vars(s).items()))

            items.append(base + extra)

        # Reihenfolge stabilisieren
        return tuple(sorted(items))

    scenario_manager = st.session_state.get('scenario_manager', ScenarioManager())
    cache_key = (planning_year, yearly_volume, _scenario_fingerprint(scenario_manager))
    cached_key = st.session_state.get('volume_planning_cache_key', None)

    if st.session_state.get('volume_planning_calculated', False) and cached_key == cache_key:
        daily_demands_planned = st.session_state.get('daily_demands_planned', {})
        daily_demands_actual = st.session_state.get('daily_demands_actual', {})
        # WICHTIG: Prüfe nicht nur ob die Dictionaries existieren, sondern auch ob sie vollständig sind
        if daily_demands_planned and daily_demands_actual and len(daily_demands_planned) == 365 and len(daily_demands_actual) == 365:
            return daily_demands_planned, daily_demands_actual
    
    # Berechne Nachfrage
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
                    # Bestimme betroffene Produkte: Wenn None, dann alle Produkte (Rückwärtskompatibilität)
                    affected_products = scenario.affected_products if scenario.affected_products is not None else list(MasterData.BOM.keys())
                    
                    for product in affected_products:
                        if product not in MasterData.BOM:
                            continue  # Überspringe ungültige Produkte
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
    # Dies stellt sicher, dass jedes Produkt seine exakte Zielsumme erreicht, auch wenn Reste durch Rundung verloren gehen.
    #
    # WICHTIG: Diese Korrektur darf NUR für die geplante Nachfrage gelten.
    # Für die tatsächliche Nachfrage (mit Marketing/Szenarien) würde eine erzwungene Zielsumme sonst zu
    # negativen Rest-Korrekturen am Jahresende führen und Szenario-Effekte "wegkorrigieren".
    #
    # OPTIMIERUNG: Berechne Summen effizienter (nur einmal über alle Tage iterieren)
    if last_workday_of_year is not None:
        demands_dict = daily_demands_planned
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
    
    # Speichere im Session State (mit Cache-Key für Invalidierung)
    st.session_state.daily_demands_planned = daily_demands_planned
    st.session_state.daily_demands_actual = daily_demands_actual
    st.session_state.volume_planning_calculated = True
    st.session_state.volume_planning_year = planning_year  # Backward-compat / Debug
    st.session_state.volume_planning_cache_key = cache_key
    
    return daily_demands_planned, daily_demands_actual

