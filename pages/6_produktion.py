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

col_title_prod, col_help_prod = st.columns([20, 1])
with col_title_prod:
    st.title("🏭 Produktion")
    st.markdown("Übersicht über Produktionsplanung, tatsächliche Produktion und Materialverfügbarkeit")
with col_help_prod:
    st.markdown("""
    <div style="margin-top: 1.5rem;">
        <span title="Produktions-Berechnung (Ranking-Logik): 
1. Bedarf = Tagesnachfrage + Backlog (nicht produzierte Mengen von vorherigen Tagen)
2. Proportionalität: Jedes Produkt erhält anteilig Kapazität basierend auf Bedarf
   Anteil = (Bedarf Produkt / Gesamtbedarf) × Tageskapazität
3. Ranking: Produkte werden nach (Reihenfolge / 1.000.000 + proportionaler Anteil) sortiert
   Dies entscheidet die Produktionsreihenfolge bei Kapazitätsengpässen
4. Tatsächliche Produktion = min(geplante Produktion, verfügbares Material)
   Materialverfügbarkeit begrenzt die Produktion
5. Backlog = Bedarf - tatsächliche Produktion (wird auf nächsten Tag übertragen)
Die Produktion reagiert auf Marketing-Szenarien (erhöhte Nachfrage) und Materialverfügbarkeit." 
        style="cursor: help; color: #6b7280; font-size: 1.2rem; display: inline-block;">ℹ️</span>
    </div>
    """, unsafe_allow_html=True)

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

# NEU: Materialverbrauch-Analyse pro Datum
st.markdown("---")
st.subheader("📊 Materialverbrauch-Analyse")
st.markdown("<style>div[data-testid='stDataFrame'] { margin-bottom: 0.1rem !important; }</style>", unsafe_allow_html=True)

col_date, col_info = st.columns([2, 3])
with col_date:
    selected_date = st.date_input(
        "📅 Datum auswählen:",
        value=date(planning_year, 1, 1),
        min_value=date(planning_year, 1, 1),
        max_value=date(planning_year, 12, 31),
        key="material_consumption_date"
    )

# Prüfe ob Datum ein Arbeitstag ist
# Berechne Tag-Index: Differenz zwischen selected_date und 1. Januar des Planungsjahres
start_date = date(planning_year, 1, 1)
day_index = (selected_date - start_date).days
is_workday = workday_calc.is_workday(day_index) if 0 <= day_index < 365 else False

if selected_date:
    from ui.production_calculations import get_material_consumption_by_date
    
    try:
        consumption_df = get_material_consumption_by_date(
            selected_date, production_logs, planning_year
        )
        
        if not consumption_df.empty:
            # Gruppiere nach Material-Typ
            material_types = sorted(consumption_df['Material-Typ'].unique())
            
            # CSS für kompakte Tabellen-Abstände
            st.markdown("""
            <style>
            /* Reduziere Abstände zwischen DataFrames drastisch */
            div[data-testid="stDataFrame"] {
                margin-top: 0 !important;
                margin-bottom: 0.1rem !important;
            }
            /* Reduziere Abstände nach Überschriften */
            h3 {
                margin-top: 0.2rem !important;
                margin-bottom: 0.1rem !important;
            }
            /* Reduziere Abstände nach HR */
            hr {
                margin: 0.05rem 0 !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            for idx, saddle_type in enumerate(material_types):
                saddle_df = consumption_df[consumption_df['Material-Typ'] == saddle_type].copy()
                
                # Dünne Trennlinie mit sehr minimalem Abstand (nur zwischen Material-Typen)
                if idx > 0:
                    st.markdown("<hr style='margin: 0.05rem 0 !important; border: none; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)
                
                # Überschrift mit minimalem Abstand
                st.markdown(f"<h3 style='margin-top: 0.2rem !important; margin-bottom: 0.1rem !important;'>{saddle_type}</h3>", unsafe_allow_html=True)
                
                # Erstelle Anzeige-Tabelle
                display_cols = ['Produkt', 'Geplante PM', 'Tatsächliche PM', 'Materialverbrauch', 'Abweichung']
                if 'Materialverfügbarkeit' in saddle_df.columns and saddle_df['Materialverfügbarkeit'].notna().any():
                    display_cols.append('Materialverfügbarkeit')
                
                display_df = saddle_df[display_cols].copy()
                
                # Berechne Summen für Summenzeile
                total_consumption = saddle_df['Materialverbrauch'].sum()
                total_planned = saddle_df['Geplante PM'].sum()
                total_actual = saddle_df['Tatsächliche PM'].sum()
                total_deviation = total_actual - total_planned
                
                # Erstelle Summenzeile
                sum_row = {'Produkt': '**Summe**'}
                sum_row['Geplante PM'] = int(total_planned)
                sum_row['Tatsächliche PM'] = int(total_actual)
                sum_row['Materialverbrauch'] = int(total_consumption)
                sum_row['Abweichung'] = int(total_deviation)
                if 'Materialverfügbarkeit' in display_cols:
                    # Summe der Materialverfügbarkeit (falls verfügbar)
                    if saddle_df['Materialverfügbarkeit'].notna().any():
                        sum_row['Materialverfügbarkeit'] = int(saddle_df['Materialverfügbarkeit'].sum())
                    else:
                        sum_row['Materialverfügbarkeit'] = None
                
                # Füge Summenzeile zum DataFrame hinzu
                sum_df = pd.DataFrame([sum_row])
                display_df_with_sum = pd.concat([display_df, sum_df], ignore_index=True)
                
                # Zeige kompakte Tabelle mit Styling für Summenzeile
                styled_df = display_df_with_sum.style.apply(
                    lambda row: ['font-weight: bold; background-color: #f0f0f0' if row.name == len(display_df_with_sum) - 1 else '' for _ in row],
                    axis=1
                )
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True
                )
        else:
            if is_workday:
                st.info(f"ℹ️ Am {selected_date.strftime('%d.%m.%Y')} wurde kein Material verbraucht.")
            else:
                st.info(f"ℹ️ Am {selected_date.strftime('%d.%m.%Y')} ist kein Arbeitstag - keine Produktion.")
                
    except Exception as e:
        st.error(f"⚠️ Fehler bei Materialverbrauch-Analyse: {str(e)}")
        # Debug-Info (kann später entfernt werden)
        if st.session_state.get('debug_mode', False):
            st.exception(e)

st.markdown("---")

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
    
    # Speichere Flags für Wochenende, Feiertage und Nicht-Arbeitstage (DAILY_WORKLOAD = 0.0)
    weekend_flags = df_prod_filtered['Is_Weekend'].values
    holiday_flags = df_prod_filtered['Is_Holiday'].values
    workday_flags = df_prod_filtered['Is_Workday'].values if 'Is_Workday' in df_prod_filtered.columns else None
    # Nicht-Arbeitstage: Tage die nicht Wochenende sind, aber auch kein Arbeitstag (DAILY_WORKLOAD = 0.0)
    non_workday_flags = None
    if workday_flags is not None:
        non_workday_flags = ~workday_flags & ~weekend_flags
    
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
            <span style="background-color: #ffcccc; padding: 2px 8px; border-radius: 3px; margin-left: 5px;">Wochenende</span>
            <span style="background-color: #c8e6c9; padding: 2px 8px; border-radius: 3px; margin-left: 5px;">Feiertag / Kein Arbeitstag</span>
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
        non_workday_flags_extended = list(non_workday_flags) + [False] if non_workday_flags is not None else None
    else:
        df_display_with_sum = df_display
        weekend_flags_extended = weekend_flags
        holiday_flags_extended = holiday_flags
        non_workday_flags_extended = non_workday_flags
    
    # Theme-aware Styling verwenden
    from ui.theme_aware_styling import style_row_with_theme
    
    # Styling-Funktion mit Summenzeile (theme-aware)
    def style_row_with_sum(row):
        idx = row.name
        # Summenzeile: grauer Hintergrund, fett
        if idx >= len(weekend_flags):
            return ['background-color: #e0e0e0; font-weight: bold'] * len(row)
        # Normale Zeilen
        if idx < len(weekend_flags_extended):
            if weekend_flags_extended[idx]:
                return ['background-color: #ffcccc'] * len(row)
            if holiday_flags_extended[idx]:
                return ['background-color: #c8e6c9'] * len(row)
            # Nicht-Arbeitstage (DAILY_WORKLOAD = 0.0) - grün wie Feiertage
            if non_workday_flags_extended is not None and idx < len(non_workday_flags_extended) and non_workday_flags_extended[idx]:
                return ['background-color: #c8e6c9'] * len(row)
        return [''] * len(row)
    
    # Zeige Tabelle
    from ui.theme_aware_styling import apply_theme_to_styled_dataframe
    styled_df = df_display_with_sum.style.apply(style_row_with_sum, axis=1)
    # KRITISCH: Wende Theme-Styling auf Header an (mit Fehlerbehandlung)
    try:
        styled_df = apply_theme_to_styled_dataframe(styled_df)
    except Exception:
        pass  # Bei Fehler: Verwende Styler ohne Header-Styling
    st.dataframe(styled_df, width='stretch', hide_index=True)
    
    st.divider()
