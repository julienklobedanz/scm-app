"""
Materiallager - Seite
Zeigt Sattelzugänge, Bestände und Verluste
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

st.set_page_config(page_title="Materiallager - Supply Chain Simulation", layout="wide", page_icon="📦")

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

st.title("📦 Materiallager")
st.markdown("Übersicht über Sattelzugänge, Bestände und Verluste")

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

def calculate_saddle_shares():
    """Berechnet die Anteile jedes Sattel-Typs basierend auf BOM und Produktanteilen"""
    saddle_totals = {}
    total_volume = 0.0
    
    for product, product_share in MasterData.PRODUCT_SALES_SHARES.items():
        saddle_type = MasterData.BOM[product]['saddle']
        if saddle_type not in saddle_totals:
            saddle_totals[saddle_type] = 0.0
        saddle_totals[saddle_type] += product_share
        total_volume += product_share
    
    # Normalisiere zu Anteilen
    saddle_shares = {}
    for saddle_type, volume in saddle_totals.items():
        saddle_shares[saddle_type] = volume / total_volume if total_volume > 0 else 0.0
    
    return saddle_shares

def create_saddle_inventory_log():
    """Erstellt Sattel-Lager-Log für jeden Sattel-Typ"""
    saddle_shares = calculate_saddle_shares()
    saddle_types = list(saddle_shares.keys())
    
    saddle_logs = {saddle_type: [] for saddle_type in saddle_types}
    
    for day in range(365):
        current_date = workday_calc.get_date_from_day(day)
        
        # Stock-Änderungen berechnen
        if day == 0:
            stock_saddles_morning = MasterData.DEFAULT_INITIAL_STOCK['saddles']
            receipt_saddles = 0
        else:
            stock_saddles_morning = results_df.iloc[day-1]['Stock_Saddles']
            # Berechne Zugänge (Stock-Erhöhung)
            receipt_saddles = max(0, results_df.iloc[day]['Stock_Saddles'] - stock_saddles_morning)
        
        stock_saddles_evening = results_df.iloc[day]['Stock_Saddles']
        
        # Berechne Abgänge (Verbrauch)
        issue_saddles = stock_saddles_morning + receipt_saddles - stock_saddles_evening
        
        # Wochentag und Feiertag
        weekday_name = workday_calc.get_weekday_name(day)
        is_workday = workday_calc.is_workday(day)
        is_holiday = not is_workday and weekday_name not in ['Samstag', 'Sonntag']
        is_weekend = weekday_name in ['Samstag', 'Sonntag']
        
        # Für jeden Sattel-Typ
        for saddle_type in saddle_types:
            share = saddle_shares[saddle_type]
            
            saddle_logs[saddle_type].append({
                'Datum': current_date.strftime('%d.%m.%Y'),
                'Wochentag': weekday_name,
                'Lagerzugang': round(receipt_saddles * share, 1),
                'Bestand morgens': round(stock_saddles_morning * share, 1),
                'Lagerabgang': round(issue_saddles * share, 1),
                'Verlustmenge': 0,
                'Bestand abends': round(stock_saddles_evening * share, 1),
                'Is_Weekend_Or_Holiday': is_weekend or is_holiday
            })
    
    return {saddle_type: pd.DataFrame(log) for saddle_type, log in saddle_logs.items()}

# Erstelle Sattel-Lager-Log
with st.spinner("🔄 Berechne Materiallager..."):
    saddle_logs = create_saddle_inventory_log()

# Zeit-Filter
date_range = st.date_input(
    "Zeitraum",
    value=(start_date, end_date),
    min_value=start_date,
    max_value=end_date
)

# Zeige Tabelle für jeden Sattel-Typ
for saddle_type in sorted(saddle_logs.keys()):
    st.subheader(f"📋 {saddle_type}")
    
    df_saddle = saddle_logs[saddle_type]
    
    # Filtere nach Zeitraum
    df_saddle_filtered = df_saddle[
        (pd.to_datetime(df_saddle['Datum'], format='%d.%m.%Y') >= pd.to_datetime(date_range[0])) &
        (pd.to_datetime(df_saddle['Datum'], format='%d.%m.%Y') <= pd.to_datetime(date_range[1]))
    ]
    
    # Speichere Is_Weekend_Or_Holiday Flag vor Entfernen
    weekend_holiday_flags = df_saddle_filtered['Is_Weekend_Or_Holiday'].copy()
    
    # Definiere Spaltenreihenfolge (ohne Is_Weekend_Or_Holiday)
    column_order = [
        'Datum',
        'Wochentag',
        'Lagerzugang',
        'Bestand morgens',
        'Lagerabgang',
        'Verlustmenge',
        'Bestand abends'
    ]
    df_display = df_saddle_filtered[column_order].copy()
    
    # Zeige Tabelle mit Styling
    styled_df = df_display.style.apply(
        lambda row: ['background-color: #ffebee' if weekend_holiday_flags.iloc[row.name] else '' for _ in row],
        axis=1
    )
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    st.divider()

# Charts für alle Sättel
st.subheader("📊 Übersicht")

st.write("**Bestand über Zeit**")
fig_stock = go.Figure()
for saddle_type in sorted(saddle_logs.keys()):
    df_saddle = saddle_logs[saddle_type]
    df_saddle_filtered = df_saddle[
        (pd.to_datetime(df_saddle['Datum'], format='%d.%m.%Y') >= pd.to_datetime(date_range[0])) &
        (pd.to_datetime(df_saddle['Datum'], format='%d.%m.%Y') <= pd.to_datetime(date_range[1]))
    ]
    fig_stock.add_trace(go.Scatter(
        x=pd.to_datetime(df_saddle_filtered['Datum'], format='%d.%m.%Y'),
        y=df_saddle_filtered['Bestand abends'],
        name=saddle_type,
        mode='lines',
        fill='tozeroy'
    ))
fig_stock.update_layout(
    xaxis_title="Datum",
    yaxis_title="Bestand abends",
    height=400,
    hovermode='x unified'
)
st.plotly_chart(fig_stock, use_container_width=True)

