"""
UI Utility Functions
Zentrale Hilfsfunktionen für Streamlit-Seiten
"""

import streamlit as st
import time
from simulation.simulator import Simulator
from models.scenarios import ScenarioManager
from config.master_data import MasterData
from ui.volume_planning_utils import calculate_volume_planning_demand


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
        # FIX: Synchronisiere yearly_volume mit total_volume aus GLOBAL_CONFIG
        st.session_state.yearly_volume = MasterData.GLOBAL_CONFIG.get('total_volume', 370000)
    if 'simulation_running' not in st.session_state:
        st.session_state.simulation_running = False
    if 'simulation_started' not in st.session_state:
        st.session_state.simulation_started = False
    if 'volume_planning_calculated' not in st.session_state:
        st.session_state.volume_planning_calculated = False
    if 'last_progress_update' not in st.session_state:
        st.session_state.last_progress_update = 0
    if 'planning_year' not in st.session_state:
        st.session_state.planning_year = 2027  # Standard-Jahr
    if 'simulation_cache' not in st.session_state:
        st.session_state.simulation_cache = {}  # Cache für Simulationen pro Jahr: {year: {'results_df': ..., 'kpis': ..., 'simulator': ...}}


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
    Führt die Happy Path Simulation aus.
    
    WICHTIG: Berechnungen werden nur durchgeführt, wenn PRODUCT_SALES_SHARES und SEASONALITY jeweils 100% ergeben.
    """
    # KRITISCH: Validiere Parameter bevor Berechnungen erfolgen
    from ui.volume_planning_utils import _validate_parameters
    is_valid, error_message = _validate_parameters()
    if not is_valid:
        # Simulator wird nicht erstellt wenn Parameter ungültig sind
        return
    """
    Führt die Happy Path Simulation aus, wenn noch keine Ergebnisse vorhanden sind.
    Wird automatisch beim ersten Laden einer Seite aufgerufen.
    
    WICHTIG: Diese Funktion prüft mehrfach, ob die Simulation bereits läuft oder abgeschlossen ist,
    um sicherzustellen, dass sie nicht mehrfach ausgeführt wird.
    
    WICHTIG: Die Simulation wird synchron ausgeführt, aber mit einem Progress-Indikator.
    """
    # WICHTIG: Prüfe Cache für das aktuelle Jahr
    planning_year = st.session_state.get('planning_year', 2027)
    simulation_cache = st.session_state.get('simulation_cache', {})
    
    # Prüfe ob Simulation für das aktuelle Jahr bereits im Cache ist
    if planning_year in simulation_cache:
        cached_data = simulation_cache[planning_year]
        if cached_data.get('results_df') is not None:
            # Lade aus Cache
            st.session_state.results_df = cached_data['results_df']
            st.session_state.kpis = cached_data.get('kpis')
            st.session_state.simulator = cached_data.get('simulator')
            st.session_state.happy_path_run = True
            st.session_state.simulation_running = False
            st.session_state.simulation_started = False
            return
    
    # Fallback: Prüfe ob Simulation bereits abgeschlossen ist (für Kompatibilität)
    if st.session_state.get('happy_path_run', False) and st.session_state.get('results_df') is not None:
        # Prüfe ob das Jahr übereinstimmt
        cached_year = st.session_state.get('simulation_year', None)
        if cached_year == planning_year:
            return
        # Jahr stimmt nicht überein - Simulation muss neu berechnet werden
        st.session_state.happy_path_run = False
        st.session_state.results_df = None
    
    # Prüfe ob Simulation bereits läuft (verhindert parallele Ausführung)
    if st.session_state.get('simulation_running', False):
        # Zeige Progress-Indikator während Simulation läuft
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        
        # Schätze Fortschritt basierend auf verstrichener Zeit
        start_time = st.session_state.get('simulation_start_time', time.time())
        elapsed = time.time() - start_time
        # WICHTIG: Kein fester Timeout mehr - Simulation darf so lange laufen wie nötig
        # Progress wird basierend auf verstrichener Zeit angezeigt (max. 95% bis fertig)
        estimated_total = max(60, elapsed + 10)  # Dynamisch: mindestens 60s, sonst elapsed + 10s
        progress = min(elapsed / estimated_total, 0.95)  # Max 95%, bis Simulation wirklich fertig ist
        
        progress_placeholder.progress(progress, text=f"Simulation läuft... ({int(elapsed)}s)")
        status_placeholder.info("🔄 Die Simulation wird ausgeführt. Bitte warten Sie...")
        
        # KRITISCH: KEIN st.rerun() hier - das würde eine Endlosschleife verursachen!
        # Die Simulation läuft bereits im Hintergrund und wird automatisch die Flags zurücksetzen,
        # wenn sie fertig ist. Ein st.rerun() würde nur die Seite neu laden, während die Simulation
        # noch läuft, was zu einer Endlosschleife führt.
        # Stattdessen: Verwende st.stop() um die Seite zu stoppen, bis die Simulation fertig ist.
        st.stop()
        return
    
    # Prüfe ob Simulation bereits gestartet wurde (aber noch nicht abgeschlossen)
    if st.session_state.get('simulation_started', False):
        # Warte auf Abschluss (wird durch st.rerun() getriggert)
        return
    
    # Starte Simulation nur wenn alle Bedingungen erfüllt sind
    # WICHTIG: Prüfe auch, ob das Jahr übereinstimmt (Cache ist jahr-spezifisch)
    cached_year = st.session_state.get('simulation_year', None)
    if (not st.session_state.get('happy_path_run', False) or cached_year != planning_year) and st.session_state.get('results_df') is None:
        try:
            # WICHTIG: Berechne Volumenplanung VOR der Simulation
            # Die Volumenplanung ist die Basis, der Simulator verwendet diese Daten
            # OPTIMIERUNG: Prüfe auch, ob das Jahr übereinstimmt (Cache ist jahr-spezifisch)
            planning_year = st.session_state.get('planning_year', 2027)
            cached_year = st.session_state.get('volume_planning_year', None)
            
            if (not st.session_state.get('volume_planning_calculated', False) or 
                cached_year != planning_year):
                calculate_volume_planning_demand()
            
            # Markiere Simulation als gestartet und laufend
            st.session_state.simulation_started = True
            st.session_state.simulation_running = True
            st.session_state.simulation_start_time = time.time()
            
            # Zeige Progress-Indikator
            progress_placeholder = st.empty()
            status_placeholder = st.empty()
            
            # Initiale Anzeige
            progress_placeholder.progress(0.0, text="Simulation wird gestartet...")
            status_placeholder.info("🔄 Die Simulation wird ausgeführt. Dies sollte max. 60 Sekunden dauern...")
            
            # Führe Simulation aus (mit Timeout-Schutz)
            # WICHTIG: Kein Timeout mehr - Simulation darf so lange laufen wie nötig
            try:
                # Update Progress während Initialisierung
                progress_placeholder.progress(0.1, text="Simulator wird initialisiert...")
                simulator = create_simulator()
                
                # Update Progress während Simulation
                progress_placeholder.progress(0.3, text="Simulation läuft...")
                results_df, kpis = simulator.run()
                
                # Speichere Ergebnisse im Session State
                st.session_state.results_df = results_df
                st.session_state.kpis = kpis
                st.session_state.simulator = simulator
                st.session_state.happy_path_run = True
                st.session_state.simulation_running = False
                st.session_state.simulation_started = False
                st.session_state.simulation_year = planning_year  # Speichere Jahr für Cache-Validierung
                
                # WICHTIG: Speichere auch im Cache für das Jahr
                if 'simulation_cache' not in st.session_state:
                    st.session_state.simulation_cache = {}
                st.session_state.simulation_cache[planning_year] = {
                    'results_df': results_df,
                    'kpis': kpis,
                    'simulator': simulator
                }
                
                # Entferne Progress-Indikator
                progress_placeholder.empty()
                status_placeholder.empty()
                
                # WICHTIG: Nur einmal rerun() am Ende, nicht während der Simulation
                st.rerun()
            except Exception as sim_error:
                # Bei Fehler: Setze Flags zurück
                st.session_state.simulation_running = False
                st.session_state.simulation_started = False
                progress_placeholder.empty()
                status_placeholder.empty()
                raise  # Re-raise für die äußere Exception-Behandlung
        except Exception as e:
            st.error(f"❌ Fehler bei der Simulation: {str(e)}")
            st.exception(e)
            st.session_state.happy_path_run = True  # Verhindere Endlosschleife
            st.session_state.simulation_running = False
            st.session_state.simulation_started = False


def ensure_simulator_available():
    """
    Prüft ob Simulator verfügbar ist.
    Wenn die Simulation gerade läuft, zeigt eine Meldung und wartet.
    Wenn die Simulation nicht läuft und kein Simulator verfügbar ist, zeigt eine Warnung und stoppt.
    """
    # Prüfe ob Simulation gerade läuft
    if st.session_state.get('simulation_running', False) or st.session_state.get('simulation_started', False):
        # Simulation läuft noch - zeige Info
        elapsed = time.time() - st.session_state.get('simulation_start_time', time.time())
        
        # WICHTIG: Kein Timeout mehr - Simulation darf so lange laufen wie nötig
        
        # KRITISCH: KEIN st.rerun() hier - das würde eine Endlosschleife verursachen!
        # Die Simulation läuft bereits im Hintergrund und wird automatisch die Flags zurücksetzen,
        # wenn sie fertig ist. Ein st.rerun() würde nur die Seite neu laden, während die Simulation
        # noch läuft, was zu einer Endlosschleife führt.
        
        st.info(f"🔄 Die Simulation wird gerade ausgeführt. Bitte warten Sie... ({int(elapsed)}s)")
        st.stop()  # Stoppe die Seite, bis Simulation fertig ist
        return
    
    # Prüfe ob Simulator verfügbar ist
    if 'simulator' not in st.session_state or st.session_state.simulator is None:
        # Prüfe ob Simulation bereits gestartet wurde (aber noch nicht abgeschlossen)
        if st.session_state.get('happy_path_run', False):
            # Simulation wurde bereits ausgeführt, aber Simulator ist nicht verfügbar
            # Das sollte nicht passieren, aber falls doch, zeige eine Warnung
            st.warning("⚠️ Die Simulation wurde ausgeführt, aber der Simulator ist nicht verfügbar. Bitte starten Sie die Simulation erneut.")
            st.stop()
        else:
            # Simulation wurde noch nicht gestartet - das sollte nicht passieren, da run_happy_path_simulation() vorher aufgerufen wird
            # Aber falls doch, zeige eine Warnung
            st.warning("⚠️ Die Simulation wurde noch nicht gestartet. Bitte warten Sie, bis die automatische Simulation abgeschlossen ist.")
            # Versuche die Simulation zu starten (falls sie noch nicht gestartet wurde)
            run_happy_path_simulation()
            st.stop()
