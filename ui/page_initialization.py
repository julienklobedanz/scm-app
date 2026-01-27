"""
Page Initialization
Zentrale Initialisierung aller Page-Berechnungen beim App-Start
"""

import streamlit as st
import pandas as pd
from ui.volume_planning_utils import calculate_volume_planning_demand
from ui.utils import run_happy_path_simulation
from ui.production_calculations import calculate_production_logs
from ui.material_calculations import calculate_material_inventory


def initialize_all_page_calculations():
    """
    Initialisiert alle Page-Berechnungen beim App-Start.
    Diese Funktion stellt sicher, dass alle Caches verfügbar sind, bevor Seiten geladen werden.
    
    WICHTIG: Diese Funktion muss VOR dem Laden einer Page aufgerufen werden.
    Sie wird automatisch in app.py aufgerufen.
    
    Abhängigkeitsreihenfolge:
    1. calculate_volume_planning_demand() - Basis für alle anderen Berechnungen
    2. run_happy_path_simulation() - Erstellt Simulator und statische Logs
    3. Iterative Berechnung zur Auflösung der zirkulären Abhängigkeit:
       - Iteration 1: calculate_production_logs() mit statischen Werten
       - Iteration 1: calculate_material_inventory() mit production_logs_cache
       - Iteration 2: calculate_production_logs() mit korrigierten material_inventory_data
       - Iteration 2: calculate_material_inventory() mit korrigierten production_logs_cache
    """
    # Schritt 1: Volumenplanung (Basis für alle anderen Berechnungen)
    calculate_volume_planning_demand()
    
    # Schritt 2: Happy Path Simulation (erstellt Simulator und statische Logs)
    run_happy_path_simulation()
    
    # Schritt 3: Iterative Berechnung zur Auflösung der zirkulären Abhängigkeit
    # WICHTIG: Nur wenn Simulator verfügbar ist
    # OPTIMIERT: Führe nur aus wenn Simulation bereits abgeschlossen ist
    if ('simulator' in st.session_state and st.session_state.simulator is not None and 
        st.session_state.get('happy_path_run', False) and 
        st.session_state.get('results_df') is not None):
        # FIX: Konvergenz-Check hinzugefügt für stabile iterative Berechnung
        max_iterations = 5
        previous_logs_hash = None
        
        # DEBUG: Speichere Iterations-Info für Test-1.3
        iterations_performed = 0
        convergence_reached = False
        
        try:
            for iteration in range(max_iterations):
                iterations_performed = iteration + 1
                
                # ITERATION: Berechne production_logs und material_inventory
                try:
                    calculate_production_logs()
                except Exception as e:
                    # Bei Fehler: Logge und breche ab
                    st.warning(f"⚠️ Fehler bei calculate_production_logs() in Iteration {iteration}: {str(e)}")
                    break  # Bei Fehler abbrechen
                
                if 'production_logs_cache' not in st.session_state:
                    break
                
                try:
                    material_inventory_data, saddle_logs = calculate_material_inventory()
                    # saddle_logs wird nicht im session_state gespeichert (nur für UI-Anzeige)
                except Exception as e:
                    # Bei Fehler: Logge und breche ab
                    st.warning(f"⚠️ Fehler bei calculate_material_inventory() in Iteration {iteration}: {str(e)}")
                    break  # Bei Fehler abbrechen
                
                # Konvergenz-Check: Prüfe ob sich Werte stabilisiert haben
                # Vereinfachter Check über Summe der Produktionsmengen
                current_logs = st.session_state.get('production_logs_cache', {})
                if current_logs:
                    try:
                        current_hash = sum([
                            df['tatsächliche PM'].sum() 
                            for df in current_logs.values() 
                            if isinstance(df, pd.DataFrame) and not df.empty and 'tatsächliche PM' in df.columns
                        ])
                        
                        # Wenn Hash identisch ist, haben sich Werte nicht geändert -> Konvergenz erreicht
                        if previous_logs_hash is not None and current_hash == previous_logs_hash:
                            convergence_reached = True
                            break  # Konvergenz erreicht
                        
                        previous_logs_hash = current_hash
                    except Exception as e:
                        # Bei Fehler beim Hash-Berechnen: Breche ab
                        st.warning(f"⚠️ Fehler bei Konvergenz-Check in Iteration {iteration}: {str(e)}")
                        break
                else:
                    break  # Keine Logs vorhanden
            
            # DEBUG: Speichere Iterations-Info für Test-1.3 (sichtbar in Session State)
            st.session_state['convergence_iterations'] = iterations_performed
            st.session_state['convergence_reached'] = convergence_reached
        except Exception as e:
            # Bei kritischem Fehler: Logge und setze Default-Werte
            st.error(f"❌ Kritischer Fehler in initialize_all_page_calculations(): {str(e)}")
            st.exception(e)
            st.session_state['convergence_iterations'] = 0
            st.session_state['convergence_reached'] = False
