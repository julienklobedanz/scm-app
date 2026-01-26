"""
Material Calculations
Berechnungslogik für Materiallager (ohne UI-Rendering)
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Dict
from config.master_data import MasterData
from simulation.workday_calculator import WorkdayCalculator
from models.scenarios import WaterDamageScenario


def calculate_material_inventory():
    """
    Berechnet material_inventory_data und saddle_logs ohne UI-Rendering.
    Diese Funktion kann beim App-Start aufgerufen werden, ohne dass Streamlit-Widgets gerendert werden.
    
    Returns:
        Tuple (material_inventory_data, saddle_logs)
        - material_inventory_data: Dict[date] -> Dict[saddle] -> stock_morning
        - saddle_logs: Dict[saddle] -> List[Dict] (für UI-Anzeige)
    """
    if 'simulator' not in st.session_state or st.session_state.simulator is None:
        return {}, {}
    
    planning_year = st.session_state.get('planning_year', 2027)
    workday_calc = WorkdayCalculator(year=planning_year)
    start_date_simulation = date(planning_year, 1, 1)
    
    saddle_shares = MasterData.calculate_saddle_shares()
    saddle_types = list(saddle_shares.keys())
    
    saddle_logs = {saddle_type: [] for saddle_type in saddle_types}
    
    # Hole Inbound-Daten
    manager = st.session_state.simulator.china_transport_manager
    receipts_by_date_and_saddle: Dict[date, Dict[str, float]] = {}
    
    if manager:
        inbound_df = manager.get_inbound_log_dataframe(saddle_shares)
        
        if not inbound_df.empty:
            avail_col_idx = inbound_df.columns.get_loc('Tatsächliche Ankunft LKW 🇩🇪')
            saddle_col_indices = {s: inbound_df.columns.get_loc(s) for s in saddle_types if s in inbound_df.columns}
            
            for row_tuple in inbound_df.itertuples(index=False, name=None):
                avail_str = row_tuple[avail_col_idx] if avail_col_idx < len(row_tuple) else None
                if avail_str and isinstance(avail_str, str) and len(avail_str) > 0:
                    try:
                        avail_date = datetime.strptime(avail_str, MasterData.DATE_FORMAT).date()
                        
                        if avail_date not in receipts_by_date_and_saddle:
                            receipts_by_date_and_saddle[avail_date] = {s: 0.0 for s in saddle_types}
                        
                        for saddle, col_idx in saddle_col_indices.items():
                            if col_idx < len(row_tuple):
                                qty_val = row_tuple[col_idx]
                                if qty_val and str(qty_val).strip() != '':
                                    try:
                                        receipts_by_date_and_saddle[avail_date][saddle] += float(qty_val)
                                    except (ValueError, TypeError):
                                        pass
                    except (ValueError, TypeError):
                        continue
    
    # Materiallager berechnen
    start_date_log = date(planning_year - 1, 11, 1)
    end_date_log = date(planning_year, 12, 31)
    total_days = (end_date_log - start_date_log).days + 1
    
    stock_by_saddle = {saddle_type: 0.0 for saddle_type in saddle_types}
    material_inventory_data = {}
    
    results_df = st.session_state.get('results_df')
    if results_df is None:
        return {}, {}
    
    for day_offset in range(total_days):
        current_date = start_date_log + timedelta(days=day_offset)
        day = (current_date - start_date_simulation).days
        
        # Wochentag / Feiertag
        weekday = current_date.weekday()
        weekday_abbr = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'][weekday]
        is_weekend = weekday >= 5
        is_holiday = False
        if 0 <= day < 365:
            if current_date in workday_calc.german_holidays:
                is_holiday = True
        
        receipt_by_saddle = receipts_by_date_and_saddle.get(current_date, {s: 0.0 for s in saddle_types})
        
        stock_morning = {}
        stock_evening = {}
        issue_by_saddle = {s: 0.0 for s in saddle_types}
        
        # Verbrauch aus production_logs_cache
        if 'production_logs_cache' not in st.session_state:
            continue
        
        production_logs_cache = st.session_state.production_logs_cache
        production_by_product_from_logs = {}
        
        for product_name in MasterData.BOM.keys():
            if product_name in production_logs_cache:
                df = production_logs_cache[product_name]
                if not df.empty and 'Datum' in df.columns and 'tatsächliche PM' in df.columns:
                    current_date_str = current_date.strftime(MasterData.DATE_FORMAT)
                    matching_rows = df[df['Datum'] == current_date_str]
                    if not matching_rows.empty:
                        # OPTION 4: Verwende material_verbrauch wenn vorhanden, sonst Fallback auf tatsächliche PM
                        # Dies stellt sicher, dass Materiallager den korrekten Verbrauch verwendet
                        material_verbrauch = matching_rows.iloc[0].get('material_verbrauch', None)
                        actual_pm = matching_rows.iloc[0].get('tatsächliche PM', 0)
                        
                        # Verwende material_verbrauch wenn vorhanden, sonst actual_pm (Fallback)
                        if material_verbrauch is not None:
                            try:
                                production_by_product_from_logs[product_name] = int(material_verbrauch) if material_verbrauch > 0 else 0
                            except (ValueError, TypeError):
                                # Fallback auf actual_pm wenn material_verbrauch ungültig
                                try:
                                    production_by_product_from_logs[product_name] = int(actual_pm) if actual_pm > 0 else 0
                                except (ValueError, TypeError):
                                    production_by_product_from_logs[product_name] = 0
                        else:
                            # Fallback auf actual_pm wenn material_verbrauch nicht vorhanden
                            try:
                                production_by_product_from_logs[product_name] = int(actual_pm) if actual_pm > 0 else 0
                            except (ValueError, TypeError):
                                production_by_product_from_logs[product_name] = 0
                    else:
                        production_by_product_from_logs[product_name] = 0
                else:
                    production_by_product_from_logs[product_name] = 0
            else:
                production_by_product_from_logs[product_name] = 0
        
        for product_name, qty in production_by_product_from_logs.items():
            if qty > 0 and product_name in MasterData.BOM:
                required_saddle = MasterData.BOM[product_name]['saddle']
                if required_saddle in issue_by_saddle:
                    issue_by_saddle[required_saddle] += qty
        
        # Prüfe Wasserschaden-Szenarien für diesen Tag
        water_damage_active = False
        scenario_manager = st.session_state.get('scenario_manager')
        if scenario_manager and 0 <= day < 365:
            water_damage_scenarios = scenario_manager.get_water_damage_scenarios(day)
            if water_damage_scenarios:
                # Prüfe ob exaktes Datum (start_day == end_day)
                for scenario in water_damage_scenarios:
                    if scenario.start_day == scenario.end_day and scenario.start_day == day:
                        water_damage_active = True
                        break
        
        for s in saddle_types:
            stock_morning[s] = stock_by_saddle[s] + receipt_by_saddle.get(s, 0.0)
            
            # WASSERSCHADEN: Speichere Bestand vor dem Schaden für Verlustmenge
            stock_before_damage = stock_morning[s]
            
            # WASSERSCHADEN: Setze Bestand morgens auf 0 wenn Szenario aktiv
            if water_damage_active:
                stock_morning[s] = 0.0
            
            actual_issue = min(issue_by_saddle[s], stock_morning[s])
            val = stock_morning[s] - actual_issue
            stock_evening[s] = max(0.0, val)
            
            # WASSERSCHADEN: Setze auch Abendbestand auf 0
            if water_damage_active:
                stock_evening[s] = 0.0
            
            stock_by_saddle[s] = stock_evening[s]
            
            # Berechne Verlustmenge (nur wenn Wasserschaden aktiv)
            loss_qty = stock_before_damage if water_damage_active else 0.0
            
            saddle_logs[s].append({
                'Wochentag': weekday_abbr,
                'Datum': current_date.strftime(MasterData.DATE_FORMAT),
                'Lagerzugang': int(round(receipt_by_saddle.get(s, 0.0))) if receipt_by_saddle.get(s, 0.0) > 0 else 0,
                'Bestand morgens': int(round(stock_morning[s])),
                'Lagerabgang': int(round(actual_issue)),
                'Verlustmenge': int(round(loss_qty)) if loss_qty > 0 else 0,
                'Bestand abends': int(round(stock_evening[s])),
                'Is_Weekend': is_weekend,
                'Is_Holiday': is_holiday
            })
            
        material_inventory_data[current_date] = stock_morning.copy()
    
    st.session_state.material_inventory_data = material_inventory_data
    return material_inventory_data, saddle_logs
