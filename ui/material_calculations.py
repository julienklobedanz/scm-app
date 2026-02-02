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
    Berechnet material_inventory_data und saddle_logs synchron zur Produktion.
    
    WICHTIG: Nutzt jetzt die Inbound-Tabelle (`get_inbound_log_dataframe`) als Source of Truth
    für den Wareneingang. Das garantiert, dass Materiallager und Produktion dieselben
    (bereits berechneten) Ankunftsdaten und Mengen sehen – inkl. Vorlauf (z.B. Nov/Dez 2026).
    
    WICHTIG: Berechnungen werden nur durchgeführt, wenn PRODUCT_SALES_SHARES und SEASONALITY jeweils 100% ergeben.
    
    Returns:
        Tuple (material_inventory_data, saddle_logs)
        - material_inventory_data: Dict[date] -> Dict[saddle] -> stock_morning
        - saddle_logs: Dict[saddle] -> List[Dict] (für UI-Anzeige)
    """
    # KRITISCH: Validiere Parameter bevor Berechnungen erfolgen
    from ui.volume_planning_utils import _validate_parameters
    is_valid, error_message = _validate_parameters()
    if not is_valid:
        return {}, {}
    
    if 'simulator' not in st.session_state or st.session_state.simulator is None:
        return {}, {}
    
    # PERFORMANCE: Cache-Key für Invalidierung
    volume_planning_cache_key = st.session_state.get('volume_planning_cache_key', None)
    production_logs_cache_key = st.session_state.get('production_logs_cache_key', None)
    cache_key = f"material_inventory_v2_{volume_planning_cache_key}_{production_logs_cache_key}"
    
    # PERFORMANCE: Prüfe Cache zuerst (schnellerer Check)
    # KRITISCH: Prüfe auch ob saddle_logs_cache vorhanden ist, da material_inventory_data allein nicht ausreicht
    if ('material_inventory_data' in st.session_state and 
        st.session_state.get('material_inventory_cache_key') == cache_key and
        'saddle_logs_cache' in st.session_state):
        # Lade aus Cache
        material_inventory_data = st.session_state.material_inventory_data
        # Verwende gecachte saddle_logs (wurden bereits berechnet)
        saddle_logs = st.session_state.saddle_logs_cache
        return material_inventory_data, saddle_logs
    
    simulator = st.session_state.simulator
    manager = simulator.china_transport_manager
    
    planning_year = st.session_state.get('planning_year', 2027)
    workday_calc = WorkdayCalculator(year=planning_year)
    start_date_simulation = date(planning_year, 1, 1)
    
    saddle_shares = MasterData.calculate_saddle_shares()
    saddle_types = list(saddle_shares.keys())
    
    saddle_logs = {saddle_type: [] for saddle_type in saddle_types}
    
    # -------------------------------------------------------
    # 1. INBOUND DATEN SAMMELN (Aus der Inbound-Tabelle)
    # -------------------------------------------------------
    receipts_by_date_and_saddle: Dict[date, Dict[str, float]] = {}
    
    if manager:
        inbound_df = manager.get_inbound_log_dataframe(saddle_shares)
        if not inbound_df.empty:
            # Source-of-truth Spalte: diese wird auch für Materialzugang genutzt
            avail_col = 'Tatsächliche Ankunft LKW 🇩🇪'

            # PERFORMANCE: Vektorisierte Verarbeitung statt iterrows()
            valid_rows = inbound_df[inbound_df[avail_col].notna() & (inbound_df[avail_col].astype(str).str.strip() != '')]
            if not valid_rows.empty:
                try:
                    valid_rows = valid_rows.copy()
                    valid_rows['_parsed_date'] = pd.to_datetime(valid_rows[avail_col], format=MasterData.DATE_FORMAT, errors='coerce').dt.date
                    valid_rows = valid_rows[valid_rows['_parsed_date'].notna()]
                    
                    # Gruppiere nach Datum und summiere Mengen pro Sattel-Typ
                    for _, row in valid_rows.iterrows():
                        avail_date = row['_parsed_date']
                        if avail_date not in receipts_by_date_and_saddle:
                            receipts_by_date_and_saddle[avail_date] = {s: 0.0 for s in saddle_types}
                        
                        for saddle_name in saddle_types:
                            if saddle_name in row:
                                qty_val = row[saddle_name]
                                try:
                                    if isinstance(qty_val, str):
                                        qty_val = qty_val.strip()
                                        if qty_val == '' or qty_val == '-':
                                            continue
                                    qty = float(qty_val) if qty_val else 0.0
                                    if qty > 0:
                                        receipts_by_date_and_saddle[avail_date][saddle_name] += qty
                                except (ValueError, TypeError):
                                    continue
                except Exception:
                    # Fallback auf alte Methode
                    for _, row in inbound_df.iterrows():
                        avail_str = row.get(avail_col, '')
                        if not avail_str or (isinstance(avail_str, str) and avail_str.strip() == ''):
                            continue

                        try:
                            avail_date = datetime.strptime(avail_str, MasterData.DATE_FORMAT).date()
                        except (ValueError, TypeError):
                            continue

                        if avail_date not in receipts_by_date_and_saddle:
                            receipts_by_date_and_saddle[avail_date] = {s: 0.0 for s in saddle_types}

                        for saddle_name in saddle_types:
                            qty_val = row.get(saddle_name, 0)
                            try:
                                if isinstance(qty_val, str):
                                    qty_val = qty_val.strip()
                                    if qty_val == '' or qty_val == '-':
                                        continue
                                qty = float(qty_val) if qty_val else 0.0
                            except (ValueError, TypeError):
                                continue

                            if qty > 0:
                                receipts_by_date_and_saddle[avail_date][saddle_name] += qty
    
    # Erstes Datum im Materiallager = erste tatsächliche Ankunft LKW DE (reagiert auf Vorlaufzeit)
    if receipts_by_date_and_saddle:
        first_lkw_de_arrival_date = min(receipts_by_date_and_saddle.keys())
    else:
        first_lkw_de_arrival_date = date(planning_year - 1, 11, 1)  # Fallback
    st.session_state.material_lager_first_date = first_lkw_de_arrival_date
    
    # -------------------------------------------------------
    # 2. MATERIALVERBRAUCH VORVERARBEITEN (aus Produktions-Log)
    # -------------------------------------------------------
    # Cache für Produktionsdaten laden
    if 'production_logs_cache' not in st.session_state:
        # Fallback: Versuche zu berechnen (sollte aber eigentlich da sein)
        from ui.production_calculations import calculate_production_logs
        production_logs_cache = calculate_production_logs()
    else:
        production_logs_cache = st.session_state.production_logs_cache
    
    # Pre-Processing: Produktionsdaten in schnelles Lookup-Format wandeln
    # Map: Date -> Saddle -> ConsumedQty
    consumption_map = {}
    
    for product_name, df in production_logs_cache.items():
        if df.empty or 'Datum' not in df.columns:
            continue
            
        required_saddle = MasterData.BOM.get(product_name, {}).get('saddle')
        if not required_saddle:
            continue
        
        # Sicherstellen dass Spalte existiert
        col_name = 'material_verbrauch' if 'material_verbrauch' in df.columns else 'tatsächliche PM'
        if col_name not in df.columns:
            continue
        
        for idx, row in df.iterrows():
            d_str = row.get('Datum', '')
            if d_str:
                try:
                    d = datetime.strptime(d_str, MasterData.DATE_FORMAT).date()
                    qty = row.get(col_name, 0)
                    try:
                        qty = float(qty) if qty else 0.0
                    except (ValueError, TypeError):
                        qty = 0.0
                    
                    if qty > 0:
                        if d not in consumption_map:
                            consumption_map[d] = {}
                        if required_saddle not in consumption_map[d]:
                            consumption_map[d][required_saddle] = 0.0
                        consumption_map[d][required_saddle] += qty
                except (ValueError, TypeError):
                    continue
    
    # -------------------------------------------------------
    # 3. MATERIALVERBRAUCH & BESTAND BERECHNEN
    # -------------------------------------------------------
    # Start = erste tatsächliche Ankunft LKW DE aus Inbound (dynamisch auf Vorlaufzeit)
    # Ende bis 10.01.(Jahr+1) für konsistente Berechnungen
    start_date_log = first_lkw_de_arrival_date
    end_date_log = date(planning_year + 1, 1, 10)  # Erweitert bis 10.01.2028
    total_days = (end_date_log - start_date_log).days + 1
    
    stock_by_saddle = {saddle_type: 0.0 for saddle_type in saddle_types}
    material_inventory_data = {}
    
    # HAUPTSCHLEIFE ÜBER TAGE
    for day_offset in range(total_days):
        current_date = start_date_log + timedelta(days=day_offset)
        day = (current_date - start_date_simulation).days
        
        # Wochentag / Feiertag
        weekday = current_date.weekday()
        weekday_abbr = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'][weekday]
        is_weekend = weekday >= 5
        is_holiday = False
        is_workday = False
        
        if 0 <= day < 365:
            if current_date in workday_calc.german_holidays:
                is_holiday = True
            # Prüfe ob Arbeitstag (berücksichtigt DAILY_WORKLOAD)
            is_workday = workday_calc.is_workday(day)
        
        # 1. Zugang (aus transport_status - synchron mit Produktion!)
        receipt_by_saddle = receipts_by_date_and_saddle.get(current_date, {s: 0.0 for s in saddle_types})
        
        # 2. Verbrauch (aus Produktions-Log)
        consumed_today = consumption_map.get(current_date, {})
        
        # 3. Alle Wasserschaden-Szenarien für diesen Tag (mehrere parallel möglich)
        water_damage_scenarios_for_day = []
        scenario_manager = st.session_state.get('scenario_manager')
        if scenario_manager and 0 <= day < 365:
            for scenario in scenario_manager.get_water_damage_scenarios(day):
                if scenario.start_day == scenario.end_day and scenario.start_day == day:
                    water_damage_scenarios_for_day.append(scenario)
        
        stock_morning = {}
        stock_evening = {}
        
        for s in saddle_types:
            # Bestand morgens = Bestand gestern abend + Zugang heute
            stock_morning[s] = stock_by_saddle[s] + receipt_by_saddle.get(s, 0.0)
            
            # Abgang = Was die Produktion tatsächlich verbraucht hat
            planned_issue = consumed_today.get(s, 0.0)
            actual_issue = min(planned_issue, stock_morning[s])
            
            # Bestand abends (vor optionalem Wasserschaden-Abzug)
            stock_evening[s] = max(0.0, stock_morning[s] - actual_issue)
            
            # WASSERSCHADEN: alle Szenarien für diesen Tag anwenden (Verlust pro Szenario für betroffene Satteltypen)
            loss_qty = 0.0
            for scenario in water_damage_scenarios_for_day:
                affected_saddles = getattr(scenario, 'affected_saddles', None)
                applies_to_saddle = (not affected_saddles or len(affected_saddles) == 0 or s in affected_saddles)
                
                if not applies_to_saddle:
                    continue
                
                # Verwende loss_by_saddle wenn vorhanden, sonst Fallback auf loss_quantity_absolute (Rückwärtskompatibilität)
                loss_by_saddle = getattr(scenario, 'loss_by_saddle', None)
                if loss_by_saddle and s in loss_by_saddle:
                    # Pro-Satteltyp Verlustmenge
                    loss_amount = loss_by_saddle[s]
                    deduct = min(int(loss_amount), int(round(stock_evening[s])))
                    loss_qty += deduct
                    stock_evening[s] = max(0.0, stock_evening[s] - deduct)
                else:
                    # Fallback: loss_quantity_absolute (alte Implementierung)
                    loss_abs = max(0.0, getattr(scenario, 'loss_quantity_absolute', 0.0))
                    if loss_abs > 0:
                        deduct = min(loss_abs, stock_evening[s])
                        loss_qty += deduct
                        stock_evening[s] = max(0.0, stock_evening[s] - deduct)
            
            # Übertrag für nächsten Tag
            stock_by_saddle[s] = stock_evening[s]
            
            # Log Entry für UI
            saddle_logs[s].append({
                'Wochentag': weekday_abbr,
                'Datum': current_date.strftime(MasterData.DATE_FORMAT),
                'Lagerzugang': int(round(receipt_by_saddle.get(s, 0.0))) if receipt_by_saddle.get(s, 0.0) > 0 else 0,
                'Bestand morgens': int(round(stock_morning[s])),
                'Lagerabgang': int(round(actual_issue)),
                'Verlustmenge': int(round(loss_qty)) if loss_qty > 0 else 0,
                'Bestand abends': int(round(stock_evening[s])),
                'Is_Weekend': is_weekend,
                'Is_Holiday': is_holiday,
                'Is_Workday': is_workday
            })
            
        material_inventory_data[current_date] = stock_morning.copy()
    
    # PERFORMANCE: Speichere im Session State mit Cache-Key
    st.session_state.material_inventory_data = material_inventory_data
    st.session_state.material_inventory_cache_key = cache_key
    # KRITISCH: Speichere auch saddle_logs im Cache, damit sie beim nächsten Aufruf verfügbar sind
    st.session_state.saddle_logs_cache = saddle_logs
    return material_inventory_data, saddle_logs
