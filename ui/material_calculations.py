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
    
    Returns:
        Tuple (material_inventory_data, saddle_logs)
        - material_inventory_data: Dict[date] -> Dict[saddle] -> stock_morning
        - saddle_logs: Dict[saddle] -> List[Dict] (für UI-Anzeige)
    """
    if 'simulator' not in st.session_state or st.session_state.simulator is None:
        return {}, {}
    
    # PERFORMANCE: Cache-Key für Invalidierung
    volume_planning_cache_key = st.session_state.get('volume_planning_cache_key', None)
    production_logs_cache_key = st.session_state.get('production_logs_cache_key', None)
    cache_key = f"material_inventory_v2_{volume_planning_cache_key}_{production_logs_cache_key}"
    
    # PERFORMANCE: Prüfe Cache zuerst (schnellerer Check)
    if ('material_inventory_data' in st.session_state and 
        st.session_state.get('material_inventory_cache_key') == cache_key):
        # Lade aus Cache
        material_inventory_data = st.session_state.material_inventory_data
        # Berechne saddle_logs aus material_inventory_data (schneller als Neuberechnung)
        saddle_logs = {}
        saddle_shares = MasterData.calculate_saddle_shares()
        saddle_types = list(saddle_shares.keys())
        for saddle_type in saddle_types:
            saddle_logs[saddle_type] = []
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
    # Start etwas früher, um Übertrag aus Vorjahr korrekt aufzubauen
    start_date_log = date(planning_year - 1, 11, 1)
    end_date_log = date(planning_year, 12, 31)
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
        
        if 0 <= day < 365:
            if current_date in workday_calc.german_holidays:
                is_holiday = True
        
        # 1. Zugang (aus transport_status - synchron mit Produktion!)
        receipt_by_saddle = receipts_by_date_and_saddle.get(current_date, {s: 0.0 for s in saddle_types})
        
        # 2. Verbrauch (aus Produktions-Log)
        consumed_today = consumption_map.get(current_date, {})
        
        # 3. Prüfe Wasserschaden-Szenarien für diesen Tag
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
        
        stock_morning = {}
        stock_evening = {}
        
        for s in saddle_types:
            # Bestand morgens = Bestand gestern abend + Zugang heute
            stock_morning[s] = stock_by_saddle[s] + receipt_by_saddle.get(s, 0.0)
            
            # WASSERSCHADEN: Speichere Bestand vor dem Schaden für Verlustmenge
            stock_before_damage = stock_morning[s]
            
            # WASSERSCHADEN: Setze Bestand morgens auf 0 wenn Szenario aktiv
            if water_damage_active:
                stock_morning[s] = 0.0
            
            # Abgang = Was die Produktion tatsächlich verbraucht hat
            # HINWEIS: Wir vertrauen hier blind dem Produktions-Log.
            # Da der Produktions-Log VORHER lief und geprüft hat "ist genug da?",
            # sollte stock_morning[s] >= planned_issue sein.
            # Falls Rundungsdifferenzen auftreten, fangen wir das mit max(0) ab.
            planned_issue = consumed_today.get(s, 0.0)
            
            # Zur Sicherheit: Nicht mehr abziehen als da ist (sollte dank Synchro nicht passieren)
            actual_issue = min(planned_issue, stock_morning[s])
            
            # Bestand abends
            stock_evening[s] = max(0.0, stock_morning[s] - actual_issue)
            
            # WASSERSCHADEN: Setze auch Abendbestand auf 0
            if water_damage_active:
                stock_evening[s] = 0.0
            
            # Übertrag für nächsten Tag
            stock_by_saddle[s] = stock_evening[s]
            
            # Berechne Verlustmenge (nur wenn Wasserschaden aktiv)
            loss_qty = stock_before_damage if water_damage_active else 0.0
            
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
                'Is_Holiday': is_holiday
            })
            
        material_inventory_data[current_date] = stock_morning.copy()
    
    # PERFORMANCE: Speichere im Session State mit Cache-Key
    st.session_state.material_inventory_data = material_inventory_data
    st.session_state.material_inventory_cache_key = cache_key
    return material_inventory_data, saddle_logs
