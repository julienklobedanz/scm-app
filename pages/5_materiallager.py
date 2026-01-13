"""
Materiallager - Seite
Zeigt Sattelzugänge, Bestände und Verluste
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta, datetime
from typing import Dict
from config.master_data import MasterData
from simulation.simulator import Simulator
from models.scenarios import ScenarioManager
from simulation.workday_calculator import WorkdayCalculator
from ui.scenario_sidebar import render_scenario_sidebar

st.set_page_config(page_title="Materiallager - Supply Chain Simulation", layout="wide", page_icon="📦")

render_scenario_sidebar()

# Init Session State
from ui.utils import initialize_session_state, run_happy_path_simulation

initialize_session_state()

st.title("📦 Materiallager")
st.markdown("Übersicht über Sattelzugänge, Bestände und Verluste")

# Happy Path Simulation
run_happy_path_simulation()

if st.session_state.results_df is None:
    st.warning("⚠️ Keine Simulationsergebnisse verfügbar.")
    st.stop()

results_df = st.session_state.results_df

# Zeitraum
start_date = date(2025, 12, 31)
end_date = date(2026, 12, 31)
workday_calc = WorkdayCalculator(year=2026)
start_date_simulation = date(2026, 1, 1)

def create_saddle_inventory_log():
    """Erstellt Sattel-Lager-Log synchronisiert mit Inbound-Daten"""
    saddle_shares = MasterData.calculate_saddle_shares()
    saddle_types = list(saddle_shares.keys())
    
    saddle_logs = {saddle_type: [] for saddle_type in saddle_types}
    
    # 1. Hole die "Wahrheit" von der Inbound-Logik
    manager = None
    if st.session_state.simulator:
        manager = st.session_state.simulator.china_transport_manager
    elif st.session_state.kpis and 'china_transport_manager' in st.session_state.kpis:
        manager = st.session_state.kpis['china_transport_manager']
    
    receipts_by_date_and_saddle: Dict[date, Dict[str, float]] = {}
    
    if manager:
        # Rufe die Inbound-Tabelle ab (enthält die korrekte 500er Logik und Termine)
        inbound_df = manager.get_inbound_log_dataframe(saddle_shares)
        
        # Scanne die Inbound-Tabelle nach Wareneingängen
        for _, row in inbound_df.iterrows():
            # Datum "Verfügbar im Lager" lesen
            avail_str = row.get('Verfügbar im Lager')
            if avail_str and isinstance(avail_str, str) and len(avail_str) > 0:
                try:
                    avail_date = datetime.strptime(avail_str, MasterData.DATE_FORMAT).date()
                    
                    if avail_date not in receipts_by_date_and_saddle:
                        receipts_by_date_and_saddle[avail_date] = {s: 0.0 for s in saddle_types}
                    
                    # Mengen pro Sattel auslesen und addieren
                    for saddle in saddle_types:
                        qty_val = row.get(saddle)
                        if qty_val and str(qty_val).strip() != '':
                            try:
                                receipts_by_date_and_saddle[avail_date][saddle] += float(qty_val)
                            except ValueError:
                                pass
                except ValueError:
                    continue

    # 2. Materiallager berechnen
    # Startdatum: Früher ansetzen, um Vorlauf (Initial Stock) mitzunehmen!
    # Die Schleife beginnt ab November, sammelt die ersten Lieferungen ein,
    # zieht die ersten Verbräuche ab, und kommt dann am 01.01.2026 mit dem korrekten Bestand an
    start_date_log = date(2025, 11, 1)
    end_date_log = date(2026, 12, 31)
    total_days = (end_date_log - start_date_log).days + 1
    
    stock_by_saddle = {saddle_type: 0.0 for saddle_type in saddle_types}
    material_inventory_data = {}
    
    for day_offset in range(total_days):
        current_date = start_date_log + timedelta(days=day_offset)
        day = (current_date - start_date_simulation).days
        
        # Wochentag / Feiertag
        if 0 <= day < 365:
            day_info = workday_calc.get_day_info(day)
            weekday_abbr = day_info['weekday_abbr']
            is_weekend = day_info['is_weekend']
            is_holiday = day_info['is_holiday']
        else:
            weekday = current_date.weekday()
            weekday_abbr = workday_calc.get_weekday_abbr(day) if 0 <= day < 365 else ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'][weekday]
            is_weekend = weekday >= 5
            is_holiday = False
        
        # Zugang (aus Inbound-Daten)
        receipt_by_saddle = receipts_by_date_and_saddle.get(current_date, {s: 0.0 for s in saddle_types})
        
        # Bestand berechnen
        stock_morning = {}
        stock_evening = {}
        issue_by_saddle = {s: 0.0 for s in saddle_types}
        
        # Verbrauch (Produktion DE) - Exakte Stücklisten-Logik
        if 0 <= day < len(results_df):
            actual_build = results_df.iloc[day]['Actual_Build']
            
            # Neue (exakte) Logik: Rekonstruiere Produktionsmengen pro Produkt
            # Wir nutzen den DemandCalculator des Simulators, um die Nachfrage pro Produkt zu erhalten
            # und verteilen dann die tatsächliche Produktion proportional
            product_demands = {}
            if st.session_state.simulator and hasattr(st.session_state.simulator, 'demand_calculator'):
                demand_calc = st.session_state.simulator.demand_calculator
                
                # Berechne Marketing-Add-ons (wie im Simulator)
                marketing_add_ons = {}
                scenario_manager = st.session_state.get('scenario_manager', None)
                if scenario_manager:
                    marketing_scenarios = scenario_manager.get_marketing_scenarios(day)
                    if marketing_scenarios:
                        month = MasterData.get_month_from_day(day)
                        is_workday = workday_calc.is_workday(day)
                        
                        if is_workday:
                            # Verwende die private Methode (ist in Python trotzdem aufrufbar)
                            base_daily_floats = demand_calc._calculate_monthly_base_daily_float(month)
                            
                            for scenario in marketing_scenarios:
                                factor = scenario.demand_increase_factor
                                for product in MasterData.BOM.keys():
                                    base_float = base_daily_floats.get(product, 0.0)
                                    add_on = base_float * (factor - 1.0)
                                    if product not in marketing_add_ons:
                                        marketing_add_ons[product] = 0.0
                                    marketing_add_ons[product] += add_on
                
                # Prüfe, ob es der letzte Arbeitstag des Jahres ist
                is_last_workday_of_year = False
                if workday_calc.is_workday(day):
                    has_future_workdays = False
                    for future_day in range(day + 1, 365):
                        if workday_calc.is_workday(future_day):
                            has_future_workdays = True
                            break
                    is_last_workday_of_year = not has_future_workdays
                
                # Berechne Nachfrage pro Produkt (wie im Simulator)
                product_demands = demand_calc.calculate_daily_demand_per_product_dict(
                    day, marketing_add_ons, is_last_workday_of_year
                )
            else:
                # Fallback: Verwende PRODUCT_SALES_SHARES (alte Logik)
                total_share = sum(MasterData.PRODUCT_SALES_SHARES.values())
                for product in MasterData.BOM.keys():
                    if total_share > 0:
                        share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0) / total_share
                        product_demands[product] = int(actual_build * share) if actual_build > 0 else 0
                    else:
                        product_demands[product] = 0
            
            # Verteile die tatsächliche Produktion proportional zur Nachfrage
            total_demand = sum(product_demands.values())
            production_by_product = {}
            
            if total_demand > 0 and actual_build > 0:
                # Sortiere Produkte deterministisch
                sorted_products = sorted(MasterData.BOM.keys())
                remaining_actual = actual_build
                
                for i, product in enumerate(sorted_products):
                    if i == len(sorted_products) - 1:
                        # Letztes Produkt bekommt den Rest wegen Rundungsdifferenzen
                        production_by_product[product] = remaining_actual
                    else:
                        # Proportional verteilen
                        share = product_demands[product] / total_demand
                        allocated = int(actual_build * share)
                        production_by_product[product] = allocated
                        remaining_actual -= allocated
            else:
                for product in MasterData.BOM.keys():
                    production_by_product[product] = 0
            
            # Jetzt: Für jedes produzierte Produkt den entsprechenden Sattel aus der BOM abziehen
            # Exakte Stücklisten-Logik: 1 Bike = 1 Sattel (gemäß BOM)
            for product_name, qty in production_by_product.items():
                if qty > 0 and product_name in MasterData.BOM:
                    required_saddle = MasterData.BOM[product_name]['saddle']
                    # 1 Bike = 1 Sattel (exakte Stücklisten-Logik)
                    if required_saddle in issue_by_saddle:
                        issue_by_saddle[required_saddle] += qty

        for s in saddle_types:
            # Morgens = Gestern Abend + Zugang Heute
            stock_morning[s] = stock_by_saddle[s] + receipt_by_saddle.get(s, 0.0)
            
            # KRITISCH: Lagerabgang darf nicht größer sein als Bestand morgens!
            # Wenn kein Bestand vorhanden ist, kann auch nichts ausgegeben werden
            actual_issue = min(issue_by_saddle[s], stock_morning[s])
            
            # Abends = Morgens - Verbrauch
            val = stock_morning[s] - actual_issue
            stock_evening[s] = max(0.0, val)  # Kein negativer Bestand
            
            # Übertrag
            stock_by_saddle[s] = stock_evening[s]
            
            saddle_logs[s].append({
                'Wochentag': weekday_abbr,
                'Datum': current_date.strftime(MasterData.DATE_FORMAT),
                'Lagerzugang': round(receipt_by_saddle.get(s, 0.0), 1) if receipt_by_saddle.get(s, 0.0) > 0 else 0,
                'Bestand morgens': round(stock_morning[s], 1),
                'Lagerabgang': round(actual_issue, 1),  # Begrenzt auf verfügbaren Bestand
                'Verlustmenge': 0,
                'Bestand abends': round(stock_evening[s], 1),
                'Is_Weekend': is_weekend,
                'Is_Holiday': is_holiday
            })
            
        material_inventory_data[current_date] = stock_morning.copy()
    
    st.session_state.material_inventory_data = material_inventory_data
    return {s: pd.DataFrame(l) for s, l in saddle_logs.items()}

# Render
with st.spinner("🔄 Berechne Materiallager..."):
    saddle_logs = create_saddle_inventory_log()

for saddle_type in sorted(saddle_logs.keys()):
    st.subheader(f"📋 {saddle_type}")
    df = saddle_logs[saddle_type]
    # Filtere auf den Standard-Zeitraum (2026)
    mask = (pd.to_datetime(df['Datum'], format='%d.%m.%Y') >= pd.to_datetime(start_date)) & \
           (pd.to_datetime(df['Datum'], format='%d.%m.%Y') <= pd.to_datetime(end_date))
    df_filt = df[mask].copy()
    
    # Styling
    df_filt.reset_index(drop=True, inplace=True)
    weekend_flags = df_filt['Is_Weekend'].values
    holiday_flags = df_filt['Is_Holiday'].values
    
    def style_row_safe(row):
        if row.name < len(weekend_flags):
            if weekend_flags[row.name]:
                return ['background-color: #ffebee'] * len(row)
            if holiday_flags[row.name]:
                return ['background-color: #c8e6c9'] * len(row)
        return [''] * len(row)

    cols = ['Wochentag', 'Datum', 'Lagerzugang', 'Bestand morgens', 'Lagerabgang', 'Verlustmenge', 'Bestand abends']
    
    # Farblegende
    col1, col2 = st.columns([1, 1])
    with col2:
        st.markdown("""
        <div style="text-align: right; margin-bottom: 10px;">
            <span style="background-color: #ffebee; padding: 2px 8px; border-radius: 3px; margin-left: 5px;">Wochenende</span>
            <span style="background-color: #c8e6c9; padding: 2px 8px; border-radius: 3px; margin-left: 5px;">Feiertag</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.dataframe(df_filt[cols].style.apply(style_row_safe, axis=1), use_container_width=True, hide_index=True)
    st.divider()
