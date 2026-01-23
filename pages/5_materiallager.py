"""
Materiallager - Seite
Zeigt Sattelzugänge, Bestände und Verluste
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta, datetime
from typing import Dict
from config.master_data import MasterData
from simulation.simulator import Simulator
from models.scenarios import ScenarioManager
from simulation.workday_calculator import WorkdayCalculator
from ui.scenario_sidebar import render_scenario_sidebar

st.set_page_config(page_title="Materiallager", layout="wide", page_icon="📦")

# CSS für Menü-Formatierung (Großbuchstaben und Fett) und fixierte Summenzeilen
st.markdown("""
<style>
    /* Menüeinträge großgeschrieben und fett */
    [data-testid="stSidebarNav"] a {
        font-weight: bold !important;
        text-transform: capitalize !important;
    }
    /* Fixierte Summenzeile - letzte Zeile bleibt beim Scrollen sichtbar */
    .stDataFrame [data-testid="stDataFrame"] table tbody tr:last-child {
        position: sticky !important;
        bottom: 0 !important;
        background-color: #e0e0e0 !important;
        z-index: 100 !important;
    }
    .stDataFrame [data-testid="stDataFrame"] table tbody tr:last-child td {
        background-color: #e0e0e0 !important;
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)

render_scenario_sidebar(key_suffix="_materiallager")

# Init Session State
from ui.utils import initialize_session_state, run_happy_path_simulation
from ui.volume_planning_utils import calculate_volume_planning_demand

initialize_session_state()

# WICHTIG: Stelle sicher, dass daily_demands_actual aktualisiert wird, wenn sich Szenarien ändern
# Dies ist notwendig, damit der Materialverbrauch korrekt berechnet wird
calculate_volume_planning_demand()

st.title("📦 Materiallager")
st.markdown("Übersicht über Sattelzugänge, Bestände und Verluste")

# Happy Path Simulation
run_happy_path_simulation()

# WICHTIG: Stelle sicher, dass production_logs_cache berechnet wurde
# Dies ist notwendig, damit der Materialverbrauch aus den dynamisch aktualisierten "tatsächlichen PM" berechnet werden kann
if 'production_logs_cache' not in st.session_state:
    # Importiere get_production_logs aus Produktionsseite
    try:
        import sys
        import os
        produktion_path = os.path.join(os.path.dirname(__file__), "6_produktion.py")
        if os.path.exists(produktion_path):
            import importlib.util
            spec = importlib.util.spec_from_file_location("produktion_module", produktion_path)
            if spec and spec.loader:
                produktion_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(produktion_module)
                # Berechne production_logs_cache (wird gecacht)
                produktion_module.get_production_logs()
    except Exception:
        # Stille Fehlerbehandlung - production_logs_cache wird später geladen
        pass

if st.session_state.results_df is None:
    st.warning("⚠️ Keine Simulationsergebnisse verfügbar.")
    st.stop()

results_df = st.session_state.results_df

# Zeitraum
planning_year = st.session_state.get('planning_year', 2027)
start_date = date(planning_year - 1, 12, 31)
end_date = date(planning_year, 12, 31)
workday_calc = WorkdayCalculator(year=planning_year)
start_date_simulation = date(planning_year, 1, 1)

def create_saddle_inventory_log():
    """Erstellt Sattel-Lager-Log synchronisiert mit Inbound-Daten"""
    saddle_shares = MasterData.calculate_saddle_shares()
    saddle_types = list(saddle_shares.keys())
    
    saddle_logs = {saddle_type: [] for saddle_type in saddle_types}
    
    # 1. Hole die "Wahrheit" von der Inbound-Logik
    manager = None
    if st.session_state.simulator:
        manager = st.session_state.simulator.china_transport_manager
    elif st.session_state.kpis and 'china_transport_manager' in st.session_state.kpis:
        manager = st.session_state.kpis['china_transport_manager']
    
    receipts_by_date_and_saddle: Dict[date, Dict[str, float]] = {}
    
    if manager:
        # Rufe die Inbound-Tabelle ab (enthält die korrekte 500er Logik und Termine)
        inbound_df = manager.get_inbound_log_dataframe(saddle_shares)
        
        # OPTIMIERUNG: Verwende itertuples() statt iterrows() (3-5× schneller)
        # Scanne die Inbound-Tabelle nach Wareneingängen
        if not inbound_df.empty:
            # Hole Spalten-Index für besseren Zugriff
            avail_col_idx = inbound_df.columns.get_loc('Verfügbar im Lager 🇩🇪')
            saddle_col_indices = {s: inbound_df.columns.get_loc(s) for s in saddle_types if s in inbound_df.columns}
            
            # itertuples() gibt NamedTuples zurück, Zugriff über Index
            for row_tuple in inbound_df.itertuples(index=False, name=None):
                # Datum "Verfügbar im Lager 🇩🇪" lesen (Zugriff über Index)
                avail_str = row_tuple[avail_col_idx] if avail_col_idx < len(row_tuple) else None
                if avail_str and isinstance(avail_str, str) and len(avail_str) > 0:
                    try:
                        avail_date = datetime.strptime(avail_str, MasterData.DATE_FORMAT).date()
                        
                        if avail_date not in receipts_by_date_and_saddle:
                            receipts_by_date_and_saddle[avail_date] = {s: 0.0 for s in saddle_types}
                        
                        # Mengen pro Sattel auslesen und addieren
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

    # 2. Materiallager berechnen
    # Startdatum: Früher ansetzen, um Vorlauf (Initial Stock) mitzunehmen!
    # Die Schleife beginnt ab November des Vorjahres, sammelt die ersten Lieferungen ein,
    # zieht die ersten Verbräuche ab, und kommt dann am Jahresanfang mit dem korrekten Bestand an
    start_date_log = date(planning_year - 1, 11, 1)
    end_date_log = date(planning_year, 12, 31)
    total_days = (end_date_log - start_date_log).days + 1
    
    stock_by_saddle = {saddle_type: 0.0 for saddle_type in saddle_types}
    material_inventory_data = {}
    
    for day_offset in range(total_days):
        current_date = start_date_log + timedelta(days=day_offset)
        day = (current_date - start_date_simulation).days
        
        # Wochentag / Feiertag - OPTIMIERUNG: Direkte Berechnung statt get_day_info()
        weekday = current_date.weekday()
        weekday_abbr = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'][weekday]
        is_weekend = weekday >= 5
        # OPTIMIERUNG: Nur prüfen wenn innerhalb des Jahres
        # Feiertag: Nicht Wochenende und nicht Arbeitstag
        is_holiday = False
        if 0 <= day < 365:
            # Prüfe direkt gegen deutsche Feiertage
            if current_date in workday_calc.german_holidays:
                is_holiday = True
        
        # Zugang (aus Inbound-Daten)
        receipt_by_saddle = receipts_by_date_and_saddle.get(current_date, {s: 0.0 for s in saddle_types})
        
        # Bestand berechnen
        stock_morning = {}
        stock_evening = {}
        issue_by_saddle = {s: 0.0 for s in saddle_types}
        
        # Verbrauch (Produktion DE) - Dynamische Berechnung mit Marketing-Berücksichtigung
        # WICHTIG: Berechne Produktion dynamisch aus daily_demands_actual (enthält Marketing),
        # anstatt aus statischen production_logs zu lesen. Das stellt sicher, dass Marketing
        # sofort berücksichtigt wird, ohne dass die Simulation neu gestartet werden muss.
        production_by_product = {}
        if 0 <= day < len(results_df):
            actual_build = results_df.iloc[day]['Actual_Build']
            
            # Berechne Produktionsmengen pro Produkt dynamisch (mit Marketing)
            product_demands = {}
            if st.session_state.simulator and hasattr(st.session_state.simulator, 'demand_calculator'):
                demand_calc = st.session_state.simulator.demand_calculator
                
                # WICHTIG: Verwende daily_demands_actual (enthält bereits Marketing)
                # Das ist die Single Source of Truth für Nachfrage mit Marketing
                daily_demands_actual = st.session_state.get('daily_demands_actual', {})
                if day in daily_demands_actual:
                    # Verwende direkt daily_demands_actual (mit Marketing bereits enthalten)
                    product_demands = daily_demands_actual[day]
                else:
                    # Fallback: Berechne Marketing-Add-ons manuell (wie vorher)
                    marketing_add_ons = {}
                    scenario_manager = st.session_state.get('scenario_manager', None)
                    if scenario_manager:
                        marketing_scenarios = scenario_manager.get_marketing_scenarios(day)
                        if marketing_scenarios:
                            month = MasterData.get_month_from_day(day)
                            is_workday = workday_calc.is_workday(day)
                            
                            if is_workday:
                                base_daily_floats = demand_calc._calculate_monthly_base_daily_float(month)
                                
                                for scenario in marketing_scenarios:
                                    factor = scenario.demand_increase_factor
                                    for product in MasterData.BOM.keys():
                                        base_float = base_daily_floats.get(product, 0.0)
                                        add_on = base_float * (factor - 1.0)
                                        if product not in marketing_add_ons:
                                            marketing_add_ons[product] = 0.0
                                        marketing_add_ons[product] += add_on
                    
                    # Prüfe, ob es der letzte Arbeitstag des Jahres ist
                    is_last_workday_of_year = False
                    if workday_calc.is_workday(day):
                        has_future_workdays = False
                        for future_day in range(day + 1, 365):
                            if workday_calc.is_workday(future_day):
                                has_future_workdays = True
                                break
                        is_last_workday_of_year = not has_future_workdays
                    
                    # Berechne Nachfrage pro Produkt (mit Marketing)
                    product_demands = demand_calc.calculate_daily_demand_per_product_dict(
                        day, marketing_add_ons, is_last_workday_of_year
                    )
            else:
                # Fallback: Verwende PRODUCT_SALES_SHARES (alte Logik)
                total_share = sum(MasterData.PRODUCT_SALES_SHARES.values())
                for product in MasterData.BOM.keys():
                    if total_share > 0:
                        share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0) / total_share
                        product_demands[product] = int(actual_build * share) if actual_build > 0 else 0
                    else:
                        product_demands[product] = 0
            
            # Verteile die tatsächliche Produktion proportional zur Nachfrage
            total_demand = sum(product_demands.values())
            
            if total_demand > 0 and actual_build > 0:
                # Sortiere Produkte deterministisch
                sorted_products = sorted(MasterData.BOM.keys())
                remaining_actual = actual_build
                
                for i, product in enumerate(sorted_products):
                    if i == len(sorted_products) - 1:
                        # Letztes Produkt bekommt den Rest wegen Rundungsdifferenzen
                        production_by_product[product] = remaining_actual
                    else:
                        # Proportional verteilen
                        share = product_demands[product] / total_demand
                        allocated = int(actual_build * share)
                        production_by_product[product] = allocated
                        remaining_actual -= allocated
            else:
                for product in MasterData.BOM.keys():
                    production_by_product[product] = 0
        
        # WICHTIG: Verwende dynamisch aktualisierte "tatsächliche PM" aus production_logs
        # statt production_by_product, um Materialverbrauch korrekt zu berechnen
        # Dies stellt sicher, dass der Materialverbrauch mit der tatsächlichen Produktion übereinstimmt
        # (die in pages/6_produktion.py dynamisch aktualisiert wird)
        production_by_product_from_logs = {}
        if 'production_logs_cache' in st.session_state:
            production_logs_cache = st.session_state.production_logs_cache
            for product_name in MasterData.BOM.keys():
                if product_name in production_logs_cache:
                    df = production_logs_cache[product_name]
                    if not df.empty and 'Datum' in df.columns and 'tatsächliche PM' in df.columns:
                        # Suche Zeile für aktuelles Datum
                        current_date_str = current_date.strftime(MasterData.DATE_FORMAT)
                        matching_rows = df[df['Datum'] == current_date_str]
                        if not matching_rows.empty:
                            # Verwende dynamisch aktualisierte "tatsächliche PM"
                            actual_pm = matching_rows.iloc[0].get('tatsächliche PM', 0)
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
        else:
            # Fallback: Verwende production_by_product (alte Logik)
            production_by_product_from_logs = production_by_product
        
        # Jetzt: Für jedes produzierte Produkt den entsprechenden Sattel aus der BOM abziehen
        # Exakte Stücklisten-Logik: 1 Bike = 1 Sattel (gemäß BOM)
        # WICHTIG: Verwende production_by_product_from_logs (dynamisch aktualisiert) statt production_by_product
        for product_name, qty in production_by_product_from_logs.items():
            if qty > 0 and product_name in MasterData.BOM:
                required_saddle = MasterData.BOM[product_name]['saddle']
                # 1 Bike = 1 Sattel (exakte Stücklisten-Logik)
                if required_saddle in issue_by_saddle:
                    issue_by_saddle[required_saddle] += qty

        for s in saddle_types:
            # Morgens = Gestern Abend + Zugang Heute
            stock_morning[s] = stock_by_saddle[s] + receipt_by_saddle.get(s, 0.0)
            
            # KRITISCH: Lagerabgang darf nicht größer sein als Bestand morgens!
            # Wenn kein Bestand vorhanden ist, kann auch nichts ausgegeben werden
            actual_issue = min(issue_by_saddle[s], stock_morning[s])
            
            # Abends = Morgens - Verbrauch
            val = stock_morning[s] - actual_issue
            stock_evening[s] = max(0.0, val)  # Kein negativer Bestand
            
            # Übertrag
            stock_by_saddle[s] = stock_evening[s]
            
            saddle_logs[s].append({
                'Wochentag': weekday_abbr,
                'Datum': current_date.strftime(MasterData.DATE_FORMAT),
                'Lagerzugang': int(round(receipt_by_saddle.get(s, 0.0))) if receipt_by_saddle.get(s, 0.0) > 0 else 0,
                'Bestand morgens': int(round(stock_morning[s])),
                'Lagerabgang': int(round(actual_issue)),  # Begrenzt auf verfügbaren Bestand
                'Verlustmenge': 0,
                'Bestand abends': int(round(stock_evening[s])),
                'Is_Weekend': is_weekend,
                'Is_Holiday': is_holiday
            })
            
        material_inventory_data[current_date] = stock_morning.copy()
    
    st.session_state.material_inventory_data = material_inventory_data
    return {s: pd.DataFrame(l) for s, l in saddle_logs.items()}

# Render - OPTIMIERUNG: Nur berechnen wenn noch nicht im Cache
# WICHTIG: Cache-Key muss Szenarien und volume_planning_cache_key berücksichtigen,
# damit der Cache invalidiert wird wenn Marketing-Szenarien hinzugefügt werden
from ui.volume_planning_utils import calculate_volume_planning_demand
calculate_volume_planning_demand()  # Stelle sicher, dass daily_demands_actual aktualisiert ist

# Erweitere Cache-Key um Szenarien und volume_planning_cache_key
volume_planning_cache_key = st.session_state.get('volume_planning_cache_key', None)
simulation_hash = None
if 'simulator' in st.session_state and st.session_state.simulator:
    # Erstelle Hash aus Simulator-Status (für Cache-Invalidierung)
    try:
        import hashlib
        simulator_state = str(id(st.session_state.simulator)) + str(len(st.session_state.simulator.china_transport_manager.transport_status))
        simulation_hash = hashlib.md5(simulator_state.encode()).hexdigest()
    except:
        simulation_hash = None

# Cache-Key erweitert um volume_planning_cache_key (enthält bereits Szenario-Fingerprint)
cache_key = f"material_inventory_{simulation_hash}_{volume_planning_cache_key}" if simulation_hash else f"material_inventory_default_{volume_planning_cache_key}"

# WICHTIG: Prüfe ob Cache-Key sich geändert hat (z.B. durch Szenario-Deaktivierung)
# Wenn ja, lösche alten Cache
last_cache_key = st.session_state.get('material_inventory_last_cache_key', None)
if last_cache_key is not None and last_cache_key != cache_key:
    # Cache-Key hat sich geändert → lösche alten Cache
    if 'saddle_logs_cache' in st.session_state:
        del st.session_state.saddle_logs_cache
    # Lösche auch alle alten Cache-Keys
    for key in list(st.session_state.keys()):
        if key.startswith('material_inventory_') and key != 'material_inventory_last_cache_key':
            del st.session_state[key]

if cache_key not in st.session_state or 'saddle_logs_cache' not in st.session_state:
    with st.spinner("🔄 Berechne Materiallager..."):
        saddle_logs = create_saddle_inventory_log()
        st.session_state.saddle_logs_cache = saddle_logs
        st.session_state[cache_key] = True
        st.session_state.material_inventory_last_cache_key = cache_key
else:
    # Verwende gecachte Daten
    saddle_logs = st.session_state.saddle_logs_cache

for saddle_type in sorted(saddle_logs.keys()):
    st.subheader(f"📋 {saddle_type}")
    df = saddle_logs[saddle_type]
    # Filtere auf den Standard-Zeitraum (2027)
    mask = (pd.to_datetime(df['Datum'], format='%d.%m.%Y') >= pd.to_datetime(start_date)) & \
           (pd.to_datetime(df['Datum'], format='%d.%m.%Y') <= pd.to_datetime(end_date))
    df_filt = df[mask].copy()
    
    # Styling
    df_filt.reset_index(drop=True, inplace=True)
    weekend_flags = df_filt['Is_Weekend'].values
    holiday_flags = df_filt['Is_Holiday'].values
    
    def style_row_safe(row):
        if row.name < len(weekend_flags):
            if weekend_flags[row.name]:
                return ['background-color: #ffebee'] * len(row)
            if holiday_flags[row.name]:
                return ['background-color: #c8e6c9'] * len(row)
        return [''] * len(row)

    cols = ['Wochentag', 'Datum', 'Lagerzugang', 'Bestand morgens', 'Lagerabgang', 'Verlustmenge', 'Bestand abends']
    df_display = df_filt[cols].copy()
    
    # Identifiziere numerische Spalten für Summenzeile
    numeric_cols = ['Lagerzugang', 'Bestand morgens', 'Lagerabgang', 'Verlustmenge', 'Bestand abends']
    
    # Erstelle Summenzeile
    if numeric_cols and len(df_display) > 0:
        sum_row = {'Wochentag': 'Summe', 'Datum': ''}
        for col in df_display.columns:
            if col in numeric_cols:
                sum_row[col] = int(pd.to_numeric(df_display[col].replace('', 0), errors='coerce').sum())
            elif col not in sum_row:
                sum_row[col] = ''
        
        # Füge Summenzeile als neue Zeile hinzu
        sum_df = pd.DataFrame([sum_row])
        df_display_with_sum = pd.concat([df_display, sum_df], ignore_index=True)
        
        # Erweitere Flags für Summenzeile
        weekend_flags_extended = list(weekend_flags) + [False]
        holiday_flags_extended = list(holiday_flags) + [False]
    else:
        df_display_with_sum = df_display
        weekend_flags_extended = weekend_flags
        holiday_flags_extended = holiday_flags
    
    # Styling-Funktion mit Summenzeile
    def style_row_with_sum(row):
        idx = row.name
        # Summenzeile: grauer Hintergrund, fett
        if idx >= len(weekend_flags):
            return ['background-color: #e0e0e0; font-weight: bold'] * len(row)
        # Normale Zeilen
        if idx < len(weekend_flags_extended):
            if weekend_flags_extended[idx]:
                return ['background-color: #ffebee'] * len(row)
            if holiday_flags_extended[idx]:
                return ['background-color: #c8e6c9'] * len(row)
        return [''] * len(row)
    
    # Farblegende
    col1, col2 = st.columns([1, 1])
    with col2:
        st.markdown("""
        <div style="text-align: right; margin-bottom: 10px;">
            <span style="background-color: #ffebee; padding: 2px 8px; border-radius: 3px; margin-left: 5px;">Wochenende</span>
            <span style="background-color: #c8e6c9; padding: 2px 8px; border-radius: 3px; margin-left: 5px;">Feiertag</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.dataframe(df_display_with_sum.style.apply(style_row_with_sum, axis=1), width='stretch', hide_index=True)
    st.divider()
