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

st.set_page_config(page_title="Fertigproduktelager - Supply Chain Simulation", layout="wide", page_icon="✅")

# Szenarien-Sidebar rendern
render_scenario_sidebar()

# Initialisiere Session State
initialize_session_state()

st.title("✅ Fertigproduktelager")
st.markdown("Übersicht über Fertigproduktbestände nach Produkten")

# Happy Path: Automatische Simulation wenn noch keine Ergebnisse vorhanden
run_happy_path_simulation()

if st.session_state.results_df is None:
    st.warning("⚠️ Keine Simulationsergebnisse verfügbar.")
    st.stop()

results_df = st.session_state.results_df

# Zeitraum
start_date = date(2026, 1, 1)
end_date = date(2026, 12, 31)
workday_calc = WorkdayCalculator(year=2026)

def create_finished_goods_log():
    """Erstellt Fertigproduktelager-Log für jedes Produkt"""
    fg_logs = {product: [] for product in MasterData.BOM.keys()}
    
    for day in range(365):
        current_date = workday_calc.get_date_from_day(day)
        day_info = workday_calc.get_day_info(day)
        weekday_name = day_info['weekday_name']
        is_workday = day_info['is_workday']
        is_holiday = day_info['is_holiday']
        is_weekend = day_info['is_weekend']
        
        # Produktion und Versand
        actual_build = results_df.iloc[day]['Actual_Build']
        
        # Für jedes Produkt
        for product in MasterData.BOM.keys():
            product_share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)
            production_qty = actual_build * product_share
            
            # Aggregiere über alle Länder
            total_receipt = 0
            total_dispatch = 0
            
            for market_code, market_params in MasterData.MARKETS.items():
                market_share = market_params['share']
                
                # Vereinfacht: FGI = 0 (Just-in-Time), aber wir tracken Zugang/Abgang
                receipt = production_qty * market_share
                dispatch = receipt  # Sofort versendet (Just-in-Time)
                
                total_receipt += receipt
                total_dispatch += dispatch
            
            # Bestand morgens (vereinfacht: 0, da Just-in-Time)
            stock_morning = 0
            stock_evening = 0
            
            # Wochentag-Abkürzung
            weekday_abbr = weekday_name[:2]  # Mo, Di, Mi, etc.
            
            fg_logs[product].append({
                'Wochentag': weekday_abbr,
                'Datum': current_date.strftime(MasterData.DATE_FORMAT),
                'Lagerzugang': round(total_receipt, 1),
                'Bestand (morgens)': round(stock_morning, 1),
                'Lagerabgang': round(total_dispatch, 1),
                'Bestand (abends)': round(stock_evening, 1),
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
    
    # Filtere auf den Standard-Zeitraum (2026)
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
            <span style="background-color: #ffebee; padding: 2px 8px; border-radius: 3px; margin-left: 5px;">Wochenende</span>
            <span style="background-color: #c8e6c9; padding: 2px 8px; border-radius: 3px; margin-left: 5px;">Feiertag</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Zeige Tabelle mit Styling
    def style_row(row):
        row_idx = row.name
        # Wochenende hat Priorität (wenn beides, dann Wochenende = rot)
        if weekend_flags[row_idx]:
            return ['background-color: #ffebee' for _ in row]
        elif holiday_flags[row_idx]:
            return ['background-color: #c8e6c9' for _ in row]
        return [''] * len(row)
    
    styled_df = df_display.style.apply(style_row, axis=1)
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    st.divider()

