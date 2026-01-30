"""
Page Initialization
Zentrale Initialisierung aller Page-Berechnungen beim App-Start
"""

import streamlit as st
import pandas as pd
from ui.volume_planning_utils import calculate_volume_planning_demand, _validate_parameters
from ui.utils import run_happy_path_simulation
from ui.production_calculations import calculate_production_logs
from ui.material_calculations import calculate_material_inventory


def initialize_all_page_calculations():
    """
    Initialisiert alle Page-Berechnungen beim App-Start.
    Diese Funktion stellt sicher, dass alle Caches verfügbar sind, bevor Seiten geladen werden.
    
    WICHTIG: Diese Funktion muss VOR dem Laden einer Page aufgerufen werden.
    Sie wird automatisch in app.py aufgerufen.
    
    WICHTIG: Berechnungen werden nur durchgeführt, wenn PRODUCT_SALES_SHARES und SEASONALITY jeweils 100% ergeben.
    
    Abhängigkeitsreihenfolge:
    1. Parameter-Validierung - Prüft ob Verkaufsanteile und Saisonalität jeweils 100% ergeben
    2. calculate_volume_planning_demand() - Basis für alle anderen Berechnungen (nur wenn Parameter gültig)
    3. run_happy_path_simulation() - Erstellt Simulator und statische Logs (nur wenn Parameter gültig)
    4. Iterative Berechnung zur Auflösung der zirkulären Abhängigkeit:
       - Iteration 1: calculate_production_logs() mit statischen Werten
       - Iteration 1: calculate_material_inventory() mit production_logs_cache
       - Iteration 2: calculate_production_logs() mit korrigierten material_inventory_data
       - Iteration 2: calculate_material_inventory() mit korrigierten production_logs_cache
    """
    # Schritt 0: Parameter-Validierung
    is_valid, error_message = _validate_parameters()
    if not is_valid:
        # Berechnungen werden nicht durchgeführt, wenn Parameter ungültig sind
        # Die Fehlermeldung wird bereits in calculate_volume_planning_demand() angezeigt
        return
    
    # Schritt 1: Volumenplanung (Basis für alle anderen Berechnungen)
    calculate_volume_planning_demand()
    
    # Schritt 2: Happy Path Simulation (erstellt Simulator und statische Logs)
    run_happy_path_simulation()
    
    # PERFORMANCE: Schritt 3 wird jetzt LAZY geladen (nur wenn benötigt)
    # Die iterative Berechnung wird nicht mehr beim App-Start ausgeführt,
    # sondern erst wenn eine Seite sie wirklich benötigt (z.B. Produktion, Materiallager)
    # Dies spart ~30-60 Sekunden beim App-Start
    # 
    # Die Berechnung wird automatisch ausgeführt, wenn:
    # - Eine Seite calculate_production_logs() oder calculate_material_inventory() aufruft
    # - Diese Funktionen prüfen selbst, ob die iterative Berechnung nötig ist
    pass
