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

# Theme Toggle (oben rechts, global)
# Theme-Toggle entfernt - Light Mode ist Standard
from ui.theme_toggle import apply_theme
apply_theme("light")  # Light Mode immer aktiv

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
render_scenario_sidebar(key_suffix="_inbound")

st.title("🚢 Inbound Logistik")
st.markdown("Überwachung der Verschiffungen und Zuläufe zum Lager Dortmund.")

# Initialisiere Session State
initialize_session_state()

# WICHTIG: Stelle sicher, dass daily_demands_actual aktualisiert wird, wenn sich Szenarien ändern
# Dies ist notwendig, damit die Inbound-Tabelle korrekt aktualisiert wird
from ui.volume_planning_utils import calculate_volume_planning_demand
calculate_volume_planning_demand()

# Happy Path: Automatische Simulation wenn noch keine Ergebnisse vorhanden
run_happy_path_simulation()

# Prüfe ob Simulator verfügbar ist
ensure_simulator_available()

# KRITISCH: Prüfe ob Simulator wirklich verfügbar ist (könnte None sein bei Fehlern)
if 'simulator' not in st.session_state or st.session_state.simulator is None:
    st.error("❌ Simulator ist nicht verfügbar. Bitte starten Sie die Simulation neu.")
    st.stop()

manager = st.session_state.simulator.china_transport_manager
workday_calc = manager.workday_calculator

# Berechne Sattel-Shares (konsistent mit anderen Seiten)
saddle_shares = MasterData.calculate_saddle_shares()
        
# Rufe die neue Methode aus dem ChinaTransportManager auf
df = manager.get_inbound_log_dataframe(saddle_shares)

if not df.empty:
    # Speichere Flags für Wochenende und Feiertage
    weekend_flags = df['Is_Weekend'].values if 'Is_Weekend' in df.columns else [False] * len(df)
    holiday_flags = df['Is_Holiday'].values if 'Is_Holiday' in df.columns else [False] * len(df)
    
    # Entferne Flags aus Anzeige (werden nur für Styling verwendet)
    if 'Is_Weekend' in df.columns:
        df = df.drop(columns=['Is_Weekend'])
    if 'Is_Holiday' in df.columns:
        df = df.drop(columns=['Is_Holiday'])
    
    # NEU: Füge Summenzeilen zwischen Verschiffungen ein
    # Einfacher Ansatz: Iteriere durch DataFrame, füge jede Zeile hinzu, füge Summenzeilen dazwischen ein
    numeric_cols = ['Menge Gesamt'] + [col for col in df.columns if col in saddle_shares.keys()]
    rows_with_sums = []
    weekend_flags_extended = []
    holiday_flags_extended = []
    shipment_sum_flags = []  # Flag für Summenzeilen zwischen Verschiffungen
    
    # Sammle Zeilen pro Verschiffung für Summenberechnung
    current_shipment_rows = []  # Liste von Indizes der aktuellen Verschiffung
    last_ship_arrival = None  # Letztes "Ankunft Schiff 🇩🇪" Datum
    
    def create_sum_row_from_indices(indices):
        """Erstellt eine Summenzeile für eine Verschiffung basierend auf Indizes"""
        sum_row = {}
        
        for col in df.columns:
            if col in numeric_cols:
                # Summiere numerische Werte aus den Zeilen dieser Verschiffung
                # WICHTIG: Berücksichtige Ladungsverlust - wenn eine Zeile "Ladungsverlust: Ja" hat,
                # dann sind die Mengen bereits auf 0 gesetzt, daher wird automatisch korrekt summiert
                try:
                    values = []
                    for idx in indices:
                        val = df.iloc[idx][col]
                        num_val = pd.to_numeric(val, errors='coerce')
                        if pd.notna(num_val):
                            values.append(num_val)
                    sum_row[col] = int(sum(values)) if values else 0
                except (ValueError, TypeError):
                    sum_row[col] = 0
            elif col in ['Verspätung', 'Ladungsverlust', 'Abfahrt LKW 🇨🇳']:
                # Diese Spalten sollen in Summenzeilen leer sein
                sum_row[col] = ''
            elif col in ['Abfahrt Schiff 🇨🇳', 'Ankunft Schiff 🇩🇪', 
                         'Abfahrt LKW 🇩🇪', 'Geplante Ankunft LKW 🇩🇪', 'Tatsächliche Ankunft LKW 🇩🇪']:
                # Übernehme von der letzten Zeile der Verschiffung (zeigt die tatsächlichen Ankunftsdaten)
                # WICHTIG: Verwende die letzte Zeile, da diese die tatsächlichen (ggf. verspäteten) Daten enthält
                # Dies berücksichtigt automatisch Verspätungen und andere Szenarien
                if indices:
                    sum_row[col] = df.iloc[indices[-1]][col]
                else:
                    sum_row[col] = ''
            elif col in ['Wochentag', 'Datum', 'Ankunft LKW 🇨🇳']:
                # Diese Spalten sollen in Summenzeilen leer sein
                sum_row[col] = ''
            else:
                # Alle anderen Spalten leer
                sum_row[col] = ''
        return sum_row
    
    # NEUE STRATEGIE: Gruppiere zuerst alle Zeilen nach Verschiffung, dann füge Summenzeilen ein
    # Eine Verschiffung ist durch "Abfahrt Schiff 🇨🇳" UND "Ankunft Schiff 🇩🇪" gemeinsam definiert
    # WICHTIG: Wir müssen die Zeilen in der richtigen Reihenfolge durchgehen und Summenzeilen
    # NACH der letzten Zeile jeder Verschiffungsgruppe einfügen
    
    # Erstelle Liste mit (index, shipment_key) für jede Zeile
    rows_with_shipment_keys = []
    for idx, row in df.iterrows():
        current_ship_departure = row.get('Abfahrt Schiff 🇨🇳', '')
        current_ship_arrival = row.get('Ankunft Schiff 🇩🇪', '')
        
        # Bestimme den Verschiffungsschlüssel für diese Zeile
        if current_ship_departure and current_ship_departure != '' and current_ship_arrival and current_ship_arrival != '':
            row_shipment_key = (current_ship_departure, current_ship_arrival)
        else:
            row_shipment_key = None
        
        rows_with_shipment_keys.append((idx, row_shipment_key))
    
    # Iteriere durch alle Zeilen und füge sie hinzu
    # WICHTIG: Leere Zeilen (Wochenende) beenden die Verschiffung NICHT
    # Nur wenn eine NEUE Verschiffung beginnt (mit anderen Schiffsdaten), wird die Summenzeile eingefügt
    prev_shipment_key = None
    current_shipment_indices = []
    
    for idx, row_shipment_key in rows_with_shipment_keys:
        row = df.iloc[idx]
        
        # Prüfe ob sich die Verschiffung geändert hat (VOR dem Hinzufügen dieser Zeile)
        # WICHTIG: Nur wenn eine NEUE Verschiffung beginnt (nicht bei leeren Zeilen)
        if (prev_shipment_key is not None and 
            row_shipment_key is not None and 
            row_shipment_key != prev_shipment_key):
            # Verschiffung hat sich geändert - füge Summenzeile für vorherige Verschiffung ein
            if current_shipment_indices:
                sum_row = create_sum_row_from_indices(current_shipment_indices)
                rows_with_sums.append(sum_row)
                weekend_flags_extended.append(False)
                holiday_flags_extended.append(False)
                shipment_sum_flags.append(True)
                current_shipment_indices = []
        
        # Füge die aktuelle Zeile IMMER hinzu (keine Zeile geht verloren)
        rows_with_sums.append(row.to_dict() if isinstance(row, pd.Series) else row)
        weekend_flags_extended.append(weekend_flags[idx])
        holiday_flags_extended.append(holiday_flags[idx])
        shipment_sum_flags.append(False)
        
        # Aktualisiere Tracking
        if row_shipment_key is not None:
            # Zeile mit Verschiffung - füge Index zur aktuellen Gruppe hinzu
            if row_shipment_key == prev_shipment_key:
                # Weiterhin gleiche Verschiffung
                current_shipment_indices.append(idx)
            else:
                # Neue Verschiffung beginnt (oder erste Verschiffung)
                prev_shipment_key = row_shipment_key
                current_shipment_indices = [idx]
        # WICHTIG: Leere Zeilen (row_shipment_key is None) ändern nichts am Tracking
        # Die aktuelle Verschiffung bleibt aktiv, auch wenn dazwischen leere Zeilen kommen
    
    # Füge Summenzeile für die letzte Verschiffung ein (falls vorhanden)
    if prev_shipment_key is not None and current_shipment_indices:
        sum_row = create_sum_row_from_indices(current_shipment_indices)
        rows_with_sums.append(sum_row)
        weekend_flags_extended.append(False)
        holiday_flags_extended.append(False)
        shipment_sum_flags.append(True)
    
    # Erstelle neuen DataFrame mit Summenzeilen
    df_with_sums = pd.DataFrame(rows_with_sums)
    
    # Füge Gesamt-Summenzeile am Ende hinzu
    total_sum_row = {}
    for col in df.columns:
        if col in numeric_cols:
            try:
                numeric_values = pd.to_numeric(df[col], errors='coerce')
                total_sum_row[col] = int(numeric_values.sum()) if not numeric_values.isna().all() else 0
            except (ValueError, TypeError):
                total_sum_row[col] = 0
        elif col not in ['Wochentag', 'Datum', 'Verspätung', 'Ladungsverlust', 'Abfahrt LKW 🇨🇳', 'Ankunft LKW 🇨🇳', 
                         'Abfahrt Schiff 🇨🇳', 'Ankunft Schiff 🇩🇪', 'Abfahrt LKW 🇩🇪', 
                         'Geplante Ankunft LKW 🇩🇪', 'Tatsächliche Ankunft LKW 🇩🇪']:
            total_sum_row[col] = ''
        else:
            total_sum_row[col] = ''
    total_sum_row['Wochentag'] = 'Summe'
    total_sum_row['Datum'] = ''
    
    df_with_sum = pd.concat([df_with_sums, pd.DataFrame([total_sum_row])], ignore_index=True)
    weekend_flags_extended.append(False)
    holiday_flags_extended.append(False)
    shipment_sum_flags.append(False)  # Gesamt-Summenzeile ist keine Verschiffungs-Summenzeile
    
    # Entferne Flags aus Anzeige (werden nur für Styling verwendet)
    if 'Is_Weekend' in df.columns:
        df = df.drop(columns=['Is_Weekend'])
    if 'Is_Holiday' in df.columns:
        df = df.drop(columns=['Is_Holiday'])
    
    # Theme-aware Styling verwenden
    from ui.theme_aware_styling import style_row_with_theme, apply_theme_to_styled_dataframe
    
    # Styling-Funktion für Summenzeile (theme-aware)
    def style_row_with_sum(row):
        row_idx = row.name
        
        # Gesamt-Summenzeile (letzte Zeile) - dunkelgrau
        if row_idx >= len(shipment_sum_flags):
            return ['background-color: #e0e0e0; font-weight: bold' for _ in row]
        
        # Summenzeile zwischen Verschiffungen - leicht grau
        if row_idx < len(shipment_sum_flags) and shipment_sum_flags[row_idx]:
            return ['background-color: #f0f0f0; font-weight: bold' for _ in row]
        
        # Normale Zeilen mit Wochenende/Feiertag
        if row_idx < len(weekend_flags_extended):
            if weekend_flags_extended[row_idx]:
                return ['background-color: #ffcccc' for _ in row]
            elif holiday_flags_extended[row_idx]:
                return ['background-color: #c8e6c9' for _ in row]
        
        return [''] * len(row)
    
    styled_df = df_with_sum.style.apply(style_row_with_sum, axis=1)
    # KRITISCH: Wende Theme-Styling auf Header an (mit Fehlerbehandlung)
    try:
        styled_df = apply_theme_to_styled_dataframe(styled_df)
    except Exception:
        pass  # Bei Fehler: Verwende Styler ohne Header-Styling
    st.dataframe(styled_df, width='stretch', hide_index=True, height=800)
else:
    st.info("Keine Inbound-Daten vorhanden.")
