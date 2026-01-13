"""
Reporting-Seite
Übersicht über Lagerbestände und Produktionsleistung
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

st.set_page_config(page_title="Reporting - Supply Chain Simulation", layout="wide", page_icon="📊")

# Szenarien-Sidebar rendern
render_scenario_sidebar()

# Initialisiere Session State
initialize_session_state()

st.title("📊 Reporting")
st.markdown("Übersicht über Lagerbestände und Produktionsleistung")

# Happy Path: Automatische Simulation wenn noch keine Ergebnisse vorhanden
run_happy_path_simulation()

if st.session_state.results_df is None:
    st.warning("⚠️ Keine Simulationsergebnisse verfügbar.")
    st.stop()

results_df = st.session_state.results_df
workday_calc = WorkdayCalculator(year=2026)

# ============================================================================
# LAGER
# ============================================================================
st.header("📦 Lager")

# Berechne Sattel-Bestände (aus Materiallager-Logik)
def get_saddle_inventory_data():
    """Holt Sattel-Bestandsdaten aus dem Materiallager"""
    # Prüfe zuerst, ob die Daten bereits berechnet wurden
    if 'material_inventory_data' in st.session_state:
        return st.session_state.material_inventory_data
    
    # Wenn nicht vorhanden, berechne sie jetzt
    if 'simulator' in st.session_state and st.session_state.simulator:
        # Importiere die Funktion direkt
        import importlib
        import pages.materiallager as materiallager_module
        
        # Rufe die Funktion auf, die material_inventory_data setzt
        materiallager_module.create_saddle_inventory_log()
        if 'material_inventory_data' in st.session_state:
            return st.session_state.material_inventory_data
    
    return {}

# Berechne Fahrrad-Bestände (kumulativ)
def get_bicycle_inventory_data():
    """Berechnet Fahrrad-Bestandsdaten kumulativ"""
    bicycle_inventory = {}
    stock_by_product = {product: 0.0 for product in MasterData.BOM.keys()}
    
    for day in range(365):
        current_date = workday_calc.get_date_from_day(day)
        bicycle_inventory[current_date] = {}
        
        # Produktion und Versand
        if day < len(results_df):
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
                    receipt = production_qty * market_share
                    dispatch = receipt  # Sofort versendet (Just-in-Time)
                    total_receipt += receipt
                    total_dispatch += dispatch
                
                # Kumulativer Bestand
                stock_by_product[product] = stock_by_product[product] + total_receipt - total_dispatch
                stock_by_product[product] = max(0.0, stock_by_product[product])  # Kein negativer Bestand
                bicycle_inventory[current_date][product] = stock_by_product[product]
    
    return bicycle_inventory

# Lade Daten
saddle_inventory_data = get_saddle_inventory_data()
bicycle_inventory_data = get_bicycle_inventory_data()

# Bestände Sättel
st.subheader("Bestände Sättel")

if saddle_inventory_data:
    fig_saddles = go.Figure()
    
    # Alle Satteltypen sammeln
    all_saddles = set()
    for date_data in saddle_inventory_data.values():
        all_saddles.update(date_data.keys())
    
    # Farben für Sättel
    saddle_colors = {
        'Fizik Tundra': '#2ca02c',
        'Raceline': '#9467bd',
        'Spark': '#1f77b4',
        'Speedline': '#d62728'
    }
    
    for saddle in sorted(all_saddles):
        dates = []
        stocks = []
        for date_key in sorted(saddle_inventory_data.keys()):
            dates.append(date_key)
            stocks.append(saddle_inventory_data[date_key].get(saddle, 0.0))
        
        fig_saddles.add_trace(go.Scatter(
            x=dates,
            y=stocks,
            name=saddle,
            line=dict(color=saddle_colors.get(saddle, '#808080'), width=2),
            mode='lines'
        ))
    
    fig_saddles.update_layout(
        xaxis_title="Datum",
        yaxis_title="Bestand (Einheiten)",
        height=400,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_saddles, use_container_width=True)
else:
    st.info("Keine Sattel-Bestandsdaten verfügbar.")

# Bestände Fahrräder
st.subheader("Bestände Fahrräder")

if bicycle_inventory_data:
    fig_bicycles = go.Figure()
    
    # Farben für Fahrräder
    bicycle_colors = {
        'MTB Allrounder': '#2ca02c',
        'MTB Competition': '#9467bd',
        'MTB Downhill': '#1f77b4',
        'MTB Extreme': '#d62728',
        'MTB Freeride': '#ff7f0e',
        'MTB Marathon': '#8c564b',
        'MTB Performance': '#e377c2',
        'MTB Trail': '#7f7f7f'
    }
    
    for product in sorted(MasterData.BOM.keys()):
        dates = []
        stocks = []
        for date_key in sorted(bicycle_inventory_data.keys()):
            dates.append(date_key)
            stocks.append(bicycle_inventory_data[date_key].get(product, 0.0))
        
        fig_bicycles.add_trace(go.Scatter(
            x=dates,
            y=stocks,
            name=product,
            line=dict(color=bicycle_colors.get(product, '#808080'), width=2),
            mode='lines'
        ))
    
    fig_bicycles.update_layout(
        xaxis_title="Datum",
        yaxis_title="Bestand (Einheiten)",
        height=400,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_bicycles, use_container_width=True)
else:
    st.info("Keine Fahrrad-Bestandsdaten verfügbar.")

st.divider()

# ============================================================================
# PRODUKTION
# ============================================================================
st.header("🏭 Produktion")

# Hole Produktionslogs aus dem ProductionPlanner
def get_production_logs():
    """Liest Produktionslogs direkt aus dem ProductionPlanner"""
    if 'simulator' not in st.session_state or st.session_state.simulator is None:
        return {}
    
    planner = st.session_state.simulator.production_planner
    
    if not hasattr(planner, 'production_logs') or not planner.production_logs:
        return {}
    
    return planner.production_logs

production_logs = get_production_logs()

if not production_logs:
    st.warning("⚠️ Keine Produktionslogs verfügbar.")
    st.stop()

# Gesamtübersicht Produktion
st.subheader("Gesamtübersicht")

# Berechne Gesamt-Backlog und Gesamt-Über-/Unterproduktion
total_backlog_data = []
total_deviation_data = []

for day in range(365):
    current_date = workday_calc.get_date_from_day(day)
    
    # Gesamt-Backlog (Summe aller Produkte)
    total_backlog = 0.0
    total_planned = 0.0
    total_actual = 0.0
    
    for product, logs in production_logs.items():
        if logs and day < len(logs):
            log_entry = logs[day]
            total_backlog += log_entry.get('Backlog', 0.0)
            total_planned += log_entry.get('geplante PM', 0.0)
            total_actual += log_entry.get('tatsächliche PM', 0.0)
    
    total_backlog_data.append({
        'date': current_date,
        'backlog': total_backlog
    })
    
    total_deviation_data.append({
        'date': current_date,
        'deviation': total_actual - total_planned
    })

col1, col2 = st.columns(2)

with col1:
    st.write("**Backlog**")
    fig_total_backlog = go.Figure()
    fig_total_backlog.add_trace(go.Scatter(
        x=[d['date'] for d in total_backlog_data],
        y=[d['backlog'] for d in total_backlog_data],
        name='Backlog',
        line=dict(color='#d62728', width=2),
        mode='lines'
    ))
    fig_total_backlog.update_layout(
        xaxis_title="Datum",
        yaxis_title="Backlog (Einheiten)",
        height=350,
        hovermode='x unified'
    )
    st.plotly_chart(fig_total_backlog, use_container_width=True)

with col2:
    st.write("**Über-/Unterproduktion**")
    fig_total_deviation = go.Figure()
    
    deviations = [d['deviation'] for d in total_deviation_data]
    colors = ['#2ca02c' if x >= 0 else '#d62728' for x in deviations]
    
    fig_total_deviation.add_trace(go.Bar(
        x=[d['date'] for d in total_deviation_data],
        y=deviations,
        name='Über-/Unterproduktion',
        marker_color=colors
    ))
    fig_total_deviation.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig_total_deviation.update_layout(
        xaxis_title="Datum",
        yaxis_title="Abweichung (Ist - Soll)",
        height=350,
        hovermode='x unified',
        showlegend=False
    )
    st.plotly_chart(fig_total_deviation, use_container_width=True)

st.divider()

# Produktion einzelner Fahrräder
st.subheader("Produktion einzelner Fahrräder")

for product in sorted(production_logs.keys()):
    if not production_logs[product]:
        continue
    
    st.write(f"**{product}**")
    
    # Bereite Daten vor
    backlog_data = []
    deviation_data = []
    
    for day in range(min(365, len(production_logs[product]))):
        current_date = workday_calc.get_date_from_day(day)
        log_entry = production_logs[product][day]
        
        backlog_data.append({
            'date': current_date,
            'backlog': log_entry.get('Backlog', 0.0)
        })
        
        planned = log_entry.get('geplante PM', 0.0)
        actual = log_entry.get('tatsächliche PM', 0.0)
        deviation_data.append({
            'date': current_date,
            'deviation': actual - planned
        })
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_product_backlog = go.Figure()
        fig_product_backlog.add_trace(go.Scatter(
            x=[d['date'] for d in backlog_data],
            y=[d['backlog'] for d in backlog_data],
            name='Backlog',
            line=dict(color='#d62728', width=2),
            mode='lines'
        ))
        fig_product_backlog.update_layout(
            xaxis_title="Datum",
            yaxis_title="Backlog (Einheiten)",
            height=350,
            hovermode='x unified'
        )
        st.plotly_chart(fig_product_backlog, use_container_width=True)
    
    with col2:
        fig_product_deviation = go.Figure()
        
        deviations = [d['deviation'] for d in deviation_data]
        colors = ['#2ca02c' if x >= 0 else '#d62728' for x in deviations]
        
        fig_product_deviation.add_trace(go.Bar(
            x=[d['date'] for d in deviation_data],
            y=deviations,
            name='Über-/Unterproduktion',
            marker_color=colors
        ))
        fig_product_deviation.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig_product_deviation.update_layout(
            xaxis_title="Datum",
            yaxis_title="Abweichung (Ist - Soll)",
            height=350,
            hovermode='x unified',
            showlegend=False
        )
        st.plotly_chart(fig_product_deviation, use_container_width=True)
    
    st.divider()
