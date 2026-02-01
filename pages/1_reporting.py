"""
Reporting-Seite
Übersicht über Lagerbestände und Produktionsleistung
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta
import math
import time
from config.master_data import MasterData
from simulation.simulator import Simulator
from models.scenarios import ScenarioManager
from simulation.workday_calculator import WorkdayCalculator
from ui.scenario_sidebar import render_scenario_sidebar
from ui.utils import initialize_session_state, run_happy_path_simulation
from ui.volume_planning_utils import calculate_volume_planning_demand

st.set_page_config(page_title="Reporting", layout="wide", page_icon="📊")

# Theme Toggle (oben rechts, global)
# Theme-Toggle entfernt - Light Mode ist Standard
from ui.theme_toggle import apply_theme
apply_theme("light")  # Light Mode immer aktiv

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
# PERFORMANCE: Prüfe ob Simulation läuft bevor run_happy_path_simulation() aufgerufen wird
if not st.session_state.get('simulation_running', False):
    run_happy_path_simulation()
else:
    # Simulation läuft bereits - zeige Info und warte
    elapsed = time.time() - st.session_state.get('simulation_start_time', time.time())
    st.info(f"🔄 Simulation läuft... Bitte warten Sie ({int(elapsed)}s)")
    st.stop()

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
    # PERFORMANCE: Prüfe Cache zuerst (schnellster Check)
    if 'material_inventory_data' in st.session_state and st.session_state.material_inventory_data:
        return st.session_state.material_inventory_data
    
    # PERFORMANCE: Wenn saddle_logs_cache vorhanden ist, bedeutet das dass material_inventory_data berechnet wurde
    # aber möglicherweise gelöscht wurde. Versuche es direkt zu berechnen statt Modul zu importieren.
    if 'saddle_logs_cache' in st.session_state:
        # Versuche material_inventory_data direkt zu berechnen (schneller als Modul-Import)
        from ui.material_calculations import calculate_material_inventory
        material_inventory_data, _ = calculate_material_inventory()
        if material_inventory_data:
            return material_inventory_data
        return {}
    
    # PERFORMANCE: Fallback auf Modul-Import nur wenn wirklich nötig
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
    # PERFORMANCE: Cache für bicycle_inventory_data
    cache_key = f"bicycle_inventory_data_{st.session_state.get('production_logs_cache_key', 'none')}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    
    bicycle_inventory = {}
    stock_by_product = {product: 0.0 for product in MasterData.BOM.keys()}
    
    # PERFORMANCE: Verwende Cache statt calculate_production_logs() neu aufzurufen
    # Dies vermeidet mehrfache teure Berechnungen
    production_logs_cache = st.session_state.get('production_logs_cache', {})
    
    # Fallback: Nur wenn Cache nicht verfügbar ist, berechne neu
    if not production_logs_cache:
        from ui.production_calculations import calculate_production_logs
        production_logs_cache = calculate_production_logs()
    
    # Hole tägliche Nachfrage (für Lagerabgang)
    daily_demands_actual = st.session_state.get('daily_demands_actual', {})
    
    # PERFORMANCE: Verwende Date-Cache für bessere Performance
    date_cache = {}
    for day in range(365):
        date_cache[day] = workday_calc.get_date_from_day(day)
    
    for day in range(365):
        current_date = date_cache[day]
        bicycle_inventory[current_date] = {}
        
        # Für jedes Produkt
        for product in MasterData.BOM.keys():
            # KRITISCH: Hole fertiggestellte PM aus production_logs_cache (wie in create_finished_goods_log)
            finished_pm = 0.0
            if production_logs_cache and product in production_logs_cache and not production_logs_cache[product].empty:
                df_prod = production_logs_cache[product]
                date_str = current_date.strftime(MasterData.DATE_FORMAT)
                matching_rows = df_prod[df_prod['Datum'] == date_str]
                if not matching_rows.empty:
                    finished_pm = matching_rows.iloc[0].get('fertiggestellte PM', 0.0)
                    try:
                        finished_pm = float(finished_pm) if finished_pm > 0 else 0.0
                    except (ValueError, TypeError):
                        finished_pm = 0.0
            
            # Fallback: Verwende results_df wenn production_logs_cache nicht verfügbar
            if finished_pm == 0.0 and day < len(results_df):
                actual_build = results_df.iloc[day]['Actual_Build']
                product_share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)
                finished_pm = actual_build * product_share
            
            # Lagerzugang = fertiggestellte PM (pro Produkt)
            total_receipt = finished_pm
            
            # Lagerabgang = Nachfrage für dieses Produkt an diesem Tag
            # KRITISCH: Verwende tägliche Nachfrage aus daily_demands_actual
            day_demand = daily_demands_actual.get(day, {})
            total_dispatch = day_demand.get(product, 0.0)
            
            # Bestand (kumulativ)
            stock_morning = stock_by_product[product]
            stock_evening = stock_morning + total_receipt - total_dispatch
            stock_by_product[product] = max(0.0, stock_evening)
            bicycle_inventory[current_date][product] = stock_by_product[product]
    
    # PERFORMANCE: Cache Ergebnis
    st.session_state[cache_key] = bicycle_inventory
    return bicycle_inventory

def get_production_logs():
    """Liest Produktionslogs direkt aus dem ProductionPlanner"""
    if 'simulator' not in st.session_state or st.session_state.simulator is None:
        return {}
    
    # KRITISCH: Prüfe ob Simulator wirklich verfügbar ist (könnte None sein bei Fehlern)
    if 'simulator' not in st.session_state or st.session_state.simulator is None:
        st.error("❌ Simulator ist nicht verfügbar. Bitte starten Sie die Simulation neu.")
        st.stop()
    
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
    # PERFORMANCE: calculate_volume_planning_demand() prüft selbst den Cache
    # WICHTIG: Immer aufrufen - Funktion prüft selbst, ob Cache noch gültig ist
    # (durch Vergleich des Cache-Keys mit aktiven Szenarien)
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
            
            # Berechne Schichten (aus Stammdaten: Kapazität, Montagelinien, Min/Max Schichten)
            cfg = MasterData.GLOBAL_CONFIG
            HOURS_PER_SHIFT = cfg.get('working_hours_per_shift', 8)
            CAPACITY_PER_HOUR = cfg.get('capacity_per_hour', 130)
            ASSEMBLY_LINES = cfg.get('assembly_lines', 1)
            MIN_SHIFTS = cfg.get('min_shifts_per_day', 1)
            MAX_SHIFTS = cfg.get('max_shifts_per_day', 3)
            CAPACITY_PER_SHIFT = HOURS_PER_SHIFT * CAPACITY_PER_HOUR * ASSEMBLY_LINES
            
            total_week_demand = sum(week_demand_actual.values())
            if total_week_demand > 0 and daily_demands_for_shifts:
                required_shifts_float = max(daily_demands_for_shifts) / CAPACITY_PER_SHIFT
                required_shifts_int = math.ceil(required_shifts_float)
                shifts = max(MIN_SHIFTS, min(MAX_SHIFTS, required_shifts_int))
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
    
    # PERFORMANCE: Prüfe Cache bevor teure Berechnungen ausgeführt werden
    # WICHTIG: Stelle sicher, dass alle abhängigen Daten aktualisiert sind
    # 1. Volumenplanung (Basis für alle anderen Berechnungen)
    # PERFORMANCE: calculate_volume_planning_demand() prüft selbst den Cache
    calculate_volume_planning_demand()
    
    # 2. Produktionslogs (invalidiert Material-Cache nach Berechnung)
    # PERFORMANCE: calculate_production_logs() prüft selbst den Cache
    from ui.production_calculations import calculate_production_logs
    with st.spinner("Berechne Produktionslogs..."):
        calculate_production_logs()
    
    # 3. Materialinventar (neu berechnet mit aktualisierten Produktionsdaten)
    # PERFORMANCE: calculate_material_inventory() prüft selbst den Cache
    from ui.material_calculations import calculate_material_inventory
    with st.spinner("Berechne Materialinventar..."):
        calculate_material_inventory()
    
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
            
            start_date_year = date(planning_year, 1, 1)
            
            for saddle_type in saddle_types:
                stocks = []
                days_with_zero = 0
                consumption_per_day = []
                previous_stock = None
                
                for date_key in sorted(planning_year_dates.keys()):
                    stock = planning_year_dates[date_key].get(saddle_type, 0.0)
                    stocks.append(stock)
                    
                    # FIX: Nur Arbeitstage als Engpass zählen
                    day_idx = (date_key - start_date_year).days
                    is_workday = workday_calc.is_workday(day_idx)
                    
                    if stock == 0 and is_workday:
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
            
            # Tage mit 0 Bestand (Gesamt) - unter Berücksichtigung von Arbeitstagen
            days_with_any_zero = 0
            for date_key in sorted(planning_year_dates.keys()):
                day_idx = (date_key - start_date_year).days
                if not workday_calc.is_workday(day_idx):
                    continue
                    
                has_any_zero = False
                for saddle_type in saddle_types:
                    stock = planning_year_dates[date_key].get(saddle_type, 0.0)
                    if stock == 0:
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
                    label="Tage mit Engpass (Bestand 0)",
                    value=f"{days_with_any_zero}",
                    help="Anzahl Arbeitstage, an denen mindestens ein Materialtyp = 0 war"
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
                    'Tage mit 0 Bestand (Arbeitstage)': kpi['days_with_zero'],
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
                        'Tage mit 0 Bestand (Arbeitstage)': days_zero,
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
    
    # PERFORMANCE: Prüfe Cache bevor teure Berechnungen ausgeführt werden
    # WICHTIG: Stelle sicher, dass alle abhängigen Daten aktualisiert sind
    # 1. Volumenplanung (Basis für Produktionsberechnung)
    # PERFORMANCE: calculate_volume_planning_demand() prüft selbst den Cache
    calculate_volume_planning_demand()
    
    # 2. Produktionslogs (dynamisch, berücksichtigt Marketing)
    # PERFORMANCE: calculate_production_logs() prüft selbst den Cache
    from ui.production_calculations import calculate_production_logs
    with st.spinner("Berechne Produktionslogs..."):
        production_logs_cache = calculate_production_logs()
    
    # Berechne KPIs aus production_logs_cache (dynamisch, mit Marketing)
    if production_logs_cache:
        daily_demands_actual = st.session_state.get('daily_demands_actual', {})
        total_demand = sum(sum(day_demand.values()) for day_demand in daily_demands_actual.values())
        
        # KRITISCH: Summiere 'fertiggestellte PM' für echte Produktionsleistung
        # WICHTIG: Nur gültige Werte berücksichtigen (nicht NaN oder negative Werte)
        # KRITISCH: Addiere auch die tatsächliche PM vom letzten Tag des Jahres (wird nicht als fertiggestellte PM am nächsten Tag berücksichtigt)
        total_produced = 0.0
        last_day_actual_pm = 0.0  # Sammle tatsächliche PM vom letzten Tag
        
        for product, df in production_logs_cache.items():
            if not df.empty:
                if 'fertiggestellte PM' in df.columns:
                    # Filtere nur gültige Werte (nicht NaN, nicht negativ)
                    finished_pm_series = pd.to_numeric(df['fertiggestellte PM'], errors='coerce').fillna(0.0)
                    finished_pm_series = finished_pm_series[finished_pm_series >= 0]
                    total_produced += finished_pm_series.sum()
                    
                    # KRITISCH: Addiere auch die tatsächliche PM vom letzten Tag des Jahres
                    # Die tatsächliche PM vom letzten Tag wird nicht als fertiggestellte PM am nächsten Tag berücksichtigt
                    # weil es keinen nächsten Tag gibt. Daher müssen wir sie hier explizit addieren.
                    if 'tatsächliche PM' in df.columns and 'Datum' in df.columns:
                        # Finde letzte Zeile des Jahres (31.12.2027)
                        last_date_str = date(planning_year, 12, 31).strftime(MasterData.DATE_FORMAT)
                        last_row = df[df['Datum'] == last_date_str]
                        if not last_row.empty:
                            last_actual_pm_val = last_row.iloc[0].get('tatsächliche PM', 0)
                            try:
                                last_actual_pm = float(pd.to_numeric(last_actual_pm_val, errors='coerce')) if pd.notna(pd.to_numeric(last_actual_pm_val, errors='coerce')) else 0.0
                                if last_actual_pm > 0:
                                    last_day_actual_pm += last_actual_pm
                            except (ValueError, TypeError):
                                pass
                elif 'tatsächliche PM' in df.columns:
                    # Fallback falls Simulation noch nicht weit genug lief
                    actual_pm_series = pd.to_numeric(df['tatsächliche PM'], errors='coerce').fillna(0.0)
                    actual_pm_series = actual_pm_series[actual_pm_series >= 0]
                    total_produced += actual_pm_series.sum()
        
        # Addiere tatsächliche PM vom letzten Tag
        total_produced += last_day_actual_pm
        
        service_level = (total_produced / total_demand * 100) if total_demand > 0 else 0.0
    else:
        # Fallback: Berechne aus results_df (statisch)
        kpis = st.session_state.get('kpis', {})
        service_level = kpis.get('service_level', 0.0)
        total_demand = kpis.get('total_demand', 0.0)
        total_produced = kpis.get('total_produced', 0.0)
        
        if not kpis or service_level == 0.0:
            # Fallback: Berechne aus results_df (statisch)
            total_demand = results_df['Daily_Target'].sum() if 'Daily_Target' in results_df.columns else 0.0
            total_produced = results_df['Actual_Build'].sum() if 'Actual_Build' in results_df.columns else 0.0
            service_level = (total_produced / total_demand * 100) if total_demand > 0 else 0.0
    
    # Farblogik für Service Level
    if service_level >= 100.0:
        service_level_color = "normal"
        service_level_delta = f"⭐ Ausgezeichnet"
    elif service_level >= 99.0:
        service_level_color = "normal"
        service_level_delta = f"✅ Sehr gut"
    elif service_level >= 95.0:
        service_level_color = "normal"
        service_level_delta = f"✅ Gut"
    elif service_level >= 80.0:
        service_level_color = "normal"
        service_level_delta = f"⚠️ OK"
    else:
        service_level_color = "inverse"
        service_level_delta = f"❌ Schlecht"
    
    # KPI-Kacheln
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Service Level",
            value=f"{service_level:.2f}%",
            delta=service_level_delta,
            delta_color=service_level_color,
            help="Berechnung: Service Level = (Gesamtproduktion / Gesamtnachfrage) × 100%. "
                 "Die Gesamtproduktion umfasst alle fertiggestellten Fahrräder im Zeitraum. "
                 "Die Gesamtnachfrage ist die Summe aller Tagesnachfragen. "
                 "Reagiert auf Marketing-Szenarien (erhöhte Nachfrage) und Produktionsstörungen."
        )
    
    with col2:
        st.metric(
            label="Gesamtnachfrage",
            value=f"{int(round(total_demand)):,}".replace(",", "."),
            help="Summe aller Nachfragen im Zeitraum"
        )
    
    with col3:
        st.metric(
            label="Gesamtproduktion (Fertiggestellt)",
            value=f"{int(round(total_produced)):,}".replace(",", "."),
            help="Summe aller fertiggestellten Fahrräder im Zeitraum"
        )
    
    st.divider()
    
    # Gesamtübersicht Produktion
    st.subheader("Gesamtübersicht")
    
    # Verwende production_logs_cache (dynamisch, mit Marketing) statt statischer production_logs
    production_logs = production_logs_cache if production_logs_cache else get_production_logs()
    
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
                # Handle DataFrame (production_logs_cache) oder Liste (statische production_logs)
                if isinstance(logs, pd.DataFrame):
                    if not logs.empty and day < len(logs):
                        log_entry = logs.iloc[day]
                        total_backlog += log_entry.get('Backlog', 0.0)
                        total_planned += log_entry.get('geplante PM', 0.0)
                        total_actual += log_entry.get('tatsächliche PM', 0.0)
                else:
                    # Liste (statische production_logs)
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
            st.write("**Über-/Unterproduktion (Start)**")
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
            logs = production_logs[product]
            
            # Handle DataFrame (production_logs_cache) oder Liste (statische production_logs)
            if isinstance(logs, pd.DataFrame):
                if logs.empty:
                    continue
                max_day = min(365, len(logs))
            else:
                if not logs:
                    continue
                max_day = min(365, len(logs))
            
            st.write(f"**{product}**")
            
            backlog_data = []
            deviation_data = []
            
            date_cache = {day: workday_calc.get_date_from_day(day) for day in range(max_day)}
            
            for day in range(max_day):
                current_date = date_cache[day]
                
                # Handle DataFrame oder Liste
                if isinstance(logs, pd.DataFrame):
                    log_entry = logs.iloc[day]
                else:
                    log_entry = logs[day]
                
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
            
