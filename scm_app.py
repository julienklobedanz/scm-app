"""
SCM App - Supply Chain Simulation
Hauptseite mit Dashboard und Szenarien-Management
"""

import streamlit as st
import pandas as pd
from datetime import date
from simulation.simulator import Simulator
from models.scenarios import (
    ScenarioManager,
    StandardScenario
)
from config.master_data import MasterData
from ui.charts import (
    render_kpis,
    render_inventory_chart,
    render_backlog_chart_de,
    render_backlog_chart_all,
    render_production_chart
)
from ui.scenario_sidebar import render_scenario_sidebar

st.set_page_config(page_title="SCM App", layout="wide", page_icon="📊")

# Initialisiere Session State (MUSS ZUERST PASSIEREN)
if 'scenario_manager' not in st.session_state:
    st.session_state.scenario_manager = ScenarioManager()
if 'results_df' not in st.session_state:
    st.session_state.results_df = None
if 'kpis' not in st.session_state:
    st.session_state.kpis = None
if 'happy_path_run' not in st.session_state:
    st.session_state.happy_path_run = False
if 'yearly_volume' not in st.session_state:
    st.session_state.yearly_volume = 370000

st.title("📊 Dashboard")
st.markdown("Übersicht der wichtigsten KPIs und Szenarien-Management")

# Szenarien-Sidebar rendern
render_scenario_sidebar()

# Happy Path: Automatische Simulation beim ersten Laden
if not st.session_state.happy_path_run and st.session_state.results_df is None:
    # Führe Simulation sofort aus (blockierend)
    try:
        # Verwende yearly_volume aus session_state (wird vom Widget gesetzt)
        vol = st.session_state.get('yearly_volume', 370000)
        simulator = Simulator(
            yearly_volume=vol,
            initial_stock_frames_alu=MasterData.DEFAULT_INITIAL_STOCK['frames_alu'],
            initial_stock_frames_carbon=MasterData.DEFAULT_INITIAL_STOCK['frames_carbon'],
            initial_stock_saddles=MasterData.DEFAULT_INITIAL_STOCK['saddles'],
            scenario_manager=st.session_state.scenario_manager
        )
            results_df, kpis = simulator.run()
            st.session_state.results_df = results_df
            st.session_state.kpis = kpis
            # Speichere auch den Simulator für Zugriff auf ChinaTransportManager
            st.session_state.simulator = simulator
            st.session_state.happy_path_run = True
    except Exception as e:
        st.error(f"❌ Fehler bei der Simulation: {str(e)}")
        st.exception(e)
        st.session_state.happy_path_run = True  # Verhindere Endlosschleife

# Simulation ausführen (für manuellen Neustart)
if st.session_state.get('run_simulation', False) and st.session_state.happy_path_run:
    try:
        with st.spinner("Simulation läuft..."):
            # Verwende yearly_volume aus session_state (wird vom Widget gesetzt)
            vol = st.session_state.get('yearly_volume', 370000)
            simulator = Simulator(
                yearly_volume=vol,
                initial_stock_frames_alu=MasterData.DEFAULT_INITIAL_STOCK['frames_alu'],
                initial_stock_frames_carbon=MasterData.DEFAULT_INITIAL_STOCK['frames_carbon'],
                initial_stock_saddles=MasterData.DEFAULT_INITIAL_STOCK['saddles'],
                scenario_manager=st.session_state.scenario_manager
            )
                results_df, kpis = simulator.run()
                st.session_state.results_df = results_df
                st.session_state.kpis = kpis
                # Speichere auch den Simulator für Zugriff auf ChinaTransportManager
                st.session_state.simulator = simulator
                st.session_state.run_simulation = False
                st.success("✅ Simulation erfolgreich abgeschlossen!")
                st.rerun()
    except Exception as e:
        st.error(f"❌ Fehler bei der Simulation: {str(e)}")
        st.exception(e)
        st.session_state.run_simulation = False

# Ergebnisse anzeigen
if st.session_state.results_df is not None:
    results_df = st.session_state.results_df
    kpis = st.session_state.kpis

    # KPIs
    render_kpis(kpis)

    # Charts
    st.header("📈 Charts")

    # Inventory Levels
    st.subheader("Lagerbestände (Rahmen vs. Sättel)")
    render_inventory_chart(results_df)

    # Backlog Development (DE)
    render_backlog_chart_de(results_df)

    # Backlog alle Märkte
    render_backlog_chart_all(results_df)

    # Produktion vs. Ziel
    render_production_chart(results_df)

else:
    # Zeige Ladeanzeige während der ersten Simulation
    st.info("🔄 Die Simulation wird automatisch gestartet...")

