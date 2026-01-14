"""
Produktion - Seite
Zeigt Produktionsplanung, tatsächliche Produktion und Materialverfügbarkeit
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
from config.master_data import MasterData
from simulation.simulator import Simulator
from models.scenarios import ScenarioManager
from simulation.workday_calculator import WorkdayCalculator
from ui.scenario_sidebar import render_scenario_sidebar
from ui.utils import initialize_session_state, run_happy_path_simulation

st.set_page_config(page_title="Produktion", layout="wide", page_icon="🏭")

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

# Initialisiere Session State
initialize_session_state()

st.title("🏭 Produktion")
st.markdown("Übersicht über Produktionsplanung, tatsächliche Produktion und Materialverfügbarkeit")

# Happy Path: Automatische Simulation wenn noch keine Ergebnisse vorhanden
run_happy_path_simulation()

if st.session_state.results_df is None:
    st.warning("⚠️ Keine Simulationsergebnisse verfügbar.")
    st.stop()

results_df = st.session_state.results_df

# Zeitraum
start_date = date(2026, 1, 1)
end_date = date(2026, 12, 31)
workday_calc = WorkdayCalculator(year=2026)

# NEU: Lese Produktionslogs direkt aus dem ProductionPlanner
def get_production_logs():
    """Liest Produktionslogs direkt aus dem ProductionPlanner (Single Source of Truth)"""
    if 'simulator' not in st.session_state or st.session_state.simulator is None:
        st.error("⚠️ Simulator nicht verfügbar. Bitte führen Sie zuerst die Simulation aus.")
        return {}
    
    planner = st.session_state.simulator.production_planner
    
    if not hasattr(planner, 'production_logs') or not planner.production_logs:
        st.warning("⚠️ Keine Produktionslogs verfügbar. Bitte führen Sie die Simulation erneut aus.")
        return {}
    
    # Konvertiere Logs zu DataFrames
    production_logs = {}
    for product, logs in planner.production_logs.items():
        if logs:
            production_logs[product] = pd.DataFrame(logs)
        else:
            production_logs[product] = pd.DataFrame()
    
    return production_logs

# Erstelle Produktions-Log
with st.spinner("🔄 Lade Produktionsdaten..."):
    production_logs = get_production_logs()

if not production_logs:
    st.warning("⚠️ Keine Produktionsdaten verfügbar.")
    st.stop()

# Zeige Tabelle für jedes Produkt
for product in sorted(production_logs.keys()):
    st.subheader(f"📋 {product}")
    
    df_prod = production_logs[product]
    
    if df_prod.empty:
        st.info(f"Keine Daten für {product} verfügbar.")
        continue
    
    # Filtere auf den Standard-Zeitraum (2026)
    df_prod_filtered = df_prod[
        (pd.to_datetime(df_prod['Datum'], format='%d.%m.%Y') >= pd.to_datetime(start_date)) &
        (pd.to_datetime(df_prod['Datum'], format='%d.%m.%Y') <= pd.to_datetime(end_date))
    ]
    
    if df_prod_filtered.empty:
        st.info(f"Keine Daten für {product} im ausgewählten Zeitraum.")
        continue
    
    # Speichere Flags für Wochenende und Feiertage
    weekend_flags = df_prod_filtered['Is_Weekend'].values
    holiday_flags = df_prod_filtered['Is_Holiday'].values
    
    # Hole konkrete Einzelteil-Namen für dieses Produkt
    frame_name = MasterData.BOM[product]['frame']
    saddle_name = MasterData.BOM[product]['saddle']
    fork_name = MasterData.BOM[product]['fork']
    
    # Definiere Spaltenreihenfolge (Wochentag vor Datum)
    # Einzelteile direkt nach "Auslastung (%)"
    # Hinweis: "Produktionsbedarf" und "Rang" sind nur Hilfsberechnungen
    # und werden nicht angezeigt (Spalten beginnen mit "_")
    column_order = [
        'Wochentag',
        'Datum',
        'Schichtanzahl',
        'Auslastung (%)',
        frame_name,  # Konkreter Rahmen-Name
        saddle_name,  # Konkreter Sattel-Name
        fork_name,  # Konkrete Gabel-Name
        'Materialien vollständig?',
        'geplante PM',
        'tatsächliche PM',
        'fertiggestellte PM',
        'Backlog'
    ]
    
    # Prüfe, ob alle Spalten vorhanden sind
    available_columns = [col for col in column_order if col in df_prod_filtered.columns]
    df_display = df_prod_filtered[available_columns].copy()
    
    # Farblegende oben rechts
    col1, col2 = st.columns([1, 1])
    with col2:
        st.markdown("""
        <div style="text-align: right; margin-bottom: 10px;">
            <span style="background-color: #ffebee; padding: 2px 8px; border-radius: 3px; margin-left: 5px;">Wochenende</span>
            <span style="background-color: #c8e6c9; padding: 2px 8px; border-radius: 3px; margin-left: 5px;">Feiertag</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Styling-Funktion
    def style_row_safe(row):
        idx = row.name
        if idx < len(weekend_flags):
            if weekend_flags[idx]:
                return ['background-color: #ffebee'] * len(row)
            if holiday_flags[idx]:
                return ['background-color: #c8e6c9'] * len(row)
        return [''] * len(row)
    
    # Zeige Tabelle
    st.dataframe(
        df_display.style.apply(style_row_safe, axis=1),
        width='stretch',
        hide_index=True
    )
    
    st.divider()
