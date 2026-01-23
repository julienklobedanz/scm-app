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
render_scenario_sidebar(key_suffix="_lieferant_china")

st.title("🇨🇳 Lieferant China (Produktion & Vorlauf)")
st.markdown("Überwachung der Produktion und des Transports zum Hafen Dengwong - je Sattel-Typ eine Tabelle.")

# Initialisiere Session State
initialize_session_state()

# WICHTIG: Stelle sicher, dass daily_demands_actual aktualisiert wird, wenn sich Szenarien ändern
# Dies ist notwendig, damit der Bestelleingang in der Tabelle korrekt aktualisiert wird
from ui.volume_planning_utils import calculate_volume_planning_demand
calculate_volume_planning_demand()

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
    df = manager.get_supplier_log_dataframe(saddle_type, saddle_shares[saddle_type])
    
    if not df.empty:
        # Speichere Flags für Wochenende und Feiertage (VOR dem Entfernen)
        weekend_flags = df['Is_Weekend'].values if 'Is_Weekend' in df.columns else [False] * len(df)
        holiday_flags = df['Is_Holiday'].values if 'Is_Holiday' in df.columns else [False] * len(df)
        
        # Spaltenreihenfolge sicherstellen (Flags nicht anzeigen)
        column_order = [
            'Wochentag', 'Datum', 'Bestelleingang', 'Freigabedatum', 
            'Freigegebene Bestellungen', 'Störung', 'Produktionsdatum', 
            'Produktionsmenge', 'Warenausgang', 'Warenbestand'
        ]
        # Entferne Flags aus Anzeige (werden nur für Styling verwendet)
        if 'Is_Weekend' in df.columns:
            df = df.drop(columns=['Is_Weekend'])
        if 'Is_Holiday' in df.columns:
            df = df.drop(columns=['Is_Holiday'])
        
        # Stelle sicher, dass alle Spalten vorhanden sind
        for col in column_order:
            if col not in df.columns:
                df[col] = ''
        
        df_display = df[column_order].copy()
        
        # Farblegende oben rechts
        col1, col2 = st.columns([1, 1])
        with col2:
            st.markdown("""
            <div style="text-align: right; margin-bottom: 10px;">
                <span style="background-color: #ffebee; padding: 2px 8px; border-radius: 3px; margin-left: 5px;">Wochenende</span>
                <span style="background-color: #c8e6c9; padding: 2px 8px; border-radius: 3px; margin-left: 5px;">Feiertag</span>
            </div>
            """, unsafe_allow_html=True)
        
        # Zeige Tabelle mit Styling (Wochenenden und Feiertage hervorheben)
        def style_row(row):
            idx = row.name
            if idx < len(weekend_flags):
                # Wochenende hat Priorität (wenn beides, dann Wochenende = rot)
                if weekend_flags[idx]:
                    return ['background-color: #ffebee' for _ in row]
                elif holiday_flags[idx]:
                    return ['background-color: #c8e6c9' for _ in row]
            return [''] * len(row)
        
        # Summenzeile hinzufügen
        # Bestelleingang: Konvertiere leere Strings zu 0, dann summiere
        bestelleingang_sum = 0
        if 'Bestelleingang' in df_display.columns:
            try:
                bestelleingang_series = df_display['Bestelleingang'].replace('', 0)
                bestelleingang_series = pd.to_numeric(bestelleingang_series, errors='coerce').fillna(0)
                bestelleingang_sum = int(bestelleingang_series.sum())
            except (ValueError, TypeError):
                bestelleingang_sum = 0
        
        sum_row = {
            'Wochentag': 'Summe',
            'Datum': '',
            'Bestelleingang': bestelleingang_sum,
            'Freigabedatum': '',
            'Freigegebene Bestellungen': int(pd.to_numeric(df_display['Freigegebene Bestellungen'], errors='coerce').fillna(0).sum()) if 'Freigegebene Bestellungen' in df_display.columns else 0,
            'Störung': '',
            'Produktionsdatum': '',
            'Produktionsmenge': int(pd.to_numeric(df_display['Produktionsmenge'], errors='coerce').fillna(0).sum()) if 'Produktionsmenge' in df_display.columns else 0,
            'Warenausgang': int(pd.to_numeric(df_display['Warenausgang'], errors='coerce').fillna(0).sum()) if 'Warenausgang' in df_display.columns else 0,
            'Warenbestand': int(pd.to_numeric(df_display['Warenbestand'], errors='coerce').fillna(0).iloc[-1]) if len(df_display) > 0 and 'Warenbestand' in df_display.columns else 0
        }
        df_with_sum = pd.concat([df_display, pd.DataFrame([sum_row])], ignore_index=True)
        
        # Styling-Funktion für Summenzeile
        def style_row_with_sum(row):
            row_idx = row.name
            if row_idx < len(df_display):
                return style_row(row)
            else:
                return ['background-color: #e0e0e0; font-weight: bold' for _ in row]
        
        styled_df = df_with_sum.style.apply(style_row_with_sum, axis=1)
        st.dataframe(styled_df, width='stretch', hide_index=True)
    else:
        st.info(f"Keine Daten für {saddle_type} vorhanden.")
    
    st.divider()
