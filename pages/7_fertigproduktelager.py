"""
Fertigproduktelager - Seite
Zeigt Fertigproduktbestände nach Produkten
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

st.set_page_config(page_title="Fertigproduktelager", layout="wide", page_icon="✅")

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
render_scenario_sidebar(key_suffix="_fertigproduktelager")

# Initialisiere Session State
initialize_session_state()

# WICHTIG: Stelle sicher, dass alle abhängigen Daten aktualisiert sind
# 1. Volumenplanung (Basis für Produktion)
from ui.volume_planning_utils import calculate_volume_planning_demand
calculate_volume_planning_demand()

# 2. Produktionslogs (enthält fertiggestellte PM, reagiert auf Marketing)
from ui.production_calculations import calculate_production_logs
try:
    production_logs_cache = calculate_production_logs()
except Exception as e:
    st.error(f"⚠️ Fehler bei Berechnung der Produktionslogs: {str(e)}")
    st.exception(e)
    production_logs_cache = {}

st.title("✅ Fertigproduktelager")
st.markdown("Übersicht über Fertigproduktbestände nach Produkten")

# Happy Path: Automatische Simulation wenn noch keine Ergebnisse vorhanden
run_happy_path_simulation()

if st.session_state.results_df is None:
    st.warning("⚠️ Keine Simulationsergebnisse verfügbar.")
    st.stop()

# Zeitraum
planning_year = st.session_state.get('planning_year', 2027)
start_date = date(planning_year, 1, 1)
end_date = date(planning_year, 12, 31)
workday_calc = WorkdayCalculator(year=planning_year)

def create_finished_goods_log():
    """Erstellt Fertigproduktelager-Log für jedes Produkt"""
    fg_logs = {product: [] for product in MasterData.BOM.keys()}
    
    # Kumulativer Bestand pro Produkt
    stock_by_product = {product: 0.0 for product in MasterData.BOM.keys()}
    
    # Prüfe ob production_logs_cache verfügbar ist
    if not production_logs_cache:
        # Fallback: Verwende results_df (statisch)
        results_df = st.session_state.results_df
        for day in range(365):
            current_date = workday_calc.get_date_from_day(day)
            weekday = current_date.weekday()
            weekday_name = workday_calc.get_weekday_name(day)
            is_weekend = weekday >= 5
            is_workday = workday_calc.is_workday(day)
            is_holiday = not is_workday and not is_weekend
            
            if day < len(results_df):
                actual_build = results_df.iloc[day]['Actual_Build']
            else:
                actual_build = 0
            
            for product in MasterData.BOM.keys():
                product_share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)
                production_qty = actual_build * product_share
                
                total_receipt = 0
                total_dispatch = 0
                
                for market_code, market_params in MasterData.MARKETS.items():
                    market_share = market_params['share']
                    receipt = production_qty * market_share
                    dispatch = receipt
                    total_receipt += receipt
                    total_dispatch += dispatch
                
                stock_morning = stock_by_product[product]
                stock_evening = stock_morning + total_receipt - total_dispatch
                stock_by_product[product] = max(0.0, stock_evening)
                
                weekday_abbr = weekday_name[:2]
                
                fg_logs[product].append({
                    'Wochentag': weekday_abbr,
                    'Datum': current_date.strftime(MasterData.DATE_FORMAT),
                    'Lagerzugang': int(round(total_receipt)),
                    'Bestand (morgens)': int(round(stock_morning)),
                    'Lagerabgang': int(round(total_dispatch)),
                    'Bestand (abends)': int(round(stock_evening)),
                    'Is_Weekend': is_weekend,
                    'Is_Holiday': is_holiday
                })
    else:
        # NEU: Verwende fertiggestellte PM aus production_logs_cache (dynamisch, reagiert auf Marketing)
        for day in range(365):
            current_date = workday_calc.get_date_from_day(day)
            weekday = current_date.weekday()
            weekday_name = workday_calc.get_weekday_name(day)
            is_weekend = weekday >= 5
            is_workday = workday_calc.is_workday(day)
            is_holiday = not is_workday and not is_weekend
            
            # Für jedes Produkt
            for product in MasterData.BOM.keys():
                # Hole fertiggestellte PM aus production_logs_cache
                finished_pm = 0.0
                if product in production_logs_cache and not production_logs_cache[product].empty:
                    df_prod = production_logs_cache[product]
                    # Finde Zeile für diesen Tag
                    date_str = current_date.strftime(MasterData.DATE_FORMAT)
                    matching_rows = df_prod[df_prod['Datum'] == date_str]
                    if not matching_rows.empty:
                        finished_pm = matching_rows.iloc[0].get('fertiggestellte PM', 0.0)
                        try:
                            finished_pm = float(finished_pm) if finished_pm > 0 else 0.0
                        except (ValueError, TypeError):
                            finished_pm = 0.0
                    
                    # KRITISCH: Am letzten Tag des Jahres (31.12.2027) addiere auch die tatsächliche PM
                    # Die tatsächliche PM vom letzten Tag wird nicht als fertiggestellte PM am nächsten Tag berücksichtigt
                    # weil es keinen nächsten Tag gibt. Daher müssen wir sie hier explizit addieren.
                    if day == 364:  # Letzter Tag des Jahres
                        last_date_str = date(planning_year, 12, 31).strftime(MasterData.DATE_FORMAT)
                        last_row = df_prod[df_prod['Datum'] == last_date_str]
                        if not last_row.empty:
                            last_actual_pm = last_row.iloc[0].get('tatsächliche PM', 0.0)
                            try:
                                last_actual_pm = float(last_actual_pm) if last_actual_pm > 0 else 0.0
                                finished_pm += last_actual_pm
                            except (ValueError, TypeError):
                                pass
                
                # Lagerzugang = fertiggestellte PM (pro Produkt)
                total_receipt = finished_pm
                
                # Lagerabgang = Verteilung auf Märkte
                total_dispatch = 0.0
                for market_code, market_params in MasterData.MARKETS.items():
                    market_share = market_params['share']
                    dispatch = finished_pm * market_share
                    total_dispatch += dispatch
                
                # Bestand (kumulativ)
                stock_morning = stock_by_product[product]
                stock_evening = stock_morning + total_receipt - total_dispatch
                stock_by_product[product] = max(0.0, stock_evening)
                
                weekday_abbr = weekday_name[:2]
                
                fg_logs[product].append({
                    'Wochentag': weekday_abbr,
                    'Datum': current_date.strftime(MasterData.DATE_FORMAT),
                    'Lagerzugang': int(round(total_receipt)),
                    'Bestand (morgens)': int(round(stock_morning)),
                    'Lagerabgang': int(round(total_dispatch)),
                    'Bestand (abends)': int(round(stock_evening)),
                    'Is_Weekend': is_weekend,
                    'Is_Holiday': is_holiday
                })
    
    return {product: pd.DataFrame(log) for product, log in fg_logs.items()}

# Erstelle Fertigproduktelager-Log
with st.spinner("🔄 Berechne Fertigproduktelager..."):
    fg_logs = create_finished_goods_log()

# Zeige Tabelle für jedes Produkt
for product in sorted(fg_logs.keys()):
    st.subheader(f"📋 {product}")
    
    df_fg = fg_logs[product]
    
    # Filtere auf den Standard-Zeitraum (2027)
    df_fg_filtered = df_fg[
        (pd.to_datetime(df_fg['Datum'], format='%d.%m.%Y') >= pd.to_datetime(start_date)) &
        (pd.to_datetime(df_fg['Datum'], format='%d.%m.%Y') <= pd.to_datetime(end_date))
    ]
    
    # Speichere Flags für Wochenende und Feiertage
    weekend_flags = df_fg_filtered['Is_Weekend'].values
    holiday_flags = df_fg_filtered['Is_Holiday'].values
    
    # Definiere Spaltenreihenfolge (Wochentag vor Datum)
    column_order = [
        'Wochentag',
        'Datum',
        'Lagerzugang',
        'Bestand (morgens)',
        'Lagerabgang',
        'Bestand (abends)'
    ]
    df_display = df_fg_filtered[column_order].copy()
    
    # Farblegende oben rechts
    col1, col2 = st.columns([1, 1])
    with col2:
        st.markdown("""
        <div style="text-align: right; margin-bottom: 10px;">
            <span style="background-color: #ffcccc; padding: 2px 8px; border-radius: 3px; margin-left: 5px;">Wochenende</span>
            <span style="background-color: #c8e6c9; padding: 2px 8px; border-radius: 3px; margin-left: 5px;">Feiertag</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Identifiziere numerische Spalten für Summenzeile
    numeric_cols = ['Lagerzugang', 'Bestand (morgens)', 'Lagerabgang', 'Bestand (abends)']
    
    # Erstelle Summenzeile
    if numeric_cols and len(df_display) > 0:
        sum_row = {'Wochentag': 'Summe', 'Datum': ''}
        for col in df_display.columns:
            if col in numeric_cols:
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
    
    # Zeige Tabelle mit Styling
    def style_row(row):
        row_idx = row.name
        # Summenzeile: grauer Hintergrund, fett
        if row_idx >= len(weekend_flags):
            return ['background-color: #e0e0e0; font-weight: bold' for _ in row]
        # Normale Zeilen
        if row_idx < len(weekend_flags_extended):
            # Wochenende hat Priorität (wenn beides, dann Wochenende = rot)
            if weekend_flags_extended[row_idx]:
                return ['background-color: #ffcccc' for _ in row]
            elif holiday_flags_extended[row_idx]:
                return ['background-color: #c8e6c9' for _ in row]
        return [''] * len(row)
    
    styled_df = df_display_with_sum.style.apply(style_row, axis=1)
    st.dataframe(styled_df, width='stretch', hide_index=True)
    
    st.divider()

