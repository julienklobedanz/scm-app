"""
Page Initialization
Zentrale Initialisierung aller Page-Berechnungen beim App-Start
"""

import streamlit as st
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
    if 'simulator' in st.session_state and st.session_state.simulator is not None:
        # ITERATION 1: Erste Berechnung mit statischen Werten
        try:
            calculate_production_logs()
        except Exception:
            pass  # Wird später beim Laden der Seite behandelt
        
        if 'production_logs_cache' in st.session_state:
            try:
                material_inventory_data, saddle_logs = calculate_material_inventory()
                # saddle_logs wird nicht im session_state gespeichert (nur für UI-Anzeige)
            except Exception:
                pass  # Wird später beim Laden der Seite behandelt
        
        # ITERATION 2: Zweite Berechnung mit korrigierten Werten (falls material_inventory_data verfügbar)
        if 'material_inventory_data' in st.session_state:
            try:
                # Berechne production_logs_cache erneut mit korrigierten material_inventory_data
                calculate_production_logs()
                
                # Berechne material_inventory_data erneut mit korrigierten production_logs_cache
                if 'production_logs_cache' in st.session_state:
                    material_inventory_data, saddle_logs = calculate_material_inventory()
                    # saddle_logs wird nicht im session_state gespeichert (nur für UI-Anzeige)
            except Exception:
                pass  # Wird später beim Laden der Seite behandelt
