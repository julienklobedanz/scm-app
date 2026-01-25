"""
Reporting-Seite
Übersicht über Lagerbestände und Produktionsleistung
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta
import math
from config.master_data import MasterData
from simulation.simulator import Simulator
from models.scenarios import ScenarioManager
from simulation.workday_calculator import WorkdayCalculator
from ui.scenario_sidebar import render_scenario_sidebar
from ui.utils import initialize_session_state, run_happy_path_simulation
from ui.volume_planning_utils import calculate_volume_planning_demand

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
# HILFSFUNKTIONEN
# ============================================================================

def get_saddle_inventory_data():
    """Holt Sattel-Bestandsdaten aus dem Materiallager"""
    if 'material_inventory_data' in st.session_state and st.session_state.material_inventory_data:
        return st.session_state.material_inventory_data
    
    if 'saddle_logs_cache' in st.session_state:
        return {}
    
    if 'simulator' in st.session_state and st.session_state.simulator:
        import importlib.util
        import os
        
        try:
            module_path = os.path.join(os.path.dirname(__file__), "5_materiallager.py")
            spec = importlib.util.spec_from_file_location("materiallager_module_reporting", module_path)
            if spec and spec.loader:
                materiallager_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(materiallager_module)
                if 'material_inventory_data' not in st.session_state:
                    materiallager_module.create_saddle_inventory_log()
                if 'material_inventory_data' in st.session_state:
                    return st.session_state.material_inventory_data
        except Exception as e:
            pass
    
    return {}

def get_bicycle_inventory_data():
    """Berechnet Fahrrad-Bestandsdaten kumulativ"""
    bicycle_inventory = {}
    stock_by_product = {product: 0.0 for product in MasterData.BOM.keys()}
    
    for day in range(365):
        current_date = workday_calc.get_date_from_day(day)
        bicycle_inventory[current_date] = {}
        
        if day < len(results_df):
            actual_build = results_df.iloc[day]['Actual_Build']
            
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
                
                stock_by_product[product] = stock_by_product[product] + total_receipt - total_dispatch
                stock_by_product[product] = max(0.0, stock_by_product[product])
                bicycle_inventory[current_date][product] = stock_by_product[product]
    
    return bicycle_inventory

def get_production_logs():
    """Liest Produktionslogs direkt aus dem ProductionPlanner"""
    if 'simulator' not in st.session_state or st.session_state.simulator is None:
        return {}
    
    planner = st.session_state.simulator.production_planner
    
    if not hasattr(planner, 'production_logs') or not planner.production_logs:
        return {}
    
    return planner.production_logs

# ============================================================================
# TABS
# ============================================================================

tab1, tab2, tab3 = st.tabs(["📅 Volumenplanung", "📦 Material", "🏭 Produktion"])

# ============================================================================
# TAB 1: VOLUMENPLANUNG
# ============================================================================

with tab1:
    # Lade Volumenplanungsdaten
    if not st.session_state.get('volume_planning_calculated', False):
        calculate_volume_planning_demand()
    
    daily_demands_planned = st.session_state.get('daily_demands_planned', {})
    daily_demands_actual = st.session_state.get('daily_demands_actual', {})
    
    if daily_demands_planned and daily_demands_actual:
        # KPI-Dashboard Volumenplanung
        st.header("📊 KPI-Dashboard Volumenplanung")
        
        # Berechne KPIs
        total_planned_demand = sum(sum(day_demand.values()) for day_demand in daily_demands_planned.values())
        total_actual_demand = sum(sum(day_demand.values()) for day_demand in daily_demands_actual.values())
        demand_variance = total_actual_demand - total_planned_demand
        demand_variance_pct = (demand_variance / total_planned_demand * 100) if total_planned_demand > 0 else 0.0
        
        # KPI-Kacheln
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="Geplante Gesamtnachfrage",
                value=f"{int(round(total_planned_demand)):,}".replace(",", "."),
                help="Summe aller geplanten Nachfragen im Zeitraum"
            )
        
        with col2:
            st.metric(
                label="Tatsächliche Gesamtnachfrage",
                value=f"{int(round(total_actual_demand)):,}".replace(",", "."),
                help="Summe aller tatsächlichen Nachfragen im Zeitraum (mit Marketing)"
            )
        
        with col3:
            variance_color = "normal" if abs(demand_variance_pct) < 5 else ("normal" if abs(demand_variance_pct) < 10 else "inverse")
            st.metric(
                label="Nachfrage-Abweichung",
                value=f"{int(round(demand_variance)):,}".replace(",", "."),
                delta=f"{demand_variance_pct:.2f}%",
                delta_color=variance_color,
                help="Differenz zwischen tatsächlicher und geplanter Nachfrage"
            )
        
        st.divider()
        
        # Wöchentliche Planung
        st.subheader("Wöchentliche Volumenplanung")
        
        # Berechne wöchentliche Daten
        start_date = date(planning_year, 1, 1)
        end_date = date(planning_year, 12, 31)
        
        last_week = 52
        if end_date.isocalendar()[1] > 52:
            last_week = end_date.isocalendar()[1]
        
        weekly_data = []
        
        for week_num in range(1, last_week + 1):
            jan_1 = date(planning_year, 1, 1)
            jan_1_weekday = jan_1.weekday()
            
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
        
        # Schichten-Visualisierung
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
    else:
        st.info("Keine Volumenplanungsdaten verfügbar.")

# ============================================================================
# TAB 2: MATERIAL
# ============================================================================

with tab2:
    st.header("📦 KPI-Dashboard Materiallager")
    
    # Hole Materiallager-Daten
    saddle_inventory_data = get_saddle_inventory_data()
    
    if saddle_inventory_data:
        # Berechne KPIs für jedes Material (Satteltyp)
        saddle_types = sorted(set(saddle for date_data in saddle_inventory_data.values() for saddle in date_data.keys()))
        
        # Filtere auf das Planungsjahr
        planning_year_dates = {d: data for d, data in saddle_inventory_data.items() if d.year == planning_year}
        
        if planning_year_dates:
            # Berechne KPIs pro Satteltyp
            kpi_data_by_saddle = {}
            total_days = len(planning_year_dates)
            
            for saddle_type in saddle_types:
                stocks = []
                days_with_zero = 0
                consumption_per_day = []
                previous_stock = None
                
                for date_key in sorted(planning_year_dates.keys()):
                    stock = planning_year_dates[date_key].get(saddle_type, 0.0)
                    stocks.append(stock)
                    
                    if stock == 0:
                        days_with_zero += 1
                    
                    if previous_stock is not None and stock < previous_stock:
                        consumption = previous_stock - stock
                        consumption_per_day.append(consumption)
                    previous_stock = stock
                
                # KPIs berechnen
                avg_stock = sum(stocks) / len(stocks) if stocks else 0.0
                min_stock = min(stocks) if stocks else 0.0
                max_stock = max(stocks) if stocks else 0.0
                avg_daily_consumption = sum(consumption_per_day) / len(consumption_per_day) if consumption_per_day else 0.0
                avg_days_of_supply = (avg_stock / avg_daily_consumption) if avg_daily_consumption > 0 else 0.0
                
                kpi_data_by_saddle[saddle_type] = {
                    'avg_stock': avg_stock,
                    'min_stock': min_stock,
                    'max_stock': max_stock,
                    'days_with_zero': days_with_zero,
                    'avg_daily_consumption': avg_daily_consumption,
                    'avg_days_of_supply': avg_days_of_supply
                }
            
            # Gesamt-KPIs
            total_avg_stock = sum(kpi['avg_stock'] for kpi in kpi_data_by_saddle.values())
            total_min_stock = min(kpi['min_stock'] for kpi in kpi_data_by_saddle.values()) if kpi_data_by_saddle else 0.0
            total_max_stock = sum(kpi['max_stock'] for kpi in kpi_data_by_saddle.values())
            total_days_with_zero = 0
            days_with_any_zero = 0
            
            for date_key in sorted(planning_year_dates.keys()):
                has_any_zero = False
                for saddle_type in saddle_types:
                    stock = planning_year_dates[date_key].get(saddle_type, 0.0)
                    if stock == 0:
                        total_days_with_zero += 1
                        has_any_zero = True
                if has_any_zero:
                    days_with_any_zero += 1
            
            # KPI-Kacheln
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    label="Durchschnittlicher Lagerbestand (Gesamt)",
                    value=f"{int(round(total_avg_stock)):,}".replace(",", "."),
                    help="Durchschnittlicher Gesamtbestand über den Zeitraum (alle Satteltypen)"
                )
            
            with col2:
                st.metric(
                    label="Tage mit 0 Bestand (Gesamt)",
                    value=f"{days_with_any_zero}",
                    help="Anzahl Tage, an denen mindestens ein Materialtyp = 0 war"
                )
            
            with col3:
                st.metric(
                    label="Minimum / Maximum Bestand",
                    value=f"{int(round(total_min_stock)):,} / {int(round(total_max_stock)):,}".replace(",", "."),
                    help="Minimum und Maximum Gesamtbestand über den Zeitraum"
                )
            
            st.divider()
            
            # KPIs pro Satteltyp
            st.subheader("KPIs pro Satteltyp")
            
            kpi_rows = []
            for saddle_type in sorted(saddle_types):
                kpi = kpi_data_by_saddle[saddle_type]
                kpi_rows.append({
                    'Satteltyp': saddle_type,
                    'Durchschnittlicher Bestand': int(round(kpi['avg_stock'])),
                    'Minimum Bestand': int(round(kpi['min_stock'])),
                    'Maximum Bestand': int(round(kpi['max_stock'])),
                    'Tage mit 0 Bestand': kpi['days_with_zero'],
                    'Ø Tagesverbrauch': int(round(kpi['avg_daily_consumption'])) if kpi['avg_daily_consumption'] > 0 else 0,
                    'Ø Reichweite (Tage)': f"{kpi['avg_days_of_supply']:.1f}" if kpi['avg_days_of_supply'] > 0 else "N/A"
                })
            
            kpi_df = pd.DataFrame(kpi_rows)
            st.dataframe(kpi_df, width='stretch', hide_index=True)
            
            # Bestand über Zeit
            st.subheader("Bestand über Zeit")
            fig_material_stocks = go.Figure()
            
            saddle_colors = {
                'Fizik Tundra': '#2ca02c',
                'Raceline': '#9467bd',
                'Spark': '#1f77b4',
                'Speedline': '#d62728'
            }
            
            for saddle_type in sorted(saddle_types):
                dates = []
                stocks = []
                for date_key in sorted(planning_year_dates.keys()):
                    dates.append(date_key)
                    stocks.append(planning_year_dates[date_key].get(saddle_type, 0.0))
                
                fig_material_stocks.add_trace(go.Scatter(
                    x=dates,
                    y=stocks,
                    name=saddle_type,
                    line=dict(color=saddle_colors.get(saddle_type, '#808080'), width=2),
                    mode='lines'
                ))
            
            fig_material_stocks.update_layout(
                xaxis_title="Datum",
                yaxis_title="Bestand (Einheiten)",
                height=400,
                hovermode='x unified',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_material_stocks, width='stretch', key='chart_material_stocks_kpi')
            
            # Engpass-Analyse
            st.subheader("Engpass-Analyse")
            
            bottleneck_data = sorted(
                [(saddle, kpi_data_by_saddle[saddle]['days_with_zero']) for saddle in saddle_types],
                key=lambda x: x[1],
                reverse=True
            )
            
            if bottleneck_data:
                bottleneck_df = pd.DataFrame([
                    {
                        'Satteltyp': saddle,
                        'Tage mit 0 Bestand': days_zero,
                        'Engpass-Risiko': '🔴 Hoch' if days_zero > 30 else ('🟡 Mittel' if days_zero > 10 else '🟢 Niedrig')
                    }
                    for saddle, days_zero in bottleneck_data
                ])
                st.dataframe(bottleneck_df, width='stretch', hide_index=True)
        else:
            st.info("Keine Materiallager-Daten für das Planungsjahr verfügbar.")
    else:
        st.info("Keine Materiallager-Daten verfügbar.")

# ============================================================================
# TAB 3: PRODUKTION
# ============================================================================

with tab3:
    # KPI-Dashboard Produktion
    st.header("🏭 KPI-Dashboard Produktion")
    
    # Hole KPIs aus Session State
    kpis = st.session_state.get('kpis', {})
    service_level = kpis.get('service_level', 0.0)
    total_demand = kpis.get('total_demand', 0.0)
    total_produced = kpis.get('total_produced', 0.0)
    
    # Falls KPIs nicht vorhanden, berechne sie aus results_df
    if not kpis or service_level == 0.0:
        total_demand = results_df['Daily_Target'].sum() if 'Daily_Target' in results_df.columns else 0.0
        total_produced = results_df['Actual_Build'].sum() if 'Actual_Build' in results_df.columns else 0.0
        service_level = (total_produced / total_demand * 100) if total_demand > 0 else 0.0
    
    # Farblogik für Service Level
    if service_level >= 95.0:
        service_level_color = "normal"
        service_level_delta = f"✅ Gut"
    elif service_level >= 90.0:
        service_level_color = "normal"
        service_level_delta = f"⚠️ Akzeptabel"
    else:
        service_level_color = "inverse"
        service_level_delta = f"❌ Kritisch"
    
    # KPI-Kacheln
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Service Level",
            value=f"{service_level:.2f}%",
            delta=service_level_delta,
            delta_color=service_level_color
        )
    
    with col2:
        st.metric(
            label="Gesamtnachfrage",
            value=f"{int(round(total_demand)):,}".replace(",", "."),
            help="Summe aller Nachfragen im Zeitraum"
        )
    
    with col3:
        st.metric(
            label="Gesamtproduktion",
            value=f"{int(round(total_produced)):,}".replace(",", "."),
            help="Summe aller produzierten Einheiten im Zeitraum"
        )
    
    st.divider()
    
    # Gesamtübersicht Produktion
    st.subheader("Gesamtübersicht")
    
    production_logs = get_production_logs()
    
    if not production_logs:
        st.warning("⚠️ Keine Produktionslogs verfügbar.")
    else:
        # Berechne Gesamt-Backlog und Gesamt-Über-/Unterproduktion
        total_backlog_data = []
        total_deviation_data = []
        
        date_cache = {day: workday_calc.get_date_from_day(day) for day in range(365)}
        
        for day in range(365):
            current_date = date_cache[day]
            
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
            
            backlog_data = []
            deviation_data = []
            
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
        
        # Bestände Fahrräder
        st.subheader("Bestände Fahrräder")
        
        bicycle_inventory_data = get_bicycle_inventory_data()
        
        if bicycle_inventory_data:
            fig_bicycles = go.Figure()
            
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
