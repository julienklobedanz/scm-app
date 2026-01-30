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
        background-color: #404040 !important;
        z-index: 100 !important;
    }
    .stDataFrame [data-testid="stDataFrame"] table tbody tr:last-child td {
        background-color: #404040 !important;
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

# WICHTIG: production_logs_cache sollte bereits beim App-Start initialisiert worden sein
# (durch initialize_all_page_calculations() in app.py)
# Falls nicht, versuche es jetzt zu initialisieren (Fallback für direkten Seitenaufruf)
if 'production_logs_cache' not in st.session_state:
    from ui.production_calculations import calculate_production_logs
    try:
        calculate_production_logs()
    except Exception:
        pass  # Wird beim Laden der Seite behandelt

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
    """
    Erstellt Sattel-Lager-Log synchronisiert mit Inbound-Daten.
    Wrapper-Funktion, die die Berechnungslogik aus ui.material_calculations verwendet.
    """
    from ui.material_calculations import calculate_material_inventory
    material_inventory_data, saddle_logs = calculate_material_inventory()
    return {s: pd.DataFrame(l) for s, l in saddle_logs.items()}

# Alte Implementierung entfernt - wird jetzt in ui.material_calculations.py verwendet

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
    # Prüfe ob DataFrame leer ist oder 'Datum' Spalte fehlt
    if df.empty or 'Datum' not in df.columns:
        st.info(f"Keine Daten für {saddle_type} verfügbar.")
        continue
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
                return ['background-color: #4a2525'] * len(row)
            if holiday_flags[row.name]:
                return ['background-color: #1e3d2a'] * len(row)
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
            return ['background-color: #404040; font-weight: bold'] * len(row)
        # Normale Zeilen
        if idx < len(weekend_flags_extended):
            if weekend_flags_extended[idx]:
                return ['background-color: #4a2525'] * len(row)
            if holiday_flags_extended[idx]:
                return ['background-color: #1e3d2a'] * len(row)
        return [''] * len(row)
    
    # Farblegende
    col1, col2 = st.columns([1, 1])
    with col2:
        st.markdown("""
        <div style="text-align: right; margin-bottom: 10px;">
            <span style="background-color: #4a2525; padding: 2px 8px; border-radius: 3px; margin-left: 5px;">Wochenende</span>
            <span style="background-color: #1e3d2a; padding: 2px 8px; border-radius: 3px; margin-left: 5px;">Feiertag</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.dataframe(df_display_with_sum.style.apply(style_row_with_sum, axis=1), width='stretch', hide_index=True)
    st.divider()
