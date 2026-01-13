"""
UI Utility Functions
Zentrale Hilfsfunktionen für Streamlit-Seiten
"""

import streamlit as st
from simulation.simulator import Simulator
from models.scenarios import ScenarioManager
from config.master_data import MasterData


def initialize_session_state():
    """Initialisiert alle Session State Variablen mit Standardwerten"""
    if 'scenario_manager' not in st.session_state:
        st.session_state.scenario_manager = ScenarioManager()
    if 'results_df' not in st.session_state:
        st.session_state.results_df = None
    if 'kpis' not in st.session_state:
        st.session_state.kpis = None
    if 'simulator' not in st.session_state:
        st.session_state.simulator = None
    if 'happy_path_run' not in st.session_state:
        st.session_state.happy_path_run = False
    if 'yearly_volume' not in st.session_state:
        st.session_state.yearly_volume = 370000


def create_simulator(scenario_manager=None):
    """
    Erstellt eine Simulator-Instanz mit Standard-Parametern
    
    Args:
        scenario_manager: Optional ScenarioManager, falls None wird aus session_state genommen
    
    Returns:
        Simulator-Instanz
    """
    if scenario_manager is None:
        scenario_manager = st.session_state.get('scenario_manager', ScenarioManager())
    
    vol = st.session_state.get('yearly_volume', 370000)
    return Simulator(
        yearly_volume=vol,
        initial_stock_frames_alu=MasterData.DEFAULT_INITIAL_STOCK['frames_alu'],
        initial_stock_frames_carbon=MasterData.DEFAULT_INITIAL_STOCK['frames_carbon'],
        initial_stock_saddles=MasterData.DEFAULT_INITIAL_STOCK['saddles'],
        scenario_manager=scenario_manager
    )


def run_happy_path_simulation():
    """
    Führt die Happy Path Simulation aus, wenn noch keine Ergebnisse vorhanden sind.
    Wird automatisch beim ersten Laden einer Seite aufgerufen.
    """
    if not st.session_state.happy_path_run and st.session_state.results_df is None:
        try:
            with st.spinner("🔄 Happy Path Simulation wird ausgeführt..."):
                simulator = create_simulator()
                results_df, kpis = simulator.run()
                st.session_state.results_df = results_df
                st.session_state.kpis = kpis
                st.session_state.simulator = simulator
                st.session_state.happy_path_run = True
                st.rerun()
        except Exception as e:
            st.error(f"❌ Fehler bei der Simulation: {str(e)}")
            st.exception(e)
            st.session_state.happy_path_run = True  # Verhindere Endlosschleife


def ensure_simulator_available():
    """
    Prüft ob Simulator verfügbar ist, zeigt Warning und stoppt falls nicht.
    """
    if 'simulator' not in st.session_state or st.session_state.simulator is None:
        st.warning("⚠️ Bitte führen Sie zuerst die Simulation auf dem Dashboard aus.")
        st.stop()
