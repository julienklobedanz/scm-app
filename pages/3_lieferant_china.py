"""
Lieferant China-Seite
Zeigt Produktion und Transport zum Hafen Dengwong - je Sattel-Typ eine Tabelle
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

st.set_page_config(page_title="Lieferant China", page_icon="🇨🇳", layout="wide")

# Szenarien-Sidebar rendern
render_scenario_sidebar()

st.title("🇨🇳 Lieferant China (Produktion & Vorlauf)")
st.markdown("Überwachung der Produktion und des Transports zum Hafen Dengwong - je Sattel-Typ eine Tabelle.")

# Initialisiere Session State
initialize_session_state()

# Happy Path: Automatische Simulation wenn noch keine Ergebnisse vorhanden
run_happy_path_simulation()

# Prüfe ob Simulator verfügbar ist
ensure_simulator_available()

manager = st.session_state.simulator.china_transport_manager
workday_calc = manager.workday_calculator
demand_calculator = st.session_state.simulator.demand_calculator

# Berechne Sattel-Shares (konsistent mit anderen Seiten)
saddle_shares = MasterData.calculate_saddle_shares()
all_saddle_types = sorted(list(saddle_shares.keys()))

# Tabellen für jeden Sattel-Typ anzeigen
for saddle_type in all_saddle_types:
    st.subheader(f"📦 {saddle_type}")
    
    # Rufe die neue Methode aus dem ChinaTransportManager auf
    # Übergebe demand_calculator für korrekte Bestelleingang-Berechnung
    df = manager.get_supplier_log_dataframe(saddle_type, saddle_shares[saddle_type], demand_calculator)
    
    if not df.empty:
        # Spaltenreihenfolge sicherstellen
        column_order = [
            'Wochentag', 'Datum', 'Bestelleingang', 'Freigabedatum', 
            'Freigegebene Bestellungen', 'Störung', 'Produktionsdatum', 
            'Produktionsmenge', 'Warenausgang', 'Warenbestand'
        ]
        
        # Stelle sicher, dass alle Spalten vorhanden sind
        for col in column_order:
            if col not in df.columns:
                df[col] = ''
        
        df_display = df[column_order].copy()
        
        # Zeige Tabelle mit Styling (Wochenenden hervorheben)
        def style_row(row):
            styles = [''] * len(row)
            weekday = row['Wochentag']
            # Wochenende: Sa oder So
            if weekday in ['Sa', 'So']:
                return ['background-color: #ffebee' for _ in row]
            return styles
        
        styled_df = df_display.style.apply(style_row, axis=1)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.info(f"Keine Daten für {saddle_type} vorhanden.")
    
    st.divider()
