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
start_date = date(2026, 1, 1)
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

def calculate_material_inventory_data_if_needed():
    """Berechnet Materiallager-Daten, falls sie nicht in session_state verfügbar sind"""
    from datetime import timedelta
    from typing import Dict
    
    if 'material_inventory_data' in st.session_state:
        return  # Bereits vorhanden
    
    # Berechne Materiallager-Daten (vereinfachte Version, ohne Inbound-Daten)
    # Diese Funktion wird verwendet, wenn Materiallager-Seite noch nicht geladen wurde
    saddle_shares = calculate_saddle_shares()
    saddle_types = list(saddle_shares.keys())
    
    # Hole Inbound-Daten aus session_state (falls verfügbar)
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
    
    # Dictionary für Materiallager-Daten
    material_inventory_data = {}
    
    for day_offset in range(total_days):
        current_date = start_date_log + timedelta(days=day_offset)
        day = (current_date - start_date_simulation).days
        
        # Lagerzugang aus Inbound-Daten für diesen Tag
        receipt_by_saddle = receipts_by_date_and_saddle.get(current_date, {saddle: 0.0 for saddle in saddle_types})
        
        # Bestand morgens = Bestand abends vom Vortag + Lagerzugang (heute)
        stock_morning_by_saddle = {}
        for saddle_type in saddle_types:
            stock_morning_by_saddle[saddle_type] = stock_by_saddle.get(saddle_type, 0.0) + receipt_by_saddle.get(saddle_type, 0.0)
        
        # Speichere Bestand morgens
        material_inventory_data[current_date] = stock_morning_by_saddle.copy()
        
        # Berechne Abgänge (vereinfacht, da tatsächliche PM-Daten noch nicht verfügbar sind)
        issue_by_saddle = {saddle_type: 0.0 for saddle_type in saddle_types}
        
        if day >= 0:
            # Verwende Fallback: actual_build * product_share
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
            stock_evening_by_saddle[saddle_type] = max(0.0, stock_evening_by_saddle[saddle_type])
        
        # Aktualisiere Bestand für nächsten Tag
        stock_by_saddle = stock_evening_by_saddle.copy()
    
    # Speichere in session_state
    st.session_state.material_inventory_data = material_inventory_data

def get_material_stock_by_saddle_type(day: int, saddle_name: str) -> float:
    """Holt Materialbestand für einen spezifischen Sattel-Typ aus Materiallager"""
    # Stelle sicher, dass Materiallager-Daten berechnet sind
    calculate_material_inventory_data_if_needed()
    
    # Hole Materiallager-Daten aus session_state
    if 'material_inventory_data' in st.session_state:
        material_inventory_data = st.session_state.material_inventory_data
        
        # Konvertiere day (0-basiert, ab 01.01.2026) zu Datum
        current_date = workday_calc.get_date_from_day(day)
        
        # Hole Bestand morgens für diesen Tag und Sattel-Typ
        if current_date in material_inventory_data:
            stock_by_saddle = material_inventory_data[current_date]
            return stock_by_saddle.get(saddle_name, 0.0)
    
    # Fallback: Wenn Materiallager-Daten immer noch nicht verfügbar sind
    # Berechne aus results_df und Sattel-Anteilen (wie vorher)
    saddle_shares = calculate_saddle_shares()
    saddle_share = saddle_shares.get(saddle_name, 0.0)
    
    if day == 0:
        stock_saddles = MasterData.DEFAULT_INITIAL_STOCK['saddles']
    else:
        stock_saddles = results_df.iloc[day-1]['Stock_Saddles']
    
    return stock_saddles * saddle_share if saddle_share > 0 else 0.0

def create_production_log():
    """Erstellt Produktions-Log für jedes Produkt basierend auf Excel-Formeln"""
    production_logs = {product: [] for product in MasterData.BOM.keys()}
    saddle_shares = calculate_saddle_shares()
    
    # Carry-Over für Überreste der geplanten PM (pro Produkt)
    carry_over_planned = {product: 0.0 for product in MasterData.BOM.keys()}
    
    # Backlog pro Produkt (wird täglich aktualisiert)
    backlog_by_product = {product: 0.0 for product in MasterData.BOM.keys()}
    
    # Kapazität pro Schicht
    capacity_per_shift = MasterData.GLOBAL_CONFIG['working_hours_per_shift'] * MasterData.GLOBAL_CONFIG['capacity_per_hour']
    
    # Speichere tatsächliche PM pro Produkt für Materiallager
    # Format: {day: {product: actual_pm}}
    actual_pm_by_day_and_product = {}
    
    for day in range(365):
        current_date = workday_calc.get_date_from_day(day)
        weekday_name = workday_calc.get_weekday_name(day)
        is_workday = workday_calc.is_workday(day)
        is_holiday = not is_workday and weekday_name not in ['Samstag', 'Sonntag']
        is_weekend = weekday_name in ['Samstag', 'Sonntag']
        
        # Schichtanzahl und Auslastung
        daily_target = results_df.iloc[day]['Daily_Target']
        actual_build = results_df.iloc[day]['Actual_Build']
        
        # Berechne Schichtanzahl
        if is_workday and daily_target > 0:
            shifts = min(3, max(1, int((daily_target / capacity_per_shift) + 0.5)))
            utilization = (actual_build / (shifts * capacity_per_shift) * 100) if shifts > 0 else 0
        else:
            shifts = 0
            utilization = 0
        
        # Berechne Kapazität für diesen Tag
        daily_capacity = shifts * capacity_per_shift if is_workday else 0
        
        # PHASE 1: Berechne "geplante PM" (aus Volumenplanung mit Carry-Over)
        planned_pm_by_product = {}
        for product in MasterData.BOM.keys():
            # Hole geplante PM aus Volumenplanung Tag (mit Carry-Over-Logik)
            if 'daily_demand_data' in st.session_state and day in st.session_state.daily_demand_data:
                demand_float = st.session_state.daily_demand_data[day].get(product, 0.0)
            else:
                # Fallback: Berechne aus daily_target und product_share
                product_share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)
                demand_float = daily_target * product_share
            
            # Addiere Carry-Over vom Vortag
            demand_with_carry_over = demand_float + carry_over_planned[product]
            
            # Runde ab (ABRUNDEN)
            planned_pm = int(demand_with_carry_over)
            
            # Berechne neuen Carry-Over (Überrest)
            carry_over_planned[product] = demand_with_carry_over - planned_pm
            
            planned_pm_by_product[product] = planned_pm
        
        # PHASE 2: Berechne "Produktionsbedarf" = geplante PM + Backlog
        production_demand_by_product = {}
        for product in MasterData.BOM.keys():
            production_demand_by_product[product] = planned_pm_by_product[product] + backlog_by_product[product]
        
        # PHASE 3: Berechne "Anteilige Produktion wenn möglich"
        # Excel-Formel: =WENN(SUMME(F157:F164)>0;ABRUNDEN(F157*(F154/SUMME(F157:F164));0);0)
        total_production_demand = sum(production_demand_by_product.values())
        proportional_production_by_product = {}
        
        if total_production_demand > 0 and daily_capacity > 0:
            for product in MasterData.BOM.keys():
                demand = production_demand_by_product[product]
                # ABRUNDEN(demand * (capacity / total_demand); 0)
                proportional_production = int(demand * (daily_capacity / total_production_demand))
                proportional_production_by_product[product] = proportional_production
        else:
            for product in MasterData.BOM.keys():
                proportional_production_by_product[product] = 0
        
        # PHASE 4: Berechne Materialverfügbarkeit pro Produkt
        material_availability_by_product = {}
        for product in MasterData.BOM.keys():
            saddle_name = MasterData.BOM[product]['saddle']
            stock_saddle_specific = get_material_stock_by_saddle_type(day, saddle_name)
            # Materialverfügbarkeit = Sattel-Bestand (Rahmen/Gabeln sind unbegrenzt)
            material_availability_by_product[product] = stock_saddle_specific
        
        # PHASE 5: Berechne "Rang Unterstützung" (F177) und Rang (F187)
        # Excel-Formel F177: =ZEILE()/1000000+F167
        # ZEILE() = Zeilennummer, F167 = Materialverfügbarkeit
        # In Python: Verwende Index des Produkts in der Liste als "Zeilennummer"
        products_list = list(MasterData.BOM.keys())
        rank_support_by_product = {}
        for idx, product in enumerate(products_list):
            # Zeilennummer = Index + Offset (in Excel startet ZEILE() bei der tatsächlichen Zeile)
            # Für unsere Zwecke: Index + 1 (damit erste Zeile = 1, nicht 0)
            row_number = idx + 1
            material_avail = material_availability_by_product[product]
            # Excel-Formel: ZEILE()/1000000 + F167
            rank_support = (row_number / 1000000.0) + material_avail
            rank_support_by_product[product] = rank_support
        
        # Bestimme Rang: RANG.GLEICH(F177;F177:F184)
        # RANG.GLEICH gibt den Rang eines Wertes in einer Liste zurück (aufsteigend)
        # Höherer Wert = niedrigerer Rang (1 = höchste Priorität, 8 = niedrigste)
        rank_support_values = [rank_support_by_product[p] for p in products_list]
        rank_by_product = {}
        for product in products_list:
            value = rank_support_by_product[product]
            # Zähle wie viele Produkte einen höheren Wert haben (aufsteigend sortiert)
            # RANG.GLEICH: Bei gleichen Werten wird der gleiche Rang vergeben
            rank = sum(1 for v in rank_support_values if v > value) + 1
            rank_by_product[product] = rank
        
        # PHASE 6: Berechne "tatsächliche PM" basierend auf Rang
        # Excel-Formel F224 (Rang 1): =WENN(F154=0;0; WENN(F187=1;MIN(F157;F167;F197); ...))
        # F157 = Produktionsbedarf, F167 = Materialverfügbarkeit, F197 = Anteilige Produktion
        actual_pm_by_product = {}
        total_produced_so_far = 0.0
        
        # Sortiere Produkte nach Rang (1 = höchste Priorität)
        products_by_rank = sorted(MasterData.BOM.keys(), key=lambda p: rank_by_product[p])
        
        for product in products_by_rank:
            rank = rank_by_product[product]
            demand = production_demand_by_product[product]
            material_avail = material_availability_by_product[product]
            proportional = proportional_production_by_product[product]
            
            if daily_capacity == 0:
                actual_pm = 0.0
            else:
                # MIN(Produktionsbedarf, Materialverfügbarkeit, Anteilige Produktion)
                actual_pm = min(demand, material_avail, proportional)
            
            actual_pm_by_product[product] = actual_pm
            total_produced_so_far += actual_pm
        
        # PHASE 7: Rest-Verteilung (F476)
        # Excel-Formel: =WENN(F$473<F$154; MIN(F154-F473;F455;F157-F465);0)
        # F473 = Summe bereits produziert, F154 = Kapazität, F455 = Verfügbare Materialien, F157 = Produktionsbedarf, F465 = Bereits produziert
        remaining_capacity = daily_capacity - total_produced_so_far
        
        if remaining_capacity > 0:
            # Verteile Rest-Kapazität basierend auf verbleibendem Bedarf
            for product in products_by_rank:
                demand = production_demand_by_product[product]
                material_avail = material_availability_by_product[product]
                already_produced = actual_pm_by_product[product]
                
                # Verbleibender Bedarf
                remaining_demand = demand - already_produced
                
                if remaining_capacity > 0 and remaining_demand > 0:
                    # MIN(Verbleibende Kapazität, Verfügbare Materialien, Verbleibender Bedarf)
                    additional_production = min(remaining_capacity, material_avail - already_produced, remaining_demand)
                    if additional_production > 0:
                        actual_pm_by_product[product] += additional_production
                        total_produced_so_far += additional_production
                        remaining_capacity -= additional_production
        
        # PHASE 8: Für jedes Produkt - Materialprüfung und Log-Eintrag
        for product in MasterData.BOM.keys():
            # Konkrete Einzelteil-Namen
            frame_name = MasterData.BOM[product]['frame']
            saddle_name = MasterData.BOM[product]['saddle']
            fork_name = MasterData.BOM[product]['fork']
            
            # Materialbestand pro Sattel-Typ (aus Materiallager)
            stock_saddle_specific = get_material_stock_by_saddle_type(day, saddle_name)
            
            # Materialien vollständig?
            # Excel-Formel: =WENN(UND(F28>0;F29>0;F30>0);"JA";"NEIN")
            # F28, F29, F30 = Rahmen, Sattel, Gabel
            # Da Rahmen und Gabeln unbegrenzt verfügbar sind, prüfen wir nur Sättel
            materials_complete = 'Ja' if stock_saddle_specific > 0 else 'Nein'
            
            # Tatsächliche PM (aus Rang-Logik)
            actual_qty = actual_pm_by_product[product]
            
            # Backlog = Produktionsbedarf - tatsächliche PM (wird für nächsten Tag verwendet)
            # Der Backlog ist die Differenz zwischen dem, was produziert werden sollte (Produktionsbedarf)
            # und dem, was tatsächlich produziert wurde
            backlog = max(0, production_demand_by_product[product] - actual_qty)
            backlog_by_product[product] = backlog
            
            # Wochentag-Abkürzung
            weekday_abbr = weekday_name[:2]  # Mo, Di, Mi, etc.
            
            # Erstelle Dictionary mit dynamischen Spalten
            # Hinweis: "Produktionsbedarf", "Anteilige Produktion wenn möglich" und "Rang" sind nur Hilfsberechnungen
            # und werden nicht in der Tabelle angezeigt
            log_entry = {
                'Wochentag': weekday_abbr,
                'Datum': current_date.strftime('%d.%m.%Y'),
                'Schichtanzahl': shifts,
                'Auslastung (%)': round(utilization, 1),
                'Materialien vollständig?': materials_complete,
                frame_name: '∞',  # Rahmen sind unbegrenzt verfügbar
                saddle_name: round(stock_saddle_specific, 1),  # Sattel-Bestand
                fork_name: '∞',  # Gabeln sind unbegrenzt verfügbar
                'geplante PM': planned_pm_by_product[product],
                'tatsächliche PM': round(actual_qty, 1),
                'Backlog': round(backlog, 1),
                # Hilfsberechnungen (nicht in Tabelle angezeigt):
                '_Produktionsbedarf': production_demand_by_product[product],
                '_Anteilige_Produktion_wenn_moeglich': proportional_production_by_product[product],
                '_Rang': rank_by_product[product],
                'Is_Weekend': is_weekend,
                'Is_Holiday': is_holiday
            }
            
            production_logs[product].append(log_entry)
        
        # Speichere tatsächliche PM pro Produkt für diesen Tag
        actual_pm_by_day_and_product[day] = actual_pm_by_product.copy()
    
    # Speichere tatsächliche PM pro Produkt in session_state für Materiallager
    st.session_state.actual_pm_by_day_and_product = actual_pm_by_day_and_product
    
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
    
    # Speichere Flags für Wochenende und Feiertage
    weekend_flags = df_prod_filtered['Is_Weekend'].values
    holiday_flags = df_prod_filtered['Is_Holiday'].values
    
    # Hole konkrete Einzelteil-Namen für dieses Produkt
    frame_name = MasterData.BOM[product]['frame']
    saddle_name = MasterData.BOM[product]['saddle']
    fork_name = MasterData.BOM[product]['fork']
    
    # Definiere Spaltenreihenfolge (Wochentag vor Datum)
    # Einzelteile direkt nach "Auslastung (%)"
    # Hinweis: "Produktionsbedarf", "Anteilige Produktion wenn möglich" und "Rang" sind nur Hilfsberechnungen
    # und werden nicht angezeigt (Spalten beginnen mit "_")
    column_order = [
        'Wochentag',
        'Datum',
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

