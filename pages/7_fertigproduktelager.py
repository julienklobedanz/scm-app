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

st.set_page_config(page_title="Fertigproduktelager - Supply Chain Simulation", layout="wide", page_icon="✅")

# Szenarien-Sidebar rendern
render_scenario_sidebar()

# Initialisiere Session State falls nicht vorhanden
if 'scenario_manager' not in st.session_state:
    st.session_state.scenario_manager = ScenarioManager()
if 'results_df' not in st.session_state:
    st.session_state.results_df = None
if 'kpis' not in st.session_state:
    st.session_state.kpis = None
if 'happy_path_run' not in st.session_state:
    st.session_state.happy_path_run = False
if 'yearly_volume' not in st.session_state:
    st.session_state.yearly_volume = 370000

st.title("✅ Fertigproduktelager")
st.markdown("Übersicht über Fertigproduktbestände nach Produkten")

# Happy Path: Automatische Simulation wenn noch keine Ergebnisse vorhanden
if not st.session_state.happy_path_run and st.session_state.results_df is None:
    try:
        with st.spinner("🔄 Happy Path Simulation wird ausgeführt..."):
            vol = st.session_state.get('yearly_volume', 370000)
            simulator = Simulator(
                yearly_volume=vol,
                initial_stock_frames_alu=MasterData.DEFAULT_INITIAL_STOCK['frames_alu'],
                initial_stock_frames_carbon=MasterData.DEFAULT_INITIAL_STOCK['frames_carbon'],
                initial_stock_saddles=MasterData.DEFAULT_INITIAL_STOCK['saddles'],
                scenario_manager=st.session_state.scenario_manager
            )
            results_df, kpis = simulator.run()
            st.session_state.results_df = results_df
            st.session_state.kpis = kpis
            # Speichere auch den Simulator für Zugriff auf ChinaTransportManager
            st.session_state.simulator = simulator
            st.session_state.happy_path_run = True
            st.rerun()
    except Exception as e:
        st.error(f"❌ Fehler bei der Simulation: {str(e)}")
        st.exception(e)
        st.session_state.happy_path_run = True

if st.session_state.results_df is None:
    st.warning("⚠️ Keine Simulationsergebnisse verfügbar.")
    st.stop()

results_df = st.session_state.results_df

# Zeitraum
start_date = date(2027, 1, 1)
end_date = date(2027, 12, 31)
workday_calc = WorkdayCalculator(year=2027)

def create_finished_goods_log():
    """Erstellt Fertigproduktelager-Log für jedes Produkt"""
    fg_logs = {product: [] for product in MasterData.BOM.keys()}
    
    for day in range(365):
        current_date = workday_calc.get_date_from_day(day)
        weekday_name = workday_calc.get_weekday_name(day)
        is_workday = workday_calc.is_workday(day)
        is_holiday = not is_workday and weekday_name not in ['Samstag', 'Sonntag']
        is_weekend = weekday_name in ['Samstag', 'Sonntag']
        
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
            
            fg_logs[product].append({
                'Datum': current_date.strftime('%d.%m.%Y'),
                'Wochentag': weekday_name,
                'Lagerzugang': round(total_receipt, 1),
                'Bestand (morgens)': round(stock_morning, 1),
                'Lagerabgang': round(total_dispatch, 1),
                'Bestand (abends)': round(stock_evening, 1),
                'Is_Weekend_Or_Holiday': is_weekend or is_holiday
            })
    
    return {product: pd.DataFrame(log) for product, log in fg_logs.items()}

# Erstelle Fertigproduktelager-Log
with st.spinner("🔄 Berechne Fertigproduktelager..."):
    fg_logs = create_finished_goods_log()

# Zeit-Filter
date_range_fg = st.date_input(
    "Zeitraum",
    value=(start_date, end_date),
    min_value=start_date,
    max_value=end_date,
    key="fg_date_range"
)

# Zeige Tabelle für jedes Produkt
for product in sorted(fg_logs.keys()):
    st.subheader(f"📋 {product}")
    
    df_fg = fg_logs[product]
    
    # Filtere nach Zeitraum
    df_fg_filtered = df_fg[
        (pd.to_datetime(df_fg['Datum'], format='%d.%m.%Y') >= pd.to_datetime(date_range_fg[0])) &
        (pd.to_datetime(df_fg['Datum'], format='%d.%m.%Y') <= pd.to_datetime(date_range_fg[1]))
    ]
    
    # Speichere Is_Weekend_Or_Holiday Flag vor Entfernen
    weekend_holiday_flags = df_fg_filtered['Is_Weekend_Or_Holiday'].copy()
    
    # Definiere Spaltenreihenfolge (ohne Is_Weekend_Or_Holiday)
    column_order = [
        'Datum',
        'Wochentag',
        'Lagerzugang',
        'Bestand (morgens)',
        'Lagerabgang',
        'Bestand (abends)'
    ]
    df_display = df_fg_filtered[column_order].copy()
    
    # Zeige Tabelle mit Styling
    styled_df = df_display.style.apply(
        lambda row: ['background-color: #ffebee' if weekend_holiday_flags.iloc[row.name] else '' for _ in row],
        axis=1
    )
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # Chart: Bestand über Zeit für dieses Produkt
    st.write("**Bestand über Zeit**")
    fig_stock = go.Figure()
    
    # Bestand abends über Zeit
    fig_stock.add_trace(go.Scatter(
        x=pd.to_datetime(df_fg_filtered['Datum'], format='%d.%m.%Y'),
        y=df_fg_filtered['Bestand (abends)'],
        name='Bestand (abends)',
        mode='lines',
        line=dict(color='#1f77b4', width=2),
        fill='tozeroy'
    ))
    
    fig_stock.update_layout(
        xaxis_title="Datum",
        yaxis_title="Bestand (Einheiten)",
        height=300,
        hovermode='x unified',
        showlegend=True
    )
    st.plotly_chart(fig_stock, use_container_width=True, key=f"fg_stock_{product}")
    
    st.divider()

