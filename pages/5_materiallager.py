"""
Materiallager - Seite
Zeigt Sattelzugänge, Bestände und Verluste
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta
from typing import Dict
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
start_date = date(2025, 12, 31)
end_date = date(2026, 12, 31)
workday_calc = WorkdayCalculator(year=2026)
start_date_simulation = date(2026, 1, 1)  # Simulationsstart

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
    """Erstellt Sattel-Lager-Log für jeden Sattel-Typ basierend auf Inbound-Daten"""
    saddle_shares = calculate_saddle_shares()
    saddle_types = list(saddle_shares.keys())
    
    saddle_logs = {saddle_type: [] for saddle_type in saddle_types}
    
    # Hole Inbound-Daten aus session_state
    # Falls keine Inbound-Daten vorhanden sind, verwende leeres Dictionary
    shipments_data = st.session_state.get('inbound_shipments_data', {})
    
    # Erstelle Dictionary: available_date -> {saddle_type: quantity}
    receipts_by_date_and_saddle: Dict[date, Dict[str, float]] = {}
    
    # Sammle alle Lagerzugänge aus Inbound-Daten
    for shipment_date, shipment_info in shipments_data.items():
        available_date = shipment_info.get("Verfügbar im Lager (DE)")
        if available_date:
            if available_date not in receipts_by_date_and_saddle:
                receipts_by_date_and_saddle[available_date] = {saddle: 0.0 for saddle in saddle_types}
            
            saddle_quantities = shipment_info.get("saddle_quantities", {})
            for saddle_type, qty in saddle_quantities.items():
                if saddle_type in receipts_by_date_and_saddle[available_date]:
                    receipts_by_date_and_saddle[available_date][saddle_type] += float(qty)
    
    # Startdatum: 31.12.2025
    start_date_log = date(2025, 12, 31)
    end_date_log = date(2026, 12, 31)
    total_days = (end_date_log - start_date_log).days + 1
    
    # Initialer Bestand pro Sattel-Typ: Startet bei 0, wird nur durch Lagerzugänge aufgebaut
    stock_by_saddle = {saddle_type: 0.0 for saddle_type in saddle_types}
    
    # Dictionary für Materiallager-Daten (für Produktionsseite)
    # Format: {date: {saddle_type: stock_morning}}
    material_inventory_data = {}
    
    for day_offset in range(total_days):
        current_date = start_date_log + timedelta(days=day_offset)
        
        # Berechne Tag relativ zum Simulation-Start (01.01.2026 = Tag 0)
        day = (current_date - start_date_simulation).days
        
        # Wochentag und Feiertag
        weekday = current_date.weekday()
        weekday_names = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
        weekday_abbr = weekday_names[weekday]
        is_weekend = weekday >= 5
        
        # Prüfe ob Feiertag (nur wenn Tag >= 0, da WorkdayCalculator nur für 2026 funktioniert)
        is_holiday = False
        if day >= 0:
            weekday_name = workday_calc.get_weekday_name(day)
            is_workday = workday_calc.is_workday(day)
            is_holiday = not is_workday and weekday_name not in ['Samstag', 'Sonntag']
        
        # Lagerzugang aus Inbound-Daten für diesen Tag
        receipt_by_saddle = receipts_by_date_and_saddle.get(current_date, {saddle: 0.0 for saddle in saddle_types})
        
        # Bestand morgens = Bestand abends vom Vortag + Lagerzugang (heute)
        # Der Lagerzugang fließt in den Bestand morgens mit ein
        stock_morning_by_saddle = {}
        for saddle_type in saddle_types:
            stock_morning_by_saddle[saddle_type] = stock_by_saddle.get(saddle_type, 0.0) + receipt_by_saddle.get(saddle_type, 0.0)
        
        # Speichere Bestand morgens für Produktionsseite
        material_inventory_data[current_date] = stock_morning_by_saddle.copy()
        
        # Berechne Abgänge (Verbrauch) basierend auf tatsächlicher Produktion pro Produkt
        # Excel-Formel: Summiere Produktionsmengen aller Produkte, die diesen Sattel-Typ verwenden
        issue_by_saddle = {saddle_type: 0.0 for saddle_type in saddle_types}
        
        # Nur wenn Tag >= 0 (innerhalb des Simulationszeitraums)
        if day >= 0:
            # Hole tatsächliche PM pro Produkt aus Produktionsseite (falls verfügbar)
            if 'actual_pm_by_day_and_product' in st.session_state:
                actual_pm_data = st.session_state.actual_pm_by_day_and_product
                if day in actual_pm_data:
                    # Verwende tatsächliche PM pro Produkt aus Produktionsseite
                    for product in MasterData.BOM.keys():
                        product_saddle = MasterData.BOM[product]['saddle']
                        if product_saddle in issue_by_saddle:
                            actual_pm = actual_pm_data[day].get(product, 0.0)
                            issue_by_saddle[product_saddle] += actual_pm
                else:
                    # Fallback: Verwende alte Berechnung
                    actual_build = results_df.iloc[day]['Actual_Build']
                    for product in MasterData.BOM.keys():
                        product_saddle = MasterData.BOM[product]['saddle']
                        if product_saddle in issue_by_saddle:
                            product_share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)
                            product_production = actual_build * product_share
                            issue_by_saddle[product_saddle] += product_production
            else:
                # Fallback: Verwende alte Berechnung (wenn Produktionsseite noch nicht geladen wurde)
                actual_build = results_df.iloc[day]['Actual_Build']
                for product in MasterData.BOM.keys():
                    product_saddle = MasterData.BOM[product]['saddle']
                    if product_saddle in issue_by_saddle:
                        product_share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)
                        product_production = actual_build * product_share
                        issue_by_saddle[product_saddle] += product_production
        
        # Bestand abends = Bestand morgens - Abgang
        stock_evening_by_saddle = {}
        for saddle_type in saddle_types:
            stock_evening_by_saddle[saddle_type] = stock_morning_by_saddle[saddle_type] - issue_by_saddle.get(saddle_type, 0.0)
            # Stelle sicher, dass Bestand nicht negativ wird
            stock_evening_by_saddle[saddle_type] = max(0.0, stock_evening_by_saddle[saddle_type])
        
        # Aktualisiere Bestand für nächsten Tag
        stock_by_saddle = stock_evening_by_saddle.copy()
        
        # Für jeden Sattel-Typ
        for saddle_type in saddle_types:
            saddle_logs[saddle_type].append({
                'Wochentag': weekday_abbr,
                'Datum': current_date.strftime('%d.%m.%Y'),
                'Lagerzugang': round(receipt_by_saddle.get(saddle_type, 0.0), 1),
                'Bestand morgens': round(stock_morning_by_saddle.get(saddle_type, 0.0), 1),
                'Lagerabgang': round(issue_by_saddle.get(saddle_type, 0.0), 1),
                'Verlustmenge': 0,
                'Bestand abends': round(stock_evening_by_saddle.get(saddle_type, 0.0), 1),
                'Is_Weekend': is_weekend,
                'Is_Holiday': is_holiday
            })
    
    # Speichere Materiallager-Daten in session_state für Produktionsseite
    st.session_state.material_inventory_data = material_inventory_data
    
    return {saddle_type: pd.DataFrame(log) for saddle_type, log in saddle_logs.items()}

# Prüfe ob Inbound-Daten verfügbar sind
if 'inbound_shipments_data' not in st.session_state or not st.session_state.get('inbound_shipments_data'):
    st.warning("⚠️ Keine Inbound-Daten verfügbar. Bitte zuerst die Inbound-Seite öffnen, um die Daten zu berechnen.")

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
    
    # Speichere Flags für Wochenende und Feiertage
    weekend_flags = df_saddle_filtered['Is_Weekend'].values
    holiday_flags = df_saddle_filtered['Is_Holiday'].values
    
    # Definiere Spaltenreihenfolge (Wochentag vor Datum)
    column_order = [
        'Wochentag',
        'Datum',
        'Lagerzugang',
        'Bestand morgens',
        'Lagerabgang',
        'Verlustmenge',
        'Bestand abends'
    ]
    df_display = df_saddle_filtered[column_order].copy()
    
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

