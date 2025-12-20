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

st.set_page_config(page_title="Produktion - Supply Chain Simulation", layout="wide", page_icon="🏭")

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

st.title("🏭 Produktion")
st.markdown("Übersicht über Produktionsplanung, tatsächliche Produktion und Materialverfügbarkeit")

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

def create_production_log():
    """Erstellt Produktions-Log für jedes Produkt"""
    production_logs = {product: [] for product in MasterData.BOM.keys()}
    saddle_shares = calculate_saddle_shares()
    
    for day in range(365):
        current_date = workday_calc.get_date_from_day(day)
        weekday_name = workday_calc.get_weekday_name(day)
        is_workday = workday_calc.is_workday(day)
        is_holiday = not is_workday and weekday_name not in ['Samstag', 'Sonntag']
        is_weekend = weekday_name in ['Samstag', 'Sonntag']
        
        # Schichtanzahl und Auslastung
        daily_target = results_df.iloc[day]['Daily_Target']
        actual_build = results_df.iloc[day]['Actual_Build']
        
        # Berechne Schichtanzahl (vereinfacht)
        capacity_per_shift = MasterData.GLOBAL_CONFIG['working_hours_per_shift'] * MasterData.GLOBAL_CONFIG['capacity_per_hour']
        if is_workday and daily_target > 0:
            shifts = min(3, max(1, int((daily_target / capacity_per_shift) + 0.5)))
            utilization = (actual_build / (shifts * capacity_per_shift) * 100) if shifts > 0 else 0
        else:
            shifts = 0
            utilization = 0
        
        # Für jedes Produkt
        for product in MasterData.BOM.keys():
            # Berechne produkt-spezifische Nachfrage
            product_share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)
            planned_qty = daily_target * product_share
            actual_qty = actual_build * product_share
            
            # Backlog (vereinfacht: Differenz zwischen Plan und Ist)
            backlog = max(0, planned_qty - actual_qty)
            
            # Materialien vollständig?
            # WICHTIG: Rahmen sind unbegrenzt verfügbar, daher nur Sättel prüfen
            if day == 0:
                stock_saddles = MasterData.DEFAULT_INITIAL_STOCK['saddles']
            else:
                stock_saddles = results_df.iloc[day-1]['Stock_Saddles']
            
            materials_complete = 'Ja' if stock_saddles >= planned_qty else 'Nein'
            
            # Konkrete Einzelteil-Namen und Bestände
            frame_name = MasterData.BOM[product]['frame']
            saddle_name = MasterData.BOM[product]['saddle']
            fork_name = MasterData.BOM[product]['fork']
            
            # Berechne Sattel-Bestand basierend auf Anteil
            saddle_share = saddle_shares.get(saddle_name, 0.0)
            stock_saddle_specific = stock_saddles * saddle_share if saddle_share > 0 else 0
            
            # Erstelle Dictionary mit dynamischen Spalten
            log_entry = {
                'Datum': current_date.strftime('%d.%m.%Y'),
                'Wochentag': weekday_name,
                'Schichtanzahl': shifts,
                'Auslastung (%)': round(utilization, 1),
                'Materialien vollständig?': materials_complete,
                frame_name: '∞',  # Rahmen sind unbegrenzt verfügbar
                saddle_name: round(stock_saddle_specific, 1),  # Sattel-Bestand
                fork_name: '∞',  # Gabeln sind unbegrenzt verfügbar
                'geplante PM': round(planned_qty, 1),
                'tatsächliche PM': round(actual_qty, 1),
                'Backlog': round(backlog, 1),
                'Is_Weekend_Or_Holiday': is_weekend or is_holiday
            }
            
            production_logs[product].append(log_entry)
    
    return {product: pd.DataFrame(log) for product, log in production_logs.items()}

# Erstelle Produktions-Log
with st.spinner("🔄 Berechne Produktion..."):
    production_logs = create_production_log()

# Zeit-Filter
date_range_prod = st.date_input(
    "Zeitraum",
    value=(start_date, end_date),
    min_value=start_date,
    max_value=end_date,
    key="prod_date_range"
)

# Zeige Tabelle für jedes Produkt
for product in sorted(production_logs.keys()):
    st.subheader(f"📋 {product}")
    
    df_prod = production_logs[product]
    
    # Filtere nach Zeitraum
    df_prod_filtered = df_prod[
        (pd.to_datetime(df_prod['Datum'], format='%d.%m.%Y') >= pd.to_datetime(date_range_prod[0])) &
        (pd.to_datetime(df_prod['Datum'], format='%d.%m.%Y') <= pd.to_datetime(date_range_prod[1]))
    ]
    
    # Speichere Is_Weekend_Or_Holiday Flag vor Entfernen
    weekend_holiday_flags = df_prod_filtered['Is_Weekend_Or_Holiday'].copy()
    
    # Hole konkrete Einzelteil-Namen für dieses Produkt
    frame_name = MasterData.BOM[product]['frame']
    saddle_name = MasterData.BOM[product]['saddle']
    fork_name = MasterData.BOM[product]['fork']
    
    # Definiere Spaltenreihenfolge (ohne Is_Weekend_Or_Holiday)
    # Einzelteile direkt nach "Auslastung (%)"
    column_order = [
        'Datum',
        'Wochentag',
        'Schichtanzahl',
        'Auslastung (%)',
        frame_name,  # Konkreter Rahmen-Name
        saddle_name,  # Konkreter Sattel-Name
        fork_name,  # Konkrete Gabel-Name
        'Materialien vollständig?',
        'geplante PM',
        'tatsächliche PM',
        'Backlog'
    ]
    df_display = df_prod_filtered[column_order].copy()
    
    # Zeige Tabelle mit Styling
    styled_df = df_display.style.apply(
        lambda row: ['background-color: #ffebee' if weekend_holiday_flags.iloc[row.name] else '' for _ in row],
        axis=1
    )
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    st.divider()

# Charts
st.subheader("📊 Übersicht")

# Produktfilter für Charts
selected_products_chart = st.multiselect(
    "Produkte für Charts auswählen",
    sorted(production_logs.keys()),
    default=sorted(production_logs.keys())[:4],
    key="chart_products"
)

# Chart 1: Geplante vs. Tatsächliche Produktion (breit)
st.write("**Geplante vs. Tatsächliche Produktion**")
fig_prod_comp = go.Figure()
for product in selected_products_chart:
    df_prod = production_logs[product]
    df_prod_filtered = df_prod[
        (pd.to_datetime(df_prod['Datum'], format='%d.%m.%Y') >= pd.to_datetime(date_range_prod[0])) &
        (pd.to_datetime(df_prod['Datum'], format='%d.%m.%Y') <= pd.to_datetime(date_range_prod[1]))
    ]
    fig_prod_comp.add_trace(go.Scatter(
        x=pd.to_datetime(df_prod_filtered['Datum'], format='%d.%m.%Y'),
        y=df_prod_filtered['geplante PM'],
        name=f'{product} (geplant)',
        mode='lines',
        line=dict(dash='dash')
    ))
    fig_prod_comp.add_trace(go.Scatter(
        x=pd.to_datetime(df_prod_filtered['Datum'], format='%d.%m.%Y'),
        y=df_prod_filtered['tatsächliche PM'],
        name=f'{product} (tatsächlich)',
        mode='lines'
    ))
fig_prod_comp.update_layout(
    xaxis_title="Datum",
    yaxis_title="Produktionsmenge",
    height=400,
    hovermode='x unified'
)
st.plotly_chart(fig_prod_comp, use_container_width=True)

# Chart 2: Backlog-Entwicklung mit Moving Average pro KW
st.write("**Backlog-Entwicklung (Moving Average pro Kalenderwoche)**")

# Berechne Moving Average pro KW für jedes Produkt
fig_backlog = go.Figure()
for product in selected_products_chart:
    df_prod = production_logs[product]
    df_prod_filtered = df_prod[
        (pd.to_datetime(df_prod['Datum'], format='%d.%m.%Y') >= pd.to_datetime(date_range_prod[0])) &
        (pd.to_datetime(df_prod['Datum'], format='%d.%m.%Y') <= pd.to_datetime(date_range_prod[1]))
    ].copy()
    
    # Konvertiere Datum
    df_prod_filtered['Date'] = pd.to_datetime(df_prod_filtered['Datum'], format='%d.%m.%Y')
    df_prod_filtered['Kalenderwoche'] = df_prod_filtered['Date'].dt.isocalendar().week
    
    # Aggregiere auf Wochenbasis
    df_weekly = df_prod_filtered.groupby('Kalenderwoche').agg({
        'Backlog': 'mean'
    }).reset_index()
    
    # Berechne Moving Average (7-Tage = 1 Woche)
    df_weekly['Backlog_MA'] = df_weekly['Backlog'].rolling(window=2, center=True).mean()
    
    fig_backlog.add_trace(go.Scatter(
        x=df_weekly['Kalenderwoche'],
        y=df_weekly['Backlog_MA'],
        name=product,
        mode='lines+markers',
        line=dict(width=2)
    ))

fig_backlog.update_layout(
    xaxis_title="Kalenderwoche",
    yaxis_title="Backlog (Moving Average)",
    height=400,
    hovermode='x unified'
)
st.plotly_chart(fig_backlog, use_container_width=True)

