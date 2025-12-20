"""
Lieferant China-Seite
Zeigt Produktion und Transport zum Hafen Dengwong - je Sattel-Typ eine Tabelle
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from config.master_data import MasterData
from config.holidays_config import HolidaysConfig
from simulation.simulator import Simulator
from models.scenarios import ScenarioManager
from simulation.workday_calculator import WorkdayCalculator
from simulation.demand_calculator import DemandCalculator
from ui.scenario_sidebar import render_scenario_sidebar

st.set_page_config(page_title="Lieferant China", page_icon="🇨🇳", layout="wide")

# Szenarien-Sidebar rendern
render_scenario_sidebar()

st.title("🇨🇳 Lieferant China (Produktion & Vorlauf)")
st.markdown("Überwachung der Produktion und des Transports zum Hafen Dengwong - je Sattel-Typ eine Tabelle.")

# Initialisiere Session State falls nicht vorhanden
if 'scenario_manager' not in st.session_state:
    st.session_state.scenario_manager = ScenarioManager()
if 'results_df' not in st.session_state:
    st.session_state.results_df = None
if 'simulator' not in st.session_state:
    st.session_state.simulator = None
if 'happy_path_run' not in st.session_state:
    st.session_state.happy_path_run = False
if 'yearly_volume' not in st.session_state:
    st.session_state.yearly_volume = 370000

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
            st.session_state.simulator = simulator
            st.session_state.happy_path_run = True
            st.rerun()
    except Exception as e:
        st.error(f"❌ Fehler bei der Simulation: {str(e)}")
        st.exception(e)
        st.session_state.happy_path_run = True

if 'simulator' not in st.session_state or st.session_state.simulator is None:
    st.warning("⚠️ Bitte führen Sie zuerst die Simulation auf dem Dashboard aus.")
else:
    manager = st.session_state.simulator.china_transport_manager
    workday_calc = manager.workday_calculator
    results_df = st.session_state.results_df
    
    # Initialisiere Demand Calculator für Nachsimulation der Sattel-Aufteilung
    yearly_volume = st.session_state.get('yearly_volume', 370000)
    demand_calculator = DemandCalculator(yearly_volume, workday_calc)
    
    # Sammle alle eindeutigen Sattel-Typen aus BOM
    all_saddle_types = set()
    for product in MasterData.BOM.values():
        all_saddle_types.add(product['saddle'])
    all_saddle_types = sorted(list(all_saddle_types))
    
    # Metriken berechnen
    pending_at_port = sum(manager.pending_shipments.values())
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Wartend im Hafen (Gesamt)", f"{int(pending_at_port):,} Stk")
    col2.metric("Volle Container wartend", f"{int(pending_at_port // 500)}")
    col3.metric("Restmenge (Wartet auf 500)", f"{int(pending_at_port % 500)} Stk")
    
    st.divider()
    
    # Erstelle eine Tabelle pro Sattel-Typ
    for saddle_type in all_saddle_types:
        st.subheader(f"📦 {saddle_type}")
        
        # Rekonstruiere tägliche Daten für diesen Sattel-Typ
        daily_data = []
        start_date_simulation = date(2027, 1, 1)
        
        # Finde frühestes und spätestes Bestelldatum
        earliest_order_day = None
        latest_order_day = None
        for (order_day, order_id), status in manager.transport_status.items():
            if earliest_order_day is None or order_day < earliest_order_day:
                earliest_order_day = order_day
            if latest_order_day is None or order_day > latest_order_day:
                latest_order_day = order_day
        
        if earliest_order_day is None:
            st.info(f"Keine Bestellungen für {saddle_type} vorhanden.")
            st.divider()
            continue
        
        # Erstelle tägliche Log-Einträge
        start_date_log = workday_calc.get_date_from_day(earliest_order_day)
        end_date_log = date(2027, 12, 31)
        total_days = (end_date_log - start_date_log).days + 1
        
        for day_offset in range(total_days):
            current_date = start_date_log + timedelta(days=day_offset)
            day = (current_date - start_date_simulation).days
            
            # Bestellmenge für diesen Tag (für diesen Sattel-Typ)
            daily_order_qty = 0.0
            order_day_for_date = None
            
            if current_date < start_date_simulation:
                order_day_for_date = (current_date - start_date_simulation).days
            elif current_date >= start_date_simulation:
                order_day_for_date = (current_date - start_date_simulation).days
            
            # Berechne Sattel-Aufteilung für diesen Bestellungstag
            saddle_breakdown = {}
            lead_time = 49
            demand_day = order_day_for_date + lead_time if order_day_for_date is not None else None
            
            if demand_day is not None and demand_day >= 0 and demand_day < 365:
                month = MasterData.get_month_from_day(demand_day)
                is_workday = workday_calc.is_workday(demand_day)
                
                if is_workday:
                    # Berechne Marketing-Add-ons (falls vorhanden)
                    marketing_add_ons = {}
                    marketing_scenarios = st.session_state.scenario_manager.get_marketing_scenarios(demand_day)
                    
                    if marketing_scenarios:
                        base_daily_floats = demand_calculator._calculate_monthly_base_daily_float(month)
                        for scenario in marketing_scenarios:
                            factor = scenario.demand_increase_factor
                            for product in MasterData.BOM.keys():
                                base_float = base_daily_floats.get(product, 0.0)
                                add_on = base_float * (factor - 1.0)
                                if product not in marketing_add_ons:
                                    marketing_add_ons[product] = 0.0
                                marketing_add_ons[product] += add_on
                    
                    # Berechne Produkt-Nachfrage
                    product_demands = demand_calculator.calculate_daily_demand_per_product_dict(
                        demand_day, marketing_add_ons
                    )
                    
                    # Verteile auf Sattel-Typen basierend auf BOM
                    for product, demand_qty in product_demands.items():
                        product_saddle = MasterData.BOM[product]['saddle']
                        if product_saddle == saddle_type:
                            saddle_breakdown[product] = demand_qty
                            daily_order_qty += demand_qty
            
            # Finde alle Bestellungen, die an diesem Tag bestellt wurden
            orders_today = []
            for (order_day, order_id), status in manager.transport_status.items():
                order_date = workday_calc.get_date_from_day(order_day)
                if order_date == current_date:
                    orders_today.append(status)
            
            # Produktionsdaten: Finde alle Bestellungen, die heute produziert werden
            # Die Produktionsmenge ist die Summe aller Bestellungen, die am Produktionsdatum produziert werden,
            # wobei nur der Anteil dieses spezifischen Sattel-Typs gezählt wird
            production_date = None
            production_qty = 0
            for (order_day, order_id), status in manager.transport_status.items():
                prod_end = workday_calc.get_date_from_day(status['production_end_day'])
                if prod_end == current_date:
                    # Berechne den Anteil dieses Sattel-Typs in dieser Bestellung
                    # Verwende die gleiche Logik wie bei der Bestellmenge-Berechnung
                    order_demand_day = order_day + lead_time
                    if order_demand_day >= 0 and order_demand_day < 365:
                        month = MasterData.get_month_from_day(order_demand_day)
                        if workday_calc.is_workday(order_demand_day):
                            base_daily_floats = demand_calculator._calculate_monthly_base_daily_float(month)
                            marketing_add_ons = {}
                            marketing_scenarios = st.session_state.scenario_manager.get_marketing_scenarios(order_demand_day)
                            if marketing_scenarios:
                                for scenario in marketing_scenarios:
                                    factor = scenario.demand_increase_factor
                                    for product in MasterData.BOM.keys():
                                        base_float = base_daily_floats.get(product, 0.0)
                                        add_on = base_float * (factor - 1.0)
                                        if product not in marketing_add_ons:
                                            marketing_add_ons[product] = 0.0
                                        marketing_add_ons[product] += add_on
                            product_demands = demand_calculator.calculate_daily_demand_per_product_dict(
                                order_demand_day, marketing_add_ons
                            )
                            # Berechne Anteil dieses Sattel-Typs
                            total_demand = sum(product_demands.values())
                            saddle_demand = sum(qty for prod, qty in product_demands.items() if MasterData.BOM[prod]['saddle'] == saddle_type)
                            if total_demand > 0 and saddle_demand > 0:
                                # Diese Bestellung enthält diesen Sattel-Typ
                                # Die Produktionsmenge ist die bestellte Menge * Anteil dieses Sattel-Typs
                                ratio = saddle_demand / total_demand
                                production_qty += status['quantity'] * ratio
                                if production_date is None:
                                    production_date = prod_end
            
            # Warenausgang: Finde alle Versände, die heute stattfinden
            shipment_qty = 0
            for (order_day, order_id), status in manager.transport_status.items():
                if status.get('ship_departure_day') is not None:
                    ship_dep_date = workday_calc.get_date_from_day(status['ship_departure_day'])
                    if ship_dep_date == current_date and status.get('shipped', False):
                        # Berechne Anteil dieses Sattel-Typs (wie oben)
                        order_demand_day = order_day + lead_time
                        if order_demand_day >= 0 and order_demand_day < 365:
                            month = MasterData.get_month_from_day(order_demand_day)
                            if workday_calc.is_workday(order_demand_day):
                                base_daily_floats = demand_calculator._calculate_monthly_base_daily_float(month)
                                marketing_add_ons = {}
                                marketing_scenarios = st.session_state.scenario_manager.get_marketing_scenarios(order_demand_day)
                                if marketing_scenarios:
                                    for scenario in marketing_scenarios:
                                        factor = scenario.demand_increase_factor
                                        for product in MasterData.BOM.keys():
                                            base_float = base_daily_floats.get(product, 0.0)
                                            add_on = base_float * (factor - 1.0)
                                            if product not in marketing_add_ons:
                                                marketing_add_ons[product] = 0.0
                                            marketing_add_ons[product] += add_on
                                product_demands = demand_calculator.calculate_daily_demand_per_product_dict(
                                    order_demand_day, marketing_add_ons
                                )
                                total_demand = sum(product_demands.values())
                                saddle_demand = sum(qty for prod, qty in product_demands.items() if MasterData.BOM[prod]['saddle'] == saddle_type)
                                if total_demand > 0:
                                    ratio = saddle_demand / total_demand
                                    shipped_qty = status.get('shipped_quantity', status.get('quantity', 0))
                                    shipment_qty += shipped_qty * ratio
            
            # Warenbestand: Berechne kumulativen Bestand (Produziert - Versandt)
            # Summiere alle Bestellungen, die produziert wurden (production_end_day <= current_date) aber noch nicht verschickt wurden
            stock_at_port = 0.0
            for (order_day, order_id), status in manager.transport_status.items():
                prod_end = workday_calc.get_date_from_day(status['production_end_day'])
                # Nur wenn Produktion abgeschlossen ist (production_end_day <= current_date)
                if prod_end <= current_date:
                    # Berechne Anteil dieses Sattel-Typs
                    order_demand_day = order_day + lead_time
                    if order_demand_day >= 0 and order_demand_day < 365:
                        month = MasterData.get_month_from_day(order_demand_day)
                        if workday_calc.is_workday(order_demand_day):
                            base_daily_floats = demand_calculator._calculate_monthly_base_daily_float(month)
                            marketing_add_ons = {}
                            marketing_scenarios = st.session_state.scenario_manager.get_marketing_scenarios(order_demand_day)
                            if marketing_scenarios:
                                for scenario in marketing_scenarios:
                                    factor = scenario.demand_increase_factor
                                    for product in MasterData.BOM.keys():
                                        base_float = base_daily_floats.get(product, 0.0)
                                        add_on = base_float * (factor - 1.0)
                                        if product not in marketing_add_ons:
                                            marketing_add_ons[product] = 0.0
                                        marketing_add_ons[product] += add_on
                            product_demands = demand_calculator.calculate_daily_demand_per_product_dict(
                                order_demand_day, marketing_add_ons
                            )
                            total_demand = sum(product_demands.values())
                            saddle_demand = sum(qty for prod, qty in product_demands.items() if MasterData.BOM[prod]['saddle'] == saddle_type)
                            if total_demand > 0:
                                ratio = saddle_demand / total_demand
                                produced_qty = status['quantity'] * ratio
                                # Subtrahiere bereits verschickte Menge
                                if status.get('shipped', False) and status.get('ship_departure_day') is not None:
                                    ship_dep_date = workday_calc.get_date_from_day(status['ship_departure_day'])
                                    if ship_dep_date <= current_date:
                                        shipped_qty = status.get('shipped_quantity', status.get('quantity', 0)) * ratio
                                        produced_qty -= shipped_qty
                                stock_at_port += max(0, produced_qty)  # Nicht negativ
            
            # Freigegeben: Nächster Arbeitstag nach Bestellung
            released_date = None
            if daily_order_qty > 0:
                for i in range(1, 8):
                    check_date = current_date + timedelta(days=i)
                    check_day = (check_date - date(2027, 1, 1)).days
                    if workday_calc.is_workday(check_day):
                        released_date = check_date
                        break
            
            # Maschinenausfall: Prüfe Komplikationen (Standard: "nein", außer Szenario aktiv)
            machine_breakdown = "nein"
            if day is not None and day >= 0:
                supplier_breakdowns = st.session_state.scenario_manager.get_supplier_breakdown_scenarios(day)
                for scenario in supplier_breakdowns:
                    if scenario.component_type in ['saddles', 'all']:
                        if day >= scenario.start_day and day <= scenario.end_day:
                            machine_breakdown = "ja"
                            break
            
            # Prüfe ob chinesischer Feiertag oder Wochenende
            weekday = current_date.weekday()
            is_weekend = weekday >= 5
            is_chinese_holiday = HolidaysConfig.is_holiday(current_date, 'CN')
            is_weekend_or_holiday = is_weekend or is_chinese_holiday
            
            # Produktionsdatum: Finde das Produktionsdatum der Bestellung, die an diesem Tag bestellt wurde
            production_date_for_order = None
            if daily_order_qty > 0:
                # Finde die Bestellung, die an diesem Tag bestellt wurde
                for (order_day, order_id), status in manager.transport_status.items():
                    order_date = workday_calc.get_date_from_day(order_day)
                    if order_date == current_date:
                        # Berechne Anteil dieses Sattel-Typs
                        order_demand_day = order_day + lead_time
                        if order_demand_day >= 0 and order_demand_day < 365:
                            month = MasterData.get_month_from_day(order_demand_day)
                            if workday_calc.is_workday(order_demand_day):
                                base_daily_floats = demand_calculator._calculate_monthly_base_daily_float(month)
                                marketing_add_ons = {}
                                marketing_scenarios = st.session_state.scenario_manager.get_marketing_scenarios(order_demand_day)
                                if marketing_scenarios:
                                    for scenario in marketing_scenarios:
                                        factor = scenario.demand_increase_factor
                                        for product in MasterData.BOM.keys():
                                            base_float = base_daily_floats.get(product, 0.0)
                                            add_on = base_float * (factor - 1.0)
                                            if product not in marketing_add_ons:
                                                marketing_add_ons[product] = 0.0
                                            marketing_add_ons[product] += add_on
                                product_demands = demand_calculator.calculate_daily_demand_per_product_dict(
                                    order_demand_day, marketing_add_ons
                                )
                                total_demand = sum(product_demands.values())
                                saddle_demand = sum(qty for prod, qty in product_demands.items() if MasterData.BOM[prod]['saddle'] == saddle_type)
                                if total_demand > 0 and saddle_demand > 0:
                                    # Diese Bestellung enthält diesen Sattel-Typ
                                    prod_end = workday_calc.get_date_from_day(status['production_end_day'])
                                    production_date_for_order = prod_end
                                    break
            
            # Erstelle Log-Eintrag
            log_entry = {
                'Datum': current_date.strftime('%d.%m.%Y'),
                'Bestelleingang': round(daily_order_qty) if daily_order_qty > 0 else '',
                'Freigegeben': released_date.strftime('%d.%m.%Y') if released_date else '',
                'Maschinenausfall': machine_breakdown,
                'Produktionsdatum': production_date_for_order.strftime('%d.%m.%Y') if production_date_for_order else '',
                'Produktionsmenge': round(production_qty) if production_qty > 0 else 0,
                'Warenausgang': round(shipment_qty) if shipment_qty > 0 else 0,
                'Warenbestand': round(stock_at_port),
                'Is_Weekend_Or_Holiday': is_weekend_or_holiday
            }
            
            daily_data.append(log_entry)
        
        if daily_data:
            df_saddle = pd.DataFrame(daily_data)
            
            # Zeige ALLE Zeilen (nicht gefiltert)
            df_saddle = df_saddle.reset_index(drop=True)
            
            # Spaltenreihenfolge
            display_columns = [
                'Datum',
                'Bestelleingang',
                'Freigegeben',
                'Maschinenausfall',
                'Produktionsdatum',
                'Produktionsmenge',
                'Warenausgang',
                'Warenbestand'
            ]
            
            df_display = df_saddle[display_columns].copy()
            
            # Speichere Is_Weekend_Or_Holiday Flag
            weekend_holiday_flags = df_saddle['Is_Weekend_Or_Holiday'].values
            
            # Zeige Tabelle mit Styling
            styled_df = df_display.style.apply(
                lambda row: ['background-color: #ffebee' if weekend_holiday_flags[row.name] else '' for _ in row],
                axis=1
            )
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        else:
            st.info(f"Keine Daten für {saddle_type} im ausgewählten Zeitraum.")
        
        st.divider()
