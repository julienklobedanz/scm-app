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

st.set_page_config(page_title="Reporting", layout="wide", page_icon="📊")

# CSS für Menü-Formatierung (Großbuchstaben und Fett)
st.markdown("""
<style>
    /* Menüeinträge großgeschrieben und fett */
    [data-testid="stSidebarNav"] a {
        font-weight: bold !important;
        text-transform: capitalize !important;
    }
</style>
""", unsafe_allow_html=True)

# Szenarien-Sidebar rendern (mit eindeutigem Key-Suffix)
render_scenario_sidebar(key_suffix="_reporting")

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
planning_year = st.session_state.get('planning_year', 2027)
workday_calc = WorkdayCalculator(year=planning_year)

# ============================================================================
# LAGER
# ============================================================================
st.header("📦 Lager")

# Berechne Sattel-Bestände (aus Materiallager-Logik)
def get_saddle_inventory_data():
    """Holt Sattel-Bestandsdaten aus dem Materiallager"""
    # OPTIMIERUNG: Prüfe zuerst, ob die Daten bereits berechnet wurden
    if 'material_inventory_data' in st.session_state and st.session_state.material_inventory_data:
        return st.session_state.material_inventory_data
    
    # Wenn nicht vorhanden, versuche aus Cache zu laden (von Materiallager-Seite)
    if 'saddle_logs_cache' in st.session_state:
        # Materiallager wurde bereits berechnet, aber material_inventory_data fehlt
        # Das sollte nicht passieren, aber als Fallback:
        return {}
    
    # Wenn nicht vorhanden, berechne sie jetzt (nur wenn wirklich nötig)
    if 'simulator' in st.session_state and st.session_state.simulator:
        # Importiere die Funktion direkt (Dateiname ist 5_materiallager.py)
        import importlib.util
        import os
        
        try:
            # Lade Modul über Dateipfad (wegen Zahl im Namen)
            module_path = os.path.join(os.path.dirname(__file__), "5_materiallager.py")
            spec = importlib.util.spec_from_file_location("materiallager_module_reporting", module_path)
            if spec and spec.loader:
                materiallager_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(materiallager_module)
                # OPTIMIERUNG: Nur berechnen wenn nicht bereits gecacht
                if 'material_inventory_data' not in st.session_state:
                    materiallager_module.create_saddle_inventory_log()
                if 'material_inventory_data' in st.session_state:
                    return st.session_state.material_inventory_data
        except Exception as e:
            # Stille Fehlerbehandlung - Daten werden später geladen
            pass
    
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
    st.plotly_chart(fig_saddles, width='stretch', key='chart_saddles')
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
    st.plotly_chart(fig_bicycles, width='stretch', key='chart_bicycles')
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
# OPTIMIERUNG: Cache für Datum-Berechnungen
total_backlog_data = []
total_deviation_data = []

# OPTIMIERUNG: Berechne alle Daten auf einmal (nur einmal get_date_from_day pro Tag)
date_cache = {day: workday_calc.get_date_from_day(day) for day in range(365)}

for day in range(365):
    current_date = date_cache[day]
    
    # Gesamt-Backlog (Summe aller Produkte)
    total_backlog = 0.0
    total_planned = 0.0
    total_actual = 0.0
    
    # OPTIMIERUNG: Direkter Zugriff statt get() wenn möglich
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
    st.plotly_chart(fig_total_backlog, width='stretch', key='chart_total_backlog')

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
    st.plotly_chart(fig_total_deviation, width='stretch', key='chart_total_deviation')

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
    
    # OPTIMIERUNG: Cache für Datum-Berechnungen
    max_day = min(365, len(production_logs[product]))
    date_cache = {day: workday_calc.get_date_from_day(day) for day in range(max_day)}
    
    for day in range(max_day):
        current_date = date_cache[day]
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
        st.plotly_chart(fig_product_backlog, width='stretch', key=f'chart_product_backlog_{product}')
    
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
        st.plotly_chart(fig_product_deviation, width='stretch', key=f'chart_product_deviation_{product}')
    
    st.divider()
    
    # ============================================================================
    # VOLUMENPLANUNG
    # ============================================================================
    st.header("📅 Volumenplanung")
    
    # Lade Volumenplanungsdaten
    from ui.volume_planning_utils import calculate_volume_planning_demand
    from datetime import timedelta
    import math
    
    # Berechne Daten falls nicht vorhanden
    if not st.session_state.get('volume_planning_calculated', False):
        calculate_volume_planning_demand()
    
    daily_demands_planned = st.session_state.get('daily_demands_planned', {})
    daily_demands_actual = st.session_state.get('daily_demands_actual', {})
    
    if daily_demands_planned and daily_demands_actual:
        # Wöchentliche Planung
        st.subheader("Wöchentliche Volumenplanung")
        
        # Berechne wöchentliche Daten
        start_date = date(planning_year, 1, 1)
        end_date = date(planning_year, 12, 31)
        
        # Berechne letzte KW
        last_week = 52
        if end_date.isocalendar()[1] > 52:
            last_week = end_date.isocalendar()[1]
        
        weekly_data = []
        
        for week_num in range(1, last_week + 1):
            jan_1 = date(planning_year, 1, 1)
            jan_1_weekday = jan_1.weekday()
            
            # KW 1 beginnt am 01.01. (oder nächster Montag)
            if week_num == 1:
                if jan_1_weekday == 0:
                    week_start = jan_1
                else:
                    days_to_monday = (7 - jan_1_weekday) % 7
                    if days_to_monday == 0:
                        days_to_monday = 7
                    week_start = jan_1 + timedelta(days=days_to_monday)
            else:
                if jan_1_weekday <= 3:
                    first_monday = jan_1 - timedelta(days=jan_1_weekday)
                else:
                    first_monday = jan_1 + timedelta(days=7 - jan_1_weekday)
                week_start = first_monday + timedelta(weeks=week_num - 1)
            
            week_demand_actual = {product: 0.0 for product in MasterData.BOM.keys()}
            daily_demands_for_shifts = []
            
            for day_offset in range(7):
                current_date = week_start + timedelta(days=day_offset)
                if current_date.year == planning_year:
                    day_of_year = (current_date - start_date).days
                    if 0 <= day_of_year < 365:
                        day_actual = daily_demands_actual.get(day_of_year, {})
                        for product in MasterData.BOM.keys():
                            week_demand_actual[product] += day_actual.get(product, 0)
                        
                        if workday_calc.is_workday(day_of_year):
                            total_day = sum(day_actual.get(p, 0) for p in MasterData.BOM.keys())
                            daily_demands_for_shifts.append(total_day)
            
            # Berechne Schichten
            HOURS_PER_SHIFT = 8
            CAPACITY_PER_HOUR = MasterData.GLOBAL_CONFIG['capacity_per_hour']
            CAPACITY_PER_SHIFT = HOURS_PER_SHIFT * CAPACITY_PER_HOUR
            
            total_week_demand = sum(week_demand_actual.values())
            if total_week_demand > 0 and daily_demands_for_shifts:
                required_shifts_float = max(daily_demands_for_shifts) / CAPACITY_PER_SHIFT
                required_shifts_int = math.ceil(required_shifts_float)
                shifts = max(1, min(3, required_shifts_int))
            else:
                shifts = 0
            
            weekly_data.append({
                'Kalenderwoche': week_num,
                'Schichten': shifts,
                **{f'{product}_tatsächlich': week_demand_actual[product] for product in MasterData.BOM.keys()}
            })
        
        weekly_df = pd.DataFrame(weekly_data)
        
        # Visualisierung der Schichten
        st.write("**Schichten-Visualisierung**")
        fig_shifts = go.Figure()
        fig_shifts.add_trace(go.Bar(
            x=weekly_df['Kalenderwoche'],
            y=weekly_df['Schichten'],
            name='Schichten',
            marker_color='#1f77b4',
            text=weekly_df['Schichten'],
            textposition='auto'
        ))
        fig_shifts.update_layout(
            xaxis_title="Kalenderwoche",
            yaxis_title="Anzahl Schichten",
            height=300,
            yaxis=dict(range=[0, 4], tickmode='linear', tick0=0, dtick=1)
        )
        st.plotly_chart(fig_shifts, width='stretch', key='chart_shifts')
        
        # Fahrrad-Vergleich über Kalenderwochen
        st.write("**Fahrrad-Vergleich über Kalenderwochen**")
        fig_products = go.Figure()
        
        product_colors = {
            'MTB Allrounder': '#1f77b4',
            'MTB Competition': '#ff7f0e',
            'MTB Downhill': '#2ca02c',
            'MTB Extreme': '#d62728',
            'MTB Freeride': '#9467bd',
            'MTB Marathon': '#8c564b',
            'MTB Performance': '#e377c2',
            'MTB Trail': '#7f7f7f'
        }
        
        for product in MasterData.BOM.keys():
            fig_products.add_trace(go.Scatter(
                x=weekly_df['Kalenderwoche'],
                y=weekly_df[f'{product}_tatsächlich'],
                name=product,
                mode='lines+markers',
                line=dict(color=product_colors.get(product, '#1f77b4'), width=2),
                marker=dict(size=4)
            ))
        
        fig_products.update_layout(
            xaxis_title="Kalenderwoche",
            yaxis_title="Nachfrage (Einheiten)",
            height=400,
            hovermode='x unified',
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            )
        )
        st.plotly_chart(fig_products, width='stretch', key='chart_products')
        
        # Fahrrad-Vergleich (Gestapelt)
        st.write("**Fahrrad-Vergleich (Gestapelt)**")
        fig_stacked = go.Figure()
        
        for product in MasterData.BOM.keys():
            fig_stacked.add_trace(go.Bar(
                x=weekly_df['Kalenderwoche'],
                y=weekly_df[f'{product}_tatsächlich'],
                name=product,
                marker_color=product_colors.get(product, '#1f77b4')
            ))
        
        fig_stacked.update_layout(
            xaxis_title="Kalenderwoche",
            yaxis_title="Nachfrage (Einheiten)",
            height=400,
            barmode='stack',
            hovermode='x unified',
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            )
        )
        st.plotly_chart(fig_stacked, width='stretch', key='chart_stacked')
        
        # Tägliche Planung
        st.subheader("Tägliche Volumenplanung")
        
        # Berechne tägliche Daten
        # OPTIMIERUNG: Cache für Datum-Berechnungen
        date_cache = {day: workday_calc.get_date_from_day(day) for day in range(365)}
        
        daily_data = []
        for day in range(365):
            current_date = date_cache[day]
            day_actual = daily_demands_actual.get(day, {})
            
            daily_row = {
                'Datum': current_date,
                **{f'{product}_tatsächlich': day_actual.get(product, 0) for product in MasterData.BOM.keys()}
            }
            daily_data.append(daily_row)
        
        daily_df = pd.DataFrame(daily_data)
        
        # Tägliche Entwicklung (Gestapeltes Balkendiagramm)
        st.write("**Tägliche Entwicklung (Tatsächlicher Bedarf)**")
        fig_daily = go.Figure()
        
        x_axis = pd.to_datetime(daily_df['Datum'])
        
        for product in MasterData.BOM.keys():
            fig_daily.add_trace(go.Bar(
                x=x_axis,
                y=daily_df[f'{product}_tatsächlich'],
                name=product,
                marker_color=product_colors.get(product, '#1f77b4')
            ))
        
        fig_daily.update_layout(
            xaxis_title="Datum",
            yaxis_title="Volumen (Einheiten)",
            height=400,
            barmode='stack',
            hovermode='x unified',
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            )
        )
        st.plotly_chart(fig_daily, width='stretch', key='chart_daily')
    
    st.divider()