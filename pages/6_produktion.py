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

# WICHTIG: Stelle sicher, dass Materiallager-Daten verfügbar sind (für Sattel-Bestände)
# Diese werden benötigt, um die Sattel-Bestände in der Produktionstabelle korrekt anzuzeigen
if 'material_inventory_data' not in st.session_state:
    # Importiere create_saddle_inventory_log aus Materiallager-Seite
    try:
        import sys
        import os
        materiallager_path = os.path.join(os.path.dirname(__file__), "5_materiallager.py")
        if os.path.exists(materiallager_path):
            import importlib.util
            spec = importlib.util.spec_from_file_location("materiallager_module", materiallager_path)
            if spec and spec.loader:
                materiallager_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(materiallager_module)
                # Berechne Materiallager-Daten (wird gecacht)
                materiallager_module.create_saddle_inventory_log()
    except Exception:
        # Stille Fehlerbehandlung - Materiallager-Daten werden später geladen
        pass

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
    """Liest Produktionslogs direkt aus dem ProductionPlanner (Single Source of Truth)"""
    if 'simulator' not in st.session_state or st.session_state.simulator is None:
        st.error("⚠️ Simulator nicht verfügbar. Bitte führen Sie zuerst die Simulation aus.")
        return {}
    
    planner = st.session_state.simulator.production_planner
    
    if not hasattr(planner, 'production_logs') or not planner.production_logs:
        st.warning("⚠️ Keine Produktionslogs verfügbar. Bitte führen Sie die Simulation erneut aus.")
        return {}
    
    # WICHTIG: Hole Cache-Key für Szenarien (für Cache-Invalidierung)
    volume_planning_cache_key = st.session_state.get('volume_planning_cache_key', None)
    
    # Erweitere Cache-Key um Szenarien
    cache_key = f"production_logs_{volume_planning_cache_key}"
    
    # Prüfe Cache
    if cache_key in st.session_state and 'production_logs_cache' in st.session_state:
        cached_key = st.session_state.get('production_logs_cache_key', None)
        if cached_key == cache_key:
            return st.session_state.production_logs_cache
    
    # Konvertiere Logs zu DataFrames (ERSTE RUNDE: Nur konvertieren, noch keine dynamischen Updates)
    production_logs = {}
    for product, logs in planner.production_logs.items():
        if logs:
            production_logs[product] = pd.DataFrame(logs)
        else:
            production_logs[product] = pd.DataFrame()
    
    # ZWEITE RUNDE: Dynamische Updates (nachdem alle DataFrames erstellt sind)
    # WICHTIG: Überschreibe "tatsächliche PM" dynamisch (mit Marketing)
    # Das stellt sicher, dass Marketing sofort berücksichtigt wird
    # PROBLEM: results_df['Actual_Build'] ist statisch (wird während Simulation berechnet)
    # LÖSUNG: Berechne Produktion direkt aus daily_demands_actual, berücksichtige Materialverfügbarkeit
    daily_demands_actual = st.session_state.get('daily_demands_actual', {})
    material_inventory_data = st.session_state.get('material_inventory_data', {})
    
    if daily_demands_actual:
        for product, df in production_logs.items():
            if df.empty or 'Datum' not in df.columns or 'tatsächliche PM' not in df.columns:
                continue
            
            saddle_name = MasterData.BOM[product]['saddle']
            
            # Iteriere über alle Zeilen und aktualisiere dynamisch
            for idx, row in df.iterrows():
                date_str = row.get('Datum', '')
                if date_str:
                    try:
                        from datetime import datetime, timedelta
                        row_date = datetime.strptime(date_str, MasterData.DATE_FORMAT).date()
                        # Konvertiere Datum zu Tag-Index
                        day = (row_date - date(planning_year, 1, 1)).days
                        
                        if day in daily_demands_actual:
                            # Hole Nachfrage mit Marketing
                            product_demands = daily_demands_actual[day]
                            product_demand = product_demands.get(product, 0)
                            
                            # Hole Materialverfügbarkeit aus production_logs (Sattel-Bestand morgens)
                            saddle_stock_morning = row.get(saddle_name, 0)
                            
                            # Hole Kapazität (Schichtanzahl * Kapazität pro Schicht)
                            shifts = row.get('Schichtanzahl', 0)
                            working_hours = MasterData.GLOBAL_CONFIG.get('working_hours_per_shift', 8)
                            capacity_per_hour = MasterData.GLOBAL_CONFIG.get('capacity_per_hour', 130)
                            daily_capacity = shifts * working_hours * capacity_per_hour
                            
                            # Berechne Gesamtnachfrage (für proportionale Verteilung)
                            total_demand = sum(product_demands.values())
                            
                            # Berechne "tatsächliche PM" dynamisch:
                            # 1. Anteilige Produktion basierend auf Nachfrage
                            if total_demand > 0 and daily_capacity > 0:
                                proportional_share = product_demand / total_demand
                                proportional_pm = int(daily_capacity * proportional_share)
                            else:
                                proportional_pm = 0
                            
                            # 2. Begrenze durch Materialverfügbarkeit (Sattel)
                            # Konvertiere saddle_stock_morning zu float (falls string oder '∞')
                            try:
                                if isinstance(saddle_stock_morning, str):
                                    if saddle_stock_morning == '∞':
                                        saddle_available = float('inf')
                                    else:
                                        saddle_available = float(saddle_stock_morning)
                                else:
                                    saddle_available = float(saddle_stock_morning)
                            except (ValueError, TypeError):
                                saddle_available = 0.0
                            
                            # 3. Tatsächliche PM = MIN(Proportional, Materialverfügbar, Nachfrage)
                            if saddle_available == float('inf'):
                                # Unbegrenzt verfügbar
                                dynamic_pm = min(proportional_pm, product_demand)
                            else:
                                # Begrenzt durch Material
                                dynamic_pm = min(proportional_pm, int(saddle_available), product_demand)
                            
                            # Überschreibe "tatsächliche PM" mit dynamisch berechnetem Wert
                            df.at[idx, 'tatsächliche PM'] = max(0, dynamic_pm)
                            
                            # WICHTIG: Aktualisiere Sattel-Bestand dynamisch aus Materiallager
                            # WICHTIG: material_inventory_data enthält bereits den "Bestand morgens" pro Tag
                            # Dieser Bestand ist der GESAMTBESTAND für diesen Sattel-Typ (nicht pro Produkt)
                            # Wenn mehrere Produkte denselben Sattel verwenden, zeigen alle den gleichen Gesamtbestand
                            if row_date in material_inventory_data:
                                # Hole "Bestand morgens" direkt aus material_inventory_data
                                # Dieser Wert ist bereits korrekt berechnet (inkl. Zugang und Verbrauch bis zum VORHERIGEN Tag)
                                stock_morning = material_inventory_data[row_date].get(saddle_name, 0.0)
                                
                                # Überschreibe Sattel-Bestand mit Wert aus Materiallager (Bestand morgens, vor Produktion)
                                df.at[idx, saddle_name] = int(round(stock_morning)) if stock_morning > 0 else 0
                    except (ValueError, TypeError) as e:
                        # Bei Fehler: Behalte ursprünglichen Wert
                        pass
        
        # DRITTE RUNDE: Aktualisiere "fertiggestellte PM" dynamisch (NACH Aktualisierung aller "tatsächliche PM")
        # WICHTIG: "fertiggestellte PM" = "tatsächliche PM" vom VORHERIGEN ARBEITSTAG
        # Das stellt sicher, dass "fertiggestellte PM" konsistent mit der neuen "tatsächlichen PM" ist
        for product, df in production_logs.items():
            if df.empty or 'Datum' not in df.columns or 'tatsächliche PM' not in df.columns or 'fertiggestellte PM' not in df.columns:
                continue
            
            # Sortiere DataFrame nach Datum (wichtig für korrekte Reihenfolge)
            # WICHTIG: Reset Index nach Sortierung, damit wir über die Zeilen in sortierter Reihenfolge iterieren können
            df_sorted = df.copy()
            df_sorted['_date_parsed'] = pd.to_datetime(df_sorted['Datum'], format=MasterData.DATE_FORMAT)
            df_sorted = df_sorted.sort_values('_date_parsed').reset_index(drop=True)
            
            # Erstelle Mapping: Datum -> Index in sortiertem DataFrame
            date_to_idx = {}
            for idx, row in df_sorted.iterrows():
                date_str = row.get('Datum', '')
                if date_str:
                    try:
                        row_date = datetime.strptime(date_str, MasterData.DATE_FORMAT).date()
                        date_to_idx[row_date] = idx
                    except (ValueError, TypeError):
                        pass
            
            # Iteriere über alle Zeilen und aktualisiere "fertiggestellte PM"
            for idx, row in df_sorted.iterrows():
                date_str = row.get('Datum', '')
                if date_str:
                    try:
                        from datetime import datetime, timedelta
                        row_date = datetime.strptime(date_str, MasterData.DATE_FORMAT).date()
                        
                        # Finde vorherigen Arbeitstag
                        prev_date = row_date - timedelta(days=1)
                        prev_workday_found = False
                        
                        # Suche rückwärts nach dem letzten Arbeitstag (maximal 7 Tage)
                        search_date = prev_date
                        for _ in range(7):
                            if search_date < date(planning_year, 1, 1):
                                break
                            
                            # Prüfe ob dieses Datum im DataFrame existiert
                            if search_date in date_to_idx:
                                prev_idx = date_to_idx[search_date]
                                prev_row = df_sorted.iloc[prev_idx]
                                
                                # Prüfe ob es ein Arbeitstag war (Schichtanzahl > 0)
                                prev_shifts = prev_row.get('Schichtanzahl', 0)
                                if prev_shifts > 0:  # Arbeitstag
                                    # Hole "tatsächliche PM" vom vorherigen Arbeitstag (bereits dynamisch aktualisiert)
                                    prev_actual_pm = prev_row.get('tatsächliche PM', 0)
                                    # Überschreibe "fertiggestellte PM" mit diesem Wert
                                    df_sorted.at[idx, 'fertiggestellte PM'] = int(round(prev_actual_pm)) if prev_actual_pm > 0 else 0
                                    prev_workday_found = True
                                    break
                            
                            search_date -= timedelta(days=1)
                        
                        # Wenn kein vorheriger Arbeitstag gefunden, setze "fertiggestellte PM" auf 0
                        if not prev_workday_found:
                            df_sorted.at[idx, 'fertiggestellte PM'] = 0
                    except (ValueError, TypeError) as e:
                        # Bei Fehler: Behalte ursprünglichen Wert
                        pass
            
            # Entferne temporäre Spalte und aktualisiere production_logs
            if '_date_parsed' in df_sorted.columns:
                df_sorted = df_sorted.drop(columns=['_date_parsed'])
            production_logs[product] = df_sorted
    
    # VIERTE RUNDE: Aktualisiere Backlog dynamisch (NACH Aktualisierung aller "fertiggestellte PM")
    # WICHTIG: Backlog = geplante PM (mit Marketing) - fertiggestellte PM + Backlog vom Vortag
    # Das stellt sicher, dass der Backlog konsistent mit der neuen "fertiggestellten PM" ist
    if daily_demands_actual:
        for product, df in production_logs.items():
            if df.empty or 'Datum' not in df.columns or 'fertiggestellte PM' not in df.columns or 'geplante PM' not in df.columns or 'Backlog' not in df.columns:
                continue
            
            # Sortiere DataFrame nach Datum (wichtig für korrekte Reihenfolge)
            df_sorted = df.copy()
            df_sorted['_date_parsed'] = pd.to_datetime(df_sorted['Datum'], format=MasterData.DATE_FORMAT)
            df_sorted = df_sorted.sort_values('_date_parsed').reset_index(drop=True)
            
            # Iteriere über alle Zeilen und aktualisiere Backlog
            for idx, row in df_sorted.iterrows():
                date_str = row.get('Datum', '')
                if date_str:
                    try:
                        from datetime import datetime, timedelta
                        row_date = datetime.strptime(date_str, MasterData.DATE_FORMAT).date()
                        day = (row_date - date(planning_year, 1, 1)).days
                        
                        if day in daily_demands_actual:
                            # Geplante PM (mit Marketing) = Nachfrage aus daily_demands_actual
                            product_demands = daily_demands_actual[day]
                            planned_pm = product_demands.get(product, 0)
                            
                            # Fertiggestellte PM (bereits dynamisch aktualisiert)
                            finished_pm = row.get('fertiggestellte PM', 0)
                            try:
                                finished_pm = int(finished_pm) if finished_pm > 0 else 0
                            except (ValueError, TypeError):
                                finished_pm = 0
                            
                            # Backlog vom Vortag
                            prev_backlog = 0.0
                            if idx > 0:
                                # Verwende Backlog vom vorherigen Tag (bereits aktualisiert)
                                prev_row = df_sorted.iloc[idx - 1]
                                prev_backlog = prev_row.get('Backlog', 0)
                                try:
                                    prev_backlog = float(prev_backlog) if prev_backlog > 0 else 0.0
                                except (ValueError, TypeError):
                                    prev_backlog = 0.0
                            # else: Erster Tag im DataFrame - Backlog vom Vortag ist 0 (kein vorheriger Tag)
                            
                            # Neuer Backlog = geplante PM - fertiggestellte PM + Backlog vom Vortag
                            new_backlog = max(0.0, planned_pm - finished_pm + prev_backlog)
                            df_sorted.at[idx, 'Backlog'] = int(round(new_backlog))
                            
                            # Aktualisiere auch "geplante PM" mit Marketing-Wert (falls unterschiedlich)
                            current_planned_pm = row.get('geplante PM', 0)
                            try:
                                current_planned_pm = int(current_planned_pm) if current_planned_pm > 0 else 0
                            except (ValueError, TypeError):
                                current_planned_pm = 0
                            
                            if planned_pm != current_planned_pm:
                                df_sorted.at[idx, 'geplante PM'] = int(planned_pm)
                    except (ValueError, TypeError) as e:
                        # Bei Fehler: Behalte ursprünglichen Wert
                        pass
            
            # Entferne temporäre Spalte und aktualisiere production_logs
            if '_date_parsed' in df_sorted.columns:
                df_sorted = df_sorted.drop(columns=['_date_parsed'])
            production_logs[product] = df_sorted
    
    # Cache Ergebnis
    st.session_state.production_logs_cache = production_logs
    st.session_state.production_logs_cache_key = cache_key
    
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
    
    # Styling-Funktion
    def style_row_safe(row):
        idx = row.name
        if idx < len(weekend_flags):
            if weekend_flags[idx]:
                return ['background-color: #ffebee'] * len(row)
            if holiday_flags[idx]:
                return ['background-color: #c8e6c9'] * len(row)
        return [''] * len(row)
    
    # Identifiziere numerische Spalten für Summenzeile
    numeric_cols = []
    for col in df_display.columns:
        if col not in ['Wochentag', 'Datum', 'Materialien vollständig?']:
            # Prüfe, ob Spalte numerische Werte enthält
            try:
                pd.to_numeric(df_display[col].replace('', 0), errors='coerce').sum()
                numeric_cols.append(col)
            except:
                pass
    
    # Erstelle Summenzeile
    if numeric_cols and len(df_display) > 0:
        sum_row = {'Wochentag': 'Summe', 'Datum': ''}
        for col in df_display.columns:
            if col in numeric_cols:
                # Für Auslastung: Durchschnitt statt Summe
                if col == 'Auslastung (%)':
                    # Konvertiere String-Werte zurück zu Float für Berechnung
                    numeric_values = df_display[col].apply(
                        lambda x: float(x) if isinstance(x, str) and x.strip() != '' else (float(x) if pd.notna(x) else 0)
                    )
                    avg_utilization = numeric_values.mean()
                    sum_row[col] = f"{avg_utilization:.2f}" if pd.notna(avg_utilization) else ""
                else:
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
