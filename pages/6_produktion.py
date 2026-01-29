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
render_scenario_sidebar(key_suffix="_produktion")

# Initialisiere Session State
initialize_session_state()

# WICHTIG: Stelle sicher, dass daily_demands_actual aktualisiert wird, wenn sich Szenarien ändern
# Dies ist notwendig, damit die Produktion korrekt aktualisiert wird
from ui.volume_planning_utils import calculate_volume_planning_demand
calculate_volume_planning_demand()

# WICHTIG: material_inventory_data sollte bereits beim App-Start initialisiert worden sein
# (durch initialize_all_page_calculations() in app.py)
# Falls nicht, versuche es jetzt zu initialisieren (Fallback für direkten Seitenaufruf)
if 'material_inventory_data' not in st.session_state:
    from ui.material_calculations import calculate_material_inventory
    try:
        calculate_material_inventory()
    except Exception:
        pass  # Wird beim Laden der Seite behandelt

st.title("🏭 Produktion")
st.markdown("Übersicht über Produktionsplanung, tatsächliche Produktion und Materialverfügbarkeit")

# Happy Path: Automatische Simulation wenn noch keine Ergebnisse vorhanden
run_happy_path_simulation()

if st.session_state.results_df is None:
    st.warning("⚠️ Keine Simulationsergebnisse verfügbar.")
    st.stop()

results_df = st.session_state.results_df

# Zeitraum (erweitert um erste Tage von 2028)
planning_year = st.session_state.get('planning_year', 2027)
start_date = date(planning_year, 1, 1)
end_date = date(planning_year + 1, 1, 10)  # Erweitert bis 10.01.2028
workday_calc = WorkdayCalculator(year=planning_year)

# NEU: Lese Produktionslogs direkt aus dem ProductionPlanner
# WICHTIG: Cache-Key erweitert um Szenarien, damit Cache invalidiert wird wenn Marketing hinzugefügt wird
def get_production_logs():
    """
    Wrapper-Funktion, die die Berechnungslogik aus ui.production_calculations verwendet.
    Diese Funktion wird von der Seite verwendet, um production_logs_cache zu berechnen.
    """
    from ui.production_calculations import calculate_production_logs
    return calculate_production_logs()

# Alte Implementierung entfernt - wird jetzt in ui.production_calculations.py verwendet

# Erstelle Produktions-Log
try:
    with st.spinner("🔄 Lade Produktionsdaten..."):
        production_logs = get_production_logs()
except Exception as e:
    st.error(f"⚠️ Fehler bei Berechnung der Produktionslogs: {str(e)}")
    st.exception(e)
    production_logs = {}

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
    
    # Filtere auf den Zeitraum (2027 + erste Tage 2028)
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
    saddle_name = MasterData.BOM[product]['saddle']
    
    # Definiere Spaltenreihenfolge (Wochentag vor Datum)
    # Hinweis: "Produktionsbedarf" und "Rang" sind nur Hilfsberechnungen
    # und werden nicht angezeigt (Spalten beginnen mit "_")
    column_order = [
        'Wochentag',
        'Datum',
        'Schichtanzahl',
        'Auslastung (%)',
        saddle_name,  # Konkreter Sattel-Name
        'geplante PM',
        'tatsächliche PM',
        'fertiggestellte PM',
        'Backlog'
    ]
    
    # Prüfe, ob alle Spalten vorhanden sind
    available_columns = [col for col in column_order if col in df_prod_filtered.columns]
    df_display = df_prod_filtered[available_columns].copy()
    
    # Formatierung: Auslastung auf 2 Nachkommastellen
    if 'Auslastung (%)' in df_display.columns:
        # Konvertiere zu numerisch und formatiere auf 2 Nachkommastellen
        df_display['Auslastung (%)'] = pd.to_numeric(df_display['Auslastung (%)'], errors='coerce').round(2)
        # Stelle sicher, dass NaN-Werte als leere Strings angezeigt werden
        df_display['Auslastung (%)'] = df_display['Auslastung (%)'].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else ""
        )
    
    # Farblegende oben rechts
    col1, col2 = st.columns([1, 1])
    with col2:
        st.markdown("""
        <div style="text-align: right; margin-bottom: 10px;">
            <span style="background-color: #ffebee; padding: 2px 8px; border-radius: 3px; margin-left: 5px;">Wochenende</span>
            <span style="background-color: #c8e6c9; padding: 2px 8px; border-radius: 3px; margin-left: 5px;">Feiertag</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Identifiziere numerische Spalten für Summenzeile
    numeric_cols = []
    for col in df_display.columns:
        if col not in ['Wochentag', 'Datum']:
            # Prüfe, ob Spalte numerische Werte enthält
            try:
                pd.to_numeric(df_display[col].replace('', 0), errors='coerce').sum()
                numeric_cols.append(col)
            except:
                pass
    
    # Erstelle Summenzeile
    # KRITISCH: Summe wird über das GESAMTE JAHR berechnet (df_prod), nicht nur über gefilterten Zeitraum (df_display)
    # Dies stellt sicher, dass die Summen korrekt sind, auch wenn nur ein Teil des Jahres angezeigt wird
    if numeric_cols and len(df_display) > 0:
        sum_row = {'Wochentag': 'Summe', 'Datum': ''}
        for col in df_display.columns:
            if col in numeric_cols:
                # Für Auslastung: Durchschnitt statt Summe (nur über angezeigten Zeitraum)
                if col == 'Auslastung (%)':
                    # Konvertiere String-Werte zurück zu Float für Berechnung
                    numeric_values = df_display[col].apply(
                        lambda x: float(x) if isinstance(x, str) and x.strip() != '' else (float(x) if pd.notna(x) else 0)
                    )
                    avg_utilization = numeric_values.mean()
                    sum_row[col] = f"{avg_utilization:.2f}" if pd.notna(avg_utilization) else ""
                else:
                    # KRITISCH: Summe über GESAMTES JAHR (df_prod), nicht nur gefilterten Zeitraum
                    # Dies stellt sicher, dass die Summen korrekt sind
                    if col in df_prod.columns:
                        sum_value = int(pd.to_numeric(df_prod[col].replace('', 0), errors='coerce').sum())
                        
                        # KRITISCH: Für fertiggestellte PM addiere auch die tatsächliche PM vom letzten Tag
                        # Die tatsächliche PM vom letzten Tag wird nicht als fertiggestellte PM am nächsten Tag berücksichtigt
                        # weil es keinen nächsten Tag gibt. Daher müssen wir sie hier explizit addieren.
                        if col == 'fertiggestellte PM' and 'tatsächliche PM' in df_prod.columns and 'Datum' in df_prod.columns:
                            last_date_str = date(planning_year, 12, 31).strftime('%d.%m.%Y')
                            last_row = df_prod[df_prod['Datum'] == last_date_str]
                            if not last_row.empty:
                                last_actual_pm_val = last_row.iloc[0].get('tatsächliche PM', 0)
                                try:
                                    last_actual_pm = float(pd.to_numeric(last_actual_pm_val, errors='coerce')) if pd.notna(pd.to_numeric(last_actual_pm_val, errors='coerce')) else 0.0
                                    if last_actual_pm > 0:
                                        sum_value += int(last_actual_pm)
                                except (ValueError, TypeError):
                                    pass
                        
                        sum_row[col] = sum_value
                    else:
                        # Fallback: Summe über angezeigten Zeitraum
                        sum_row[col] = int(pd.to_numeric(df_display[col].replace('', 0), errors='coerce').sum())
            elif col not in sum_row:
                sum_row[col] = ''
        
        # Füge Summenzeile als neue Zeile hinzu
        sum_df = pd.DataFrame([sum_row])
        df_display_with_sum = pd.concat([df_display, sum_df], ignore_index=True)
        
        # Erweitere Flags für Summenzeile
        weekend_flags_extended = list(weekend_flags) + [False]
        holiday_flags_extended = list(holiday_flags) + [False]
    else:
        df_display_with_sum = df_display
        weekend_flags_extended = weekend_flags
        holiday_flags_extended = holiday_flags
    
    # Styling-Funktion mit Summenzeile
    def style_row_with_sum(row):
        idx = row.name
        # Summenzeile: grauer Hintergrund, fett
        if idx >= len(weekend_flags):
            return ['background-color: #e0e0e0; font-weight: bold'] * len(row)
        # Normale Zeilen
        if idx < len(weekend_flags_extended):
            if weekend_flags_extended[idx]:
                return ['background-color: #ffebee'] * len(row)
            if holiday_flags_extended[idx]:
                return ['background-color: #c8e6c9'] * len(row)
        return [''] * len(row)
    
    # Zeige Tabelle
    st.dataframe(
        df_display_with_sum.style.apply(style_row_with_sum, axis=1),
        width='stretch',
        hide_index=True
    )
    
    st.divider()
