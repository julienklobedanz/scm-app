"""
Inbound Logistik-Seite
Zeigt Ware, die das chinesische Festland verlassen hat und auf dem Weg zum Lager Dortmund ist
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from typing import Dict, Tuple
from config.master_data import MasterData
from config.holidays_config import HolidaysConfig
from simulation.simulator import Simulator
from models.scenarios import ScenarioManager
from simulation.workday_calculator import WorkdayCalculator
from simulation.demand_calculator import DemandCalculator
from ui.scenario_sidebar import render_scenario_sidebar

st.set_page_config(page_title="Inbound Logistik", page_icon="🚢", layout="wide")

# Szenarien-Sidebar rendern
render_scenario_sidebar()

st.title("🚢 Inbound Logistik")
st.markdown("Überwachung der Verschiffungen und Zuläufe zum Lager Dortmund.")

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
    
    # ============================================================================
    # PHASE 1: Berechne shipment_qty_by_date_and_saddle (gleiche Logik wie Lieferant China)
    # ============================================================================
    shipment_qty_by_date_and_saddle: Dict[Tuple[date, str], float] = {}
    
    # Finde frühestes und spätestes Bestelldatum
    earliest_order_day = None
    latest_order_day = None
    for (order_day, order_id), status in manager.transport_status.items():
        if earliest_order_day is None or order_day < earliest_order_day:
            earliest_order_day = order_day
        if latest_order_day is None or order_day > latest_order_day:
            latest_order_day = order_day
    
    if earliest_order_day is None:
        st.warning("⚠️ Keine Bestellungen vorhanden.")
    else:
        start_date_log = workday_calc.get_date_from_day(earliest_order_day)
        end_date_log = date(2026, 12, 31)
        total_days = (end_date_log - start_date_log).days + 1
        start_date_simulation = date(2026, 1, 1)
        
        # Sammle für alle Sattel-Typen: Produktionsmenge und Warenbestand pro Tag
        production_by_date_and_saddle: Dict[Tuple[date, str], float] = {}
        stock_by_date_and_saddle: Dict[Tuple[date, str], float] = {}
        
        # Iteriere über alle Tage und alle Sattel-Typen
        for saddle_type in all_saddle_types:
            stock_at_port_vortag = 0.0
            order_quantities_by_order_date: Dict[date, Tuple[float, date, date]] = {}
            
            for day_offset in range(total_days):
                current_date = start_date_log + timedelta(days=day_offset)
                day = (current_date - start_date_simulation).days
                
                daily_order_qty = 0.0
                order_day_for_date = None
                
                if current_date < start_date_simulation:
                    order_day_for_date = (current_date - start_date_simulation).days
                elif current_date >= start_date_simulation:
                    order_day_for_date = (current_date - start_date_simulation).days
                
                lead_time = 49
                demand_day = order_day_for_date + lead_time if order_day_for_date is not None else None
                
                if demand_day is not None and demand_day >= 0 and demand_day < 365:
                    month = MasterData.get_month_from_day(demand_day)
                    is_workday = workday_calc.is_workday(demand_day)
                    
                    if is_workday:
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
                        
                        product_demands = demand_calculator.calculate_daily_demand_per_product_dict(
                            demand_day, marketing_add_ons
                        )
                        
                        for product, demand_qty in product_demands.items():
                            product_saddle = MasterData.BOM[product]['saddle']
                            if product_saddle == saddle_type:
                                daily_order_qty += demand_qty
                
                weekday = current_date.weekday()
                is_weekend = weekday >= 5
                is_chinese_holiday = HolidaysConfig.is_holiday(current_date, 'CN')
                
                released_date = None
                if daily_order_qty > 0:
                    chinese_holidays = HolidaysConfig.get_holidays_for_year(2026, 'CN')
                    for i in range(1, 8):
                        check_date = current_date + timedelta(days=i)
                        weekday_check = check_date.weekday()
                        is_weekend_check = weekday_check >= 5
                        is_chinese_holiday_check = check_date in chinese_holidays
                        if not is_weekend_check and not is_chinese_holiday_check:
                            released_date = check_date
                            break
                
                production_date_for_order = None
                if daily_order_qty > 0 and released_date is not None:
                    for (order_day, order_id), status in manager.transport_status.items():
                        order_date_from_status = workday_calc.get_date_from_day(order_day)
                        if order_date_from_status == current_date:
                            if 'production_end_day' in status:
                                production_date_for_order = workday_calc.get_date_from_day(status['production_end_day'])
                                break
                    
                    if production_date_for_order is None and released_date is not None:
                        released_day = (released_date - date(2026, 1, 1)).days
                        chinese_holidays = HolidaysConfig.get_holidays_for_year(2026, 'CN')
                        production_start_day = released_day
                        production_end_day = production_start_day + 1
                        workdays_added = 0
                        max_iterations = 20
                        iteration = 0
                        while workdays_added < 4 and iteration < max_iterations:
                            iteration += 1
                            check_date = workday_calc.get_date_from_day(production_end_day)
                            weekday_check = check_date.weekday()
                            is_weekend_check = weekday_check >= 5
                            is_chinese_holiday_check = check_date in chinese_holidays
                            if not is_weekend_check and not is_chinese_holiday_check:
                                workdays_added += 1
                            if workdays_added < 4:
                                production_end_day += 1
                        if iteration < max_iterations:
                            production_date_for_order = workday_calc.get_date_from_day(production_end_day)
                    
                    if released_date is not None and production_date_for_order is not None:
                        order_quantities_by_order_date[current_date] = (daily_order_qty, released_date, production_date_for_order)
                
                production_qty = 0.0
                for order_date, (order_qty, released_date_for_order, production_date_for_order) in order_quantities_by_order_date.items():
                    if production_date_for_order == current_date:
                        production_qty += order_qty
                
                available_stock = stock_at_port_vortag + production_qty
                
                production_by_date_and_saddle[(current_date, saddle_type)] = production_qty
                stock_by_date_and_saddle[(current_date, saddle_type)] = available_stock
                
                stock_at_port_vortag = available_stock
        
        # ============================================================================
        # PHASE 2: Losgrößen-Logik für Warenausgang (gleiche Logik wie Lieferant China)
        # ============================================================================
        lot_size = MasterData.CHINA_SUPPLIER['Saddles']['lot_size']  # 500
        
        carry_over_by_saddle: Dict[str, float] = {saddle: 0.0 for saddle in all_saddle_types}
        
        for day_offset in range(total_days):
            current_date = start_date_log + timedelta(days=day_offset)
            day = (current_date - start_date_simulation).days
            
            weekday = current_date.weekday()
            is_weekend = weekday >= 5
            is_chinese_holiday = HolidaysConfig.is_holiday(current_date, 'CN')
            is_weekend_or_holiday = is_weekend or is_chinese_holiday
            
            machine_breakdown = False
            if day is not None and day >= 0:
                supplier_breakdowns = st.session_state.scenario_manager.get_supplier_breakdown_scenarios(day)
                for scenario in supplier_breakdowns:
                    if scenario.component_type in ['saddles', 'all']:
                        if day >= scenario.start_day and day <= scenario.end_day:
                            machine_breakdown = True
                            break
            
            if is_weekend_or_holiday or machine_breakdown:
                for saddle_type in all_saddle_types:
                    shipment_qty_by_date_and_saddle[(current_date, saddle_type)] = 0.0
                continue
            
            production_by_saddle: Dict[str, float] = {}
            available_stock_by_saddle: Dict[str, float] = {}
            
            for saddle_type in all_saddle_types:
                production_by_saddle[saddle_type] = production_by_date_and_saddle.get((current_date, saddle_type), 0.0)
                available_stock_by_saddle[saddle_type] = stock_by_date_and_saddle.get((current_date, saddle_type), 0.0)
            
            total_accumulated = 0.0
            for saddle_type in all_saddle_types:
                production_qty = production_by_saddle[saddle_type]
                carry_over = carry_over_by_saddle[saddle_type]
                total_accumulated += production_qty + carry_over
            
            if total_accumulated < lot_size:
                losgroesse = 0
            else:
                losgroesse = int(total_accumulated / lot_size) * lot_size
            
            total_available_stock = sum(available_stock_by_saddle.values())
            losgroesse = min(losgroesse, total_available_stock)
            
            if losgroesse > 0:
                unrounded_shares: Dict[str, float] = {}
                for saddle_type in all_saddle_types:
                    production_qty = production_by_saddle[saddle_type]
                    carry_over = carry_over_by_saddle[saddle_type]
                    accumulated_qty = production_qty + carry_over
                    if total_accumulated > 0:
                        unrounded_share = accumulated_qty * (losgroesse / total_accumulated)
                    else:
                        unrounded_share = 0.0
                    unrounded_shares[saddle_type] = unrounded_share
                
                rounded_shares: Dict[str, int] = {}
                sum_rounded = 0
                for saddle_type in all_saddle_types:
                    rounded_share = int(unrounded_shares[saddle_type])
                    rounded_shares[saddle_type] = rounded_share
                    sum_rounded += rounded_share
                
                differenz = losgroesse - sum_rounded
                
                if differenz > 0:
                    decimal_rests = []
                    for saddle_type in all_saddle_types:
                        decimal_rest = unrounded_shares[saddle_type] - rounded_shares[saddle_type]
                        production_qty = production_by_saddle[saddle_type]
                        carry_over = carry_over_by_saddle[saddle_type]
                        remaining_capacity = (production_qty + carry_over) - rounded_shares[saddle_type]
                        available_stock = available_stock_by_saddle[saddle_type]
                        remaining_capacity = min(remaining_capacity, available_stock - rounded_shares[saddle_type])
                        decimal_rests.append((saddle_type, decimal_rest, remaining_capacity))
                    
                    decimal_rests.sort(key=lambda x: (x[1], x[2]), reverse=True)
                    
                    for i, (saddle_type, decimal_rest, remaining_capacity) in enumerate(decimal_rests):
                        if differenz > 0 and remaining_capacity > 0:
                            if differenz <= remaining_capacity:
                                extra = differenz
                            else:
                                extra = remaining_capacity
                            rounded_shares[saddle_type] += extra
                            differenz -= extra
                
                for saddle_type in all_saddle_types:
                    final_shipment = rounded_shares[saddle_type]
                    available_stock = available_stock_by_saddle[saddle_type]
                    final_shipment = min(final_shipment, available_stock)
                    shipment_qty_by_date_and_saddle[(current_date, saddle_type)] = final_shipment
                    
                    production_qty = production_by_saddle[saddle_type]
                    carry_over = carry_over_by_saddle[saddle_type]
                    accumulated_qty = production_qty + carry_over
                    carry_over_by_saddle[saddle_type] = accumulated_qty - final_shipment
            else:
                for saddle_type in all_saddle_types:
                    shipment_qty_by_date_and_saddle[(current_date, saddle_type)] = 0.0
                    production_qty = production_by_saddle[saddle_type]
                    carry_over = carry_over_by_saddle[saddle_type]
                    carry_over_by_saddle[saddle_type] = production_qty + carry_over
        
        # ============================================================================
        # PHASE 3: Sammle alle Tage mit Warenausgang > 0
        # ============================================================================
        shipment_dates = set()
        for (ship_date, saddle_type), qty in shipment_qty_by_date_and_saddle.items():
            if qty > 0:
                shipment_dates.add(ship_date)
        shipment_dates = sorted(list(shipment_dates))
        
        if not shipment_dates:
            st.info("Noch keine Ware verschifft.")
        else:
            # ============================================================================
            # PHASE 4: Berechne Transport-Phasen für jeden Warenausgang
            # ============================================================================
            shipments_data: Dict[date, Dict] = {}
            
            for shipment_date in shipment_dates:
                # Berechne Gesamtmenge und Sattel-Aufteilung für diesen Tag
                total_qty = 0.0
                saddle_quantities: Dict[str, float] = {saddle: 0.0 for saddle in all_saddle_types}
                
                for saddle_type in all_saddle_types:
                    qty = shipment_qty_by_date_and_saddle.get((shipment_date, saddle_type), 0.0)
                    total_qty += qty
                    saddle_quantities[saddle_type] = qty
                
                if total_qty > 0:
                    # Transport-Phasen berechnen
                    # LKW Abfahrt (CN) = Warenausgang-Tag
                    truck_china_start_date = shipment_date
                    
                    # Hafen Ankunft (CN) = LKW Abfahrt + 2 Arbeitstage
                    truck_china_start_day = (truck_china_start_date - date(2026, 1, 1)).days
                    truck_china_end_day = manager._add_workdays(truck_china_start_day, 2)
                    port_arrival_date = workday_calc.get_date_from_day(truck_china_end_day)
                    
                    # Schiffsabfahrt (CN) = Nächster Mittwoch nach Hafen Ankunft
                    days_until_wednesday = (2 - port_arrival_date.weekday()) % 7
                    if days_until_wednesday == 0 and port_arrival_date.weekday() == 2:
                        ship_departure_date = port_arrival_date
                    else:
                        ship_departure_date = port_arrival_date + timedelta(days=days_until_wednesday)
                    
                    # Prüfe Lieferprobleme-Szenarien
                    ship_departure_day = (ship_departure_date - date(2026, 1, 1)).days
                    delivery_problems = []
                    if st.session_state.scenario_manager:
                        delivery_problems = st.session_state.scenario_manager.get_delivery_problem_scenarios(ship_departure_day)
                    
                    delay_days = 0
                    loss_factor = 1.0
                    for scenario in delivery_problems:
                        if scenario.component_type == 'saddles':
                            delay_days = max(delay_days, scenario.delay_days)
                            loss_factor *= (1.0 - scenario.loss_percentage)
                    
                    # Schiffsankunft (HH) = Schiffsabfahrt + 30 Kalendertage + Verspätung
                    ship_arrival_date = ship_departure_date + timedelta(days=30 + delay_days)
                    
                    # LKW Start (DE) = Schiffsankunft
                    truck_de_start_date = ship_arrival_date
                    
                    # Ankunft Werk (Physisch) (DE) = LKW Start + 2 Arbeitstage
                    truck_de_start_day = (truck_de_start_date - date(2026, 1, 1)).days
                    truck_de_end_day = manager._add_workdays(truck_de_start_day, 2)
                    physical_arrival_date = workday_calc.get_date_from_day(truck_de_end_day)
                    
                    # Verfügbar (Lager) (DE) = Ankunft Werk + 1 Tag
                    available_date = physical_arrival_date + timedelta(days=1)
                    
                    # Tatsächliche Ankunft LKW (DE) = Geplante Ankunft (kann durch Verspätungen abweichen)
                    # Aktuell gleich wie geplante Ankunft, kann später durch Szenarien angepasst werden
                    actual_arrival_date = physical_arrival_date
                    
                    shipments_data[shipment_date] = {
                        "Abfahrt LKW (CN)": truck_china_start_date,
                        "Ankunft LKW (CN)": port_arrival_date,
                        "Abfahrt Schiff (CN)": ship_departure_date,
                        "Ankunft Schiff (HH)": ship_arrival_date,
                        "Abfahrt LKW (DE)": truck_de_start_date,
                        "Geplante Ankunft LKW (DE)": physical_arrival_date,
                        "Tatsächliche Ankunft LKW (DE)": actual_arrival_date,
                        "Verfügbar im Lager (DE)": available_date,
                        "Menge Gesamt": int(total_qty * loss_factor),
                        "saddle_quantities": {saddle: int(qty * loss_factor) for saddle, qty in saddle_quantities.items()}
                    }
            
            # Speichere shipments_data in session_state für Materiallager
            st.session_state.inbound_shipments_data = shipments_data
            
            # ============================================================================
            # PHASE 5: Erstelle horizontale Tabelle - Alle Tage ab 14.11.2025
            # ============================================================================
            # Transport-Phasen (erste Spalte) - mit Flaggen statt Länderkürzel
            transport_phases = [
                "Abfahrt LKW 🇨🇳",
                "Ankunft LKW 🇨🇳",
                "Abfahrt Schiff 🇨🇳",
                "Ankunft Schiff 🇩🇪",
                "Abfahrt LKW 🇩🇪",
                "Geplante Ankunft LKW 🇩🇪",
                "Tatsächliche Ankunft LKW 🇩🇪",
                "Verfügbar im Lager 🇩🇪",
                "Menge Gesamt"
            ]
            for saddle_name in sorted(all_saddle_types):
                transport_phases.append(saddle_name)
            
            # Erstelle alle Tage ab 14.11.2025
            start_date_display = date(2025, 11, 14)
            end_date_display = date(2026, 12, 31)
            all_dates = []
            current_date = start_date_display
            while current_date <= end_date_display:
                all_dates.append(current_date)
                current_date += timedelta(days=1)
            
            # Erstelle DataFrame für horizontale Struktur
            table_data = {}
            
            # Erste Spalte: Transport-Phasen
            table_data["Transport-Phase"] = transport_phases
            
            # Ab Spalte 2: Jede Spalte = ein Tag (auch ohne Daten)
            weekday_names = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
            
            for display_date in all_dates:
                weekday = display_date.weekday()
                weekday_abbr = weekday_names[weekday]
                
                # Spaltenname: Wochentag, Datum (mit Komma getrennt)
                col_name = f"{weekday_abbr}, {display_date.strftime('%d.%m.%Y')}"
                
                # Werte für diese Spalte
                col_values = []
                
                # Prüfe ob an diesem Tag ein Warenausgang stattfindet
                if display_date in shipments_data:
                    shipment = shipments_data[display_date]
                    for phase in transport_phases:
                        if phase == "Abfahrt LKW 🇨🇳":
                            col_values.append(shipment["Abfahrt LKW (CN)"].strftime('%d.%m.%Y'))
                        elif phase == "Ankunft LKW 🇨🇳":
                            col_values.append(shipment["Ankunft LKW (CN)"].strftime('%d.%m.%Y'))
                        elif phase == "Abfahrt Schiff 🇨🇳":
                            col_values.append(shipment["Abfahrt Schiff (CN)"].strftime('%d.%m.%Y'))
                        elif phase == "Ankunft Schiff 🇩🇪":
                            col_values.append(shipment["Ankunft Schiff (HH)"].strftime('%d.%m.%Y'))
                        elif phase == "Abfahrt LKW 🇩🇪":
                            col_values.append(shipment["Abfahrt LKW (DE)"].strftime('%d.%m.%Y'))
                        elif phase == "Geplante Ankunft LKW 🇩🇪":
                            col_values.append(shipment["Geplante Ankunft LKW (DE)"].strftime('%d.%m.%Y'))
                        elif phase == "Tatsächliche Ankunft LKW 🇩🇪":
                            col_values.append(shipment["Tatsächliche Ankunft LKW (DE)"].strftime('%d.%m.%Y'))
                        elif phase == "Verfügbar im Lager 🇩🇪":
                            col_values.append(shipment["Verfügbar im Lager (DE)"].strftime('%d.%m.%Y'))
                        elif phase == "Menge Gesamt":
                            col_values.append(str(shipment["Menge Gesamt"]))
                        elif phase in shipment["saddle_quantities"]:
                            col_values.append(str(shipment["saddle_quantities"][phase]))
                        else:
                            col_values.append("0")
                else:
                    # Kein Warenausgang an diesem Tag - alle Werte leer
                    for phase in transport_phases:
                        col_values.append("")
                
                table_data[col_name] = col_values
            
            df_inbound = pd.DataFrame(table_data)
            
            # Metriken
            total_on_water = 0
            next_arrival = None
            current_day = (date.today() - date(2026, 1, 1)).days if date.today() >= date(2026, 1, 1) else 0
            
            for shipment_date, shipment in shipments_data.items():
                available_day = (shipment["Verfügbar im Lager (DE)"] - date(2026, 1, 1)).days
                ship_departure_day = (shipment["Abfahrt Schiff (CN)"] - date(2026, 1, 1)).days
                
                if ship_departure_day <= current_day and available_day > current_day:
                    total_on_water += shipment["Menge Gesamt"]
                    if shipment["Ankunft Schiff (HH)"] and (next_arrival is None or shipment["Ankunft Schiff (HH)"] < next_arrival):
                        next_arrival = shipment["Ankunft Schiff (HH)"]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Ware auf See / Unterwegs", f"{int(total_on_water):,} Stk")
        col2.metric("Nächste Schiffsankunft", str(next_arrival.strftime('%d.%m.%Y')) if next_arrival else "-")
        col3.metric("Anzahl Container unterwegs", f"{int(total_on_water / 500) if total_on_water > 0 else 0} Container")
        
        st.divider()
        
        # Tabelle anzeigen
        st.subheader("Detaillierte Lieferübersicht")
        
        # Farblegende
        col1, col2 = st.columns([1, 1])
        with col2:
            st.markdown("""
            <div style="text-align: right; margin-bottom: 10px;">
                <span style="background-color: #ffebee; padding: 2px 8px; border-radius: 3px; margin-left: 5px;">Wochenende</span>
                <span style="background-color: #c8e6c9; padding: 2px 8px; border-radius: 3px; margin-left: 5px;">Feiertag</span>
            </div>
            """, unsafe_allow_html=True)
        
        # Berechne Anzahl der Zeilen mit Inhalt (für dynamische Höhe)
        rows_with_content = len(transport_phases)
        # Höhe: ~40px pro Zeile + Header (etwas mehr Platz für bessere Sichtbarkeit)
        calculated_height = rows_with_content * 40 + 60
        
        # Erstelle HTML-Tabelle mit fixierter erster Spalte
        html_table = """
            <style>
            .inbound-table-container {
                overflow-x: auto;
                max-height: """ + str(calculated_height) + """px;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
            }
            .inbound-table {
                border-collapse: collapse;
                width: 100%;
                font-size: 14px;
            }
            .inbound-table th,
            .inbound-table td {
                padding: 8px 12px;
                text-align: left;
                border: 1px solid #e0e0e0;
            }
            .inbound-table th {
                background-color: #f0f2f6;
                font-weight: 600;
                position: sticky;
                top: 0;
                z-index: 10;
            }
            .inbound-table th:first-child,
            .inbound-table td:first-child {
                position: sticky;
                left: 0;
                z-index: 20;
                background-color: #f0f2f6;
                border-right: 2px solid #e0e0e0;
                min-width: 250px;
                white-space: nowrap;
            }
            .inbound-table tbody td:first-child {
                background-color: white;
            }
            .inbound-table tbody tr td.empty-cell {
                background-color: #ffebee;
            }
            .inbound-table tbody tr td:first-child.empty-cell {
                background-color: #ffebee;
            }
            </style>
            <div class="inbound-table-container">
            <table class="inbound-table">
            <thead>
            <tr>
            """
        
        # Header-Zeile
        for col in df_inbound.columns:
            html_table += f'<th>{col}</th>'
        html_table += """
            </tr>
            </thead>
            <tbody>
            """
        
        # Daten-Zeilen
        for idx, row in df_inbound.iterrows():
            html_table += "<tr>"
            for col_idx, col_name in enumerate(df_inbound.columns):
                value = row[col_name]
                cell_class = 'empty-cell' if (value == "" or value is None or str(value).strip() == "") else ''
                cell_value = str(value) if value != "" and value is not None else ""
                html_table += f'<td class="{cell_class}">{cell_value}</td>'
            html_table += "</tr>"
        
        html_table += """
            </tbody>
            </table>
            </div>
            """
        
        # Zeige HTML-Tabelle
        st.markdown(html_table, unsafe_allow_html=True)
