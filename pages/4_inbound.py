"""
Inbound Logistik-Seite
Zeigt Ware, die das chinesische Festland verlassen hat und auf dem Weg zum Lager Dortmund ist
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from typing import Dict, Tuple
from config.master_data import MasterData
from config.holidays_config import HolidaysConfig
from simulation.simulator import Simulator
from models.scenarios import ScenarioManager
from simulation.workday_calculator import WorkdayCalculator
from simulation.demand_calculator import DemandCalculator
from ui.scenario_sidebar import render_scenario_sidebar
from ui.utils import initialize_session_state, run_happy_path_simulation, ensure_simulator_available

st.set_page_config(page_title="Inbound", page_icon="🚢", layout="wide")

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

# Szenarien-Sidebar rendern
render_scenario_sidebar(key_suffix="_inbound")

st.title("🚢 Inbound Logistik")
st.markdown("Überwachung der Verschiffungen und Zuläufe zum Lager Dortmund.")

# Initialisiere Session State
initialize_session_state()

# WICHTIG: Stelle sicher, dass daily_demands_actual aktualisiert wird, wenn sich Szenarien ändern
# Dies ist notwendig, damit die Inbound-Tabelle korrekt aktualisiert wird
from ui.volume_planning_utils import calculate_volume_planning_demand
calculate_volume_planning_demand()

# Happy Path: Automatische Simulation wenn noch keine Ergebnisse vorhanden
run_happy_path_simulation()

# Prüfe ob Simulator verfügbar ist
ensure_simulator_available()

manager = st.session_state.simulator.china_transport_manager
workday_calc = manager.workday_calculator

# Berechne Sattel-Shares (konsistent mit anderen Seiten)
saddle_shares = MasterData.calculate_saddle_shares()
        
# Rufe die neue Methode aus dem ChinaTransportManager auf
df = manager.get_inbound_log_dataframe(saddle_shares)

if not df.empty:
    # Speichere Flags für Wochenende und Feiertage
    weekend_flags = df['Is_Weekend'].values if 'Is_Weekend' in df.columns else [False] * len(df)
    holiday_flags = df['Is_Holiday'].values if 'Is_Holiday' in df.columns else [False] * len(df)
    
    # Summenzeile hinzufügen
    numeric_cols = ['Menge Gesamt'] + [col for col in df.columns if col in saddle_shares.keys()]
    sum_row = {'Wochentag': 'Summe', 'Datum': ''}
    for col in df.columns:
        if col in numeric_cols:
            # Nur summieren, wenn die Spalte numerische Werte enthält
            try:
                # Konvertiere zu numerisch, ignoriere nicht-numerische Werte
                numeric_values = pd.to_numeric(df[col], errors='coerce')
                sum_row[col] = int(numeric_values.sum()) if not numeric_values.isna().all() else 0
            except (ValueError, TypeError):
                sum_row[col] = 0
        elif col not in ['Wochentag', 'Datum', 'Verspätung', 'Ladungsverlust', 'Abfahrt LKW 🇨🇳', 'Ankunft LKW 🇨🇳', 
                         'Abfahrt Schiff 🇨🇳', 'Ankunft Schiff 🇩🇪', 'Abfahrt LKW 🇩🇪', 
                         'Geplante Ankunft LKW 🇩🇪', 'Tatsächliche Ankunft LKW 🇩🇪']:
            sum_row[col] = ''
        else:
            sum_row[col] = ''
    
    df_with_sum = pd.concat([df, pd.DataFrame([sum_row])], ignore_index=True)
    
    # Erweitere Flags für Summenzeile
    weekend_flags_extended = list(weekend_flags) + [False]
    holiday_flags_extended = list(holiday_flags) + [False]
    
    # Entferne Flags aus Anzeige (werden nur für Styling verwendet)
    if 'Is_Weekend' in df.columns:
        df = df.drop(columns=['Is_Weekend'])
    if 'Is_Holiday' in df.columns:
        df = df.drop(columns=['Is_Holiday'])
    
    # Styling-Funktion für Summenzeile
    def style_row_with_sum(row):
        row_idx = row.name
        if row_idx < len(weekend_flags):
            # Wochenende hat Priorität (wenn beides, dann Wochenende = rot)
            if weekend_flags_extended[row_idx]:
                return ['background-color: #ffebee' for _ in row]
            elif holiday_flags_extended[row_idx]:
                return ['background-color: #c8e6c9' for _ in row]
        elif row_idx >= len(weekend_flags):
            # Summenzeile
            return ['background-color: #e0e0e0; font-weight: bold' for _ in row]
        return [''] * len(row)
    
    styled_df = df_with_sum.style.apply(style_row_with_sum, axis=1)
    st.dataframe(styled_df, width='stretch', hide_index=True, height=800)
else:
    st.info("Keine Inbound-Daten vorhanden.")
