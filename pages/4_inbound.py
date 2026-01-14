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

# CSS für Menü-Formatierung (Großbuchstaben und Fett)
st.markdown("""
<style>
    /* Menüeinträge großgeschrieben und fett */
    [data-testid="stSidebarNav"] a {
        font-weight: bold !important;
        text-transform: capitalize !important;
    }
</style>
""", unsafe_allow_html=True)

# Szenarien-Sidebar rendern
render_scenario_sidebar()

st.title("🚢 Inbound Logistik")
st.markdown("Überwachung der Verschiffungen und Zuläufe zum Lager Dortmund.")

# Initialisiere Session State
initialize_session_state()

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
    # Zeige Tabelle mit Styling (Wochenenden hervorheben)
    def style_row(row):
        styles = [''] * len(row)
        weekday = row['Wochentag']
        # Wochenende: Sa oder So
        if weekday in ['Sa', 'So']:
            return ['background-color: #ffebee' for _ in row]
        return styles
    
    styled_df = df.style.apply(style_row, axis=1)
    st.dataframe(styled_df, width='stretch', hide_index=True, height=800)
else:
    st.info("Keine Inbound-Daten vorhanden.")
