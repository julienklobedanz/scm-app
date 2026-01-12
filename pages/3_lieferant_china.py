"""
Lieferant China-Seite
Zeigt Produktion und Transport zum Hafen Dengwong - je Sattel-Typ eine Tabelle
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
    
    # ============================================================================
    # PHASE 1: Pre-Processing - Sammle alle Daten für alle Sattel-Typen
    # ============================================================================
    # Initialisiere shipment_qty_by_date_and_saddle (wird in Phase 2 gefüllt)
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
        # Key: (date, saddle_type), Value: (production_qty, stock_at_port)
        production_by_date_and_saddle: Dict[Tuple[date, str], float] = {}
        stock_by_date_and_saddle: Dict[Tuple[date, str], float] = {}
        
        # Iteriere über alle Tage und alle Sattel-Typen, um Produktionsmenge und Warenbestand zu sammeln
        for saddle_type in all_saddle_types:
            # Warenbestand vom Vortag (für diesen Sattel-Typ)
            stock_at_port_vortag = 0.0
            
            # Speichere Bestellmengen pro Bestellungstag für "Freigegebene Bestellungen"
            order_quantities_by_order_date: Dict[date, Tuple[float, date, date]] = {}
            
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
                lead_time = 49
                demand_day = order_day_for_date + lead_time if order_day_for_date is not None else None
                
                if demand_day is not None and demand_day >= 0 and demand_day < 365:
                    is_workday = workday_calc.is_workday(demand_day)
                    
                    if is_workday:
                        # Hole Nachfrage aus session_state (von Volumenplanung)
                        if 'daily_demand_data' in st.session_state and demand_day in st.session_state.daily_demand_data:
                            product_demands = st.session_state.daily_demand_data[demand_day]
                            # Verteile auf Sattel-Typen basierend auf BOM
                            for product, demand_qty in product_demands.items():
                                product_saddle = MasterData.BOM[product]['saddle']
                                if product_saddle == saddle_type:
                                    daily_order_qty += demand_qty
                        else:
                            # Fallback: Berechne neu (falls Volumenplanung noch nicht geladen wurde)
                            month = MasterData.get_month_from_day(demand_day)
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
                                    daily_order_qty += demand_qty
                
                # Prüfe ob chinesischer Feiertag oder Wochenende
                weekday = current_date.weekday()
                is_weekend = weekday >= 5
                is_chinese_holiday = HolidaysConfig.is_holiday(current_date, 'CN')
                is_weekend_or_holiday = is_weekend or is_chinese_holiday
                
                # Freigabedatum: Nächster Arbeitstag nach Bestellung
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
                
                # Berechne Produktionsdatum
                production_date_for_order = None
                if daily_order_qty > 0 and released_date is not None:
                    # Finde das Produktionsdatum aus dem transport_status
                    for (order_day, order_id), status in manager.transport_status.items():
                        order_date_from_status = workday_calc.get_date_from_day(order_day)
                        if order_date_from_status == current_date:
                            if 'production_end_day' in status:
                                production_date_for_order = workday_calc.get_date_from_day(status['production_end_day'])
                                break
                    
                    # Falls nicht gefunden, berechne es
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
                    
                    if released_date is not None:
                        if production_date_for_order is None:
                            # Nochmal berechnen
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
                        
                        order_quantities_by_order_date[current_date] = (daily_order_qty, released_date, production_date_for_order)
                
                # Berechne Produktionsmenge für diesen Tag
                production_qty = 0.0
                for order_date, (order_qty, released_date_for_order, production_date_for_order) in order_quantities_by_order_date.items():
                    if production_date_for_order == current_date:
                        production_qty += order_qty
                
                # Berechne Warenbestand (vor Warenausgang)
                available_stock = stock_at_port_vortag + production_qty
                
                # Speichere Produktionsmenge und verfügbaren Bestand
                production_by_date_and_saddle[(current_date, saddle_type)] = production_qty
                stock_by_date_and_saddle[(current_date, saddle_type)] = available_stock
                
                # Aktualisiere Warenbestand für nächsten Tag (ohne Warenausgang, der wird später berechnet)
                # Wir speichern hier nur den verfügbaren Bestand vor Warenausgang
                stock_at_port_vortag = available_stock
        
        # ============================================================================
        # PHASE 2: Losgrößen-Logik für Warenausgang
        # ============================================================================
        lot_size = MasterData.CHINA_SUPPLIER['Saddles']['lot_size']  # 500
        
        # Carry-Over pro Sattel-Typ (Key: saddle_type, Value: carry_over_menge)
        carry_over_by_saddle: Dict[str, float] = {saddle: 0.0 for saddle in all_saddle_types}
        
        for day_offset in range(total_days):
            current_date = start_date_log + timedelta(days=day_offset)
            day = (current_date - start_date_simulation).days
            
            # Prüfe ob Werktag und kein Ausfall/Feiertag
            weekday = current_date.weekday()
            is_weekend = weekday >= 5
            is_chinese_holiday = HolidaysConfig.is_holiday(current_date, 'CN')
            is_weekend_or_holiday = is_weekend or is_chinese_holiday
            
            # Prüfe Störung
            machine_breakdown = False
            if day is not None and day >= 0:
                supplier_breakdowns = st.session_state.scenario_manager.get_supplier_breakdown_scenarios(day)
                for scenario in supplier_breakdowns:
                    if scenario.component_type in ['saddles', 'all']:
                        if day >= scenario.start_day and day <= scenario.end_day:
                            machine_breakdown = True
                            break
            
            # Wenn Wochenende, Feiertag oder Störung: Losgröße = 0, Warenausgang = 0
            if is_weekend_or_holiday or machine_breakdown:
                for saddle_type in all_saddle_types:
                    shipment_qty_by_date_and_saddle[(current_date, saddle_type)] = 0.0
                continue
            
            # Berechne Produktionsmenge für alle Sattel-Typen an diesem Tag
            production_by_saddle: Dict[str, float] = {}
            available_stock_by_saddle: Dict[str, float] = {}
            
            for saddle_type in all_saddle_types:
                production_by_saddle[saddle_type] = production_by_date_and_saddle.get((current_date, saddle_type), 0.0)
                available_stock_by_saddle[saddle_type] = stock_by_date_and_saddle.get((current_date, saddle_type), 0.0)
            
            # Berechne Gesamtkumulation (Produktionsmenge + Carry-Over)
            total_accumulated = 0.0
            for saddle_type in all_saddle_types:
                production_qty = production_by_saddle[saddle_type]
                carry_over = carry_over_by_saddle[saddle_type]
                total_accumulated += production_qty + carry_over
            
            # Berechne Losgröße
            if total_accumulated < lot_size:
                losgroesse = 0
            else:
                losgroesse = int(total_accumulated / lot_size) * lot_size
            
            # Berechne verfügbaren Gesamtbestand (Summe über alle Sattel-Typen)
            total_available_stock = sum(available_stock_by_saddle.values())
            
            # Begrenze Losgröße durch verfügbaren Bestand
            losgroesse = min(losgroesse, total_available_stock)
            
            # Wenn Losgröße > 0, verteile auf Sattel-Typen
            if losgroesse > 0:
                # Berechne ungerundete Anteile
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
                
                # Berechne abgerundete Anteile
                rounded_shares: Dict[str, int] = {}
                sum_rounded = 0
                for saddle_type in all_saddle_types:
                    rounded_share = int(unrounded_shares[saddle_type])
                    rounded_shares[saddle_type] = rounded_share
                    sum_rounded += rounded_share
                
                # Berechne Differenz
                differenz = losgroesse - sum_rounded
                
                # Verteile Differenz auf Sattel-Typen mit höchstem Dezimalrest
                if differenz > 0:
                    # Sortiere Sattel-Typen nach Dezimalrest (höchster zuerst)
                    decimal_rests = []
                    for saddle_type in all_saddle_types:
                        decimal_rest = unrounded_shares[saddle_type] - rounded_shares[saddle_type]
                        production_qty = production_by_saddle[saddle_type]
                        carry_over = carry_over_by_saddle[saddle_type]
                        remaining_capacity = (production_qty + carry_over) - rounded_shares[saddle_type]
                        # Zusätzlich: Begrenze durch verfügbaren Bestand
                        available_stock = available_stock_by_saddle[saddle_type]
                        remaining_capacity = min(remaining_capacity, available_stock - rounded_shares[saddle_type])
                        decimal_rests.append((saddle_type, decimal_rest, remaining_capacity))
                    
                    # Sortiere nach Dezimalrest (absteigend), dann nach verbleibender Kapazität
                    decimal_rests.sort(key=lambda x: (x[1], x[2]), reverse=True)
                    
                    # Verteile Differenz
                    for i, (saddle_type, decimal_rest, remaining_capacity) in enumerate(decimal_rests):
                        if differenz > 0 and remaining_capacity > 0:
                            # Excel-Logik: Wenn Differenz <= Restkapazität, dann Differenz, sonst Restkapazität
                            if differenz <= remaining_capacity:
                                extra = differenz
                            else:
                                extra = remaining_capacity
                            rounded_shares[saddle_type] += extra
                            differenz -= extra
                
                # Finaler Warenausgang pro Sattel-Typ (begrenzt durch verfügbaren Bestand)
                for saddle_type in all_saddle_types:
                    final_shipment = rounded_shares[saddle_type]
                    available_stock = available_stock_by_saddle[saddle_type]
                    # Stelle sicher, dass Warenausgang nicht größer als verfügbarer Bestand ist
                    final_shipment = min(final_shipment, available_stock)
                    shipment_qty_by_date_and_saddle[(current_date, saddle_type)] = final_shipment
                    
                    # Berechne neues Carry-Over
                    production_qty = production_by_saddle[saddle_type]
                    carry_over = carry_over_by_saddle[saddle_type]
                    accumulated_qty = production_qty + carry_over
                    carry_over_by_saddle[saddle_type] = accumulated_qty - final_shipment
            else:
                # Losgröße = 0, kein Warenausgang
                for saddle_type in all_saddle_types:
                    shipment_qty_by_date_and_saddle[(current_date, saddle_type)] = 0.0
                    # Carry-Over bleibt erhalten (wird später aktualisiert)
                    production_qty = production_by_saddle[saddle_type]
                    carry_over = carry_over_by_saddle[saddle_type]
                    carry_over_by_saddle[saddle_type] = production_qty + carry_over
    
    # ============================================================================
    # PHASE 3: Erstelle Tabellen pro Sattel-Typ mit korrekten Warenausgangs-Werten
    # ============================================================================
    # Erstelle eine Tabelle pro Sattel-Typ
    for saddle_type in all_saddle_types:
        st.subheader(f"📦 {saddle_type}")
        
        # Rekonstruiere tägliche Daten für diesen Sattel-Typ
        daily_data = []
        start_date_simulation = date(2026, 1, 1)
        
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
        end_date_log = date(2026, 12, 31)
        total_days = (end_date_log - start_date_log).days + 1
        
        # Speichere Bestellmengen pro Bestellungstag für "Freigegebene Bestellungen"
        # Key: Bestellungstag (date), Value: (Bestellmenge für diesen Sattel-Typ, Freigabedatum, Produktionsdatum)
        order_quantities_by_order_date: Dict[date, Tuple[float, date, date]] = {}
        
        # Warenbestand vom Vortag (für einfache Berechnung: Warenbestand heute = Warenbestand Vortag + Produktion heute - Warenausgang heute)
        stock_at_port_vortag = 0.0
        
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
                is_workday = workday_calc.is_workday(demand_day)
                
                if is_workday:
                    # Hole Nachfrage aus session_state (von Volumenplanung)
                    if 'daily_demand_data' in st.session_state and demand_day in st.session_state.daily_demand_data:
                        product_demands = st.session_state.daily_demand_data[demand_day]
                        # Verteile auf Sattel-Typen basierend auf BOM
                        for product, demand_qty in product_demands.items():
                            product_saddle = MasterData.BOM[product]['saddle']
                            if product_saddle == saddle_type:
                                saddle_breakdown[product] = demand_qty
                                daily_order_qty += demand_qty
                    else:
                        # Fallback: Berechne neu (falls Volumenplanung noch nicht geladen wurde)
                        month = MasterData.get_month_from_day(demand_day)
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
            
            # Prüfe ob chinesischer Feiertag oder Wochenende (muss VOR Verwendung definiert werden)
            weekday = current_date.weekday()
            weekday_names = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
            weekday_abbr = weekday_names[weekday]
            is_weekend = weekday >= 5
            is_chinese_holiday = HolidaysConfig.is_holiday(current_date, 'CN')
            is_weekend_or_holiday = is_weekend or is_chinese_holiday
            
            # Freigabedatum: Nächster Arbeitstag nach Bestellung (berücksichtigt NUR chinesische Feiertage, NICHT deutsche!)
            released_date = None
            if daily_order_qty > 0:
                # Verwende chinesische Feiertage für Freigabe in China
                chinese_holidays = HolidaysConfig.get_holidays_for_year(2026, 'CN')
                for i in range(1, 8):
                    check_date = current_date + timedelta(days=i)
                    # Prüfe ob Arbeitstag: Nur Wochenende (Sa/So) und chinesische Feiertage zählen
                    # DEUTSCHE Feiertage werden NICHT berücksichtigt (chinesische Perspektive!)
                    weekday_check = check_date.weekday()  # 0=Mo, 6=So
                    is_weekend_check = weekday_check >= 5  # Samstag oder Sonntag
                    is_chinese_holiday_check = check_date in chinese_holidays
                    # Arbeitstag = nicht Wochenende und nicht chinesischer Feiertag
                    if not is_weekend_check and not is_chinese_holiday_check:
                        released_date = check_date
                        break
            
            # Berechne Produktionsdatum für diese Bestellung (4 Arbeitstage nach Freigabedatum, mit chinesischen Feiertagen)
            production_date_for_order = None
            if daily_order_qty > 0 and released_date is not None:
                # Finde das Produktionsdatum aus dem transport_status
                for (order_day, order_id), status in manager.transport_status.items():
                    order_date_from_status = workday_calc.get_date_from_day(order_day)
                    if order_date_from_status == current_date:
                        if 'production_end_day' in status:
                            production_date_for_order = workday_calc.get_date_from_day(status['production_end_day'])
                            break
                
                # Falls Produktionsdatum nicht im transport_status gefunden wurde, berechne es aus released_date
                if production_date_for_order is None and released_date is not None:
                    # Berechne Produktionsdatum: 4 Arbeitstage nach Freigabedatum (mit chinesischen Feiertagen)
                    # WICHTIG: Nur chinesische Feiertage berücksichtigen, NICHT deutsche!
                    released_day = (released_date - date(2026, 1, 1)).days
                    chinese_holidays = HolidaysConfig.get_holidays_for_year(2026, 'CN')
                    production_start_day = released_day
                    # 4 Arbeitstage nach Freigabedatum (Start-Tag zählt nicht mit)
                    production_end_day = production_start_day + 1
                    workdays_added = 0
                    max_iterations = 20  # Sicherheit gegen Endlosschleife
                    iteration = 0
                    while workdays_added < 4 and iteration < max_iterations:
                        iteration += 1
                        check_date = workday_calc.get_date_from_day(production_end_day)
                        # Prüfe ob Arbeitstag: Nur Wochenende (Sa/So) und chinesische Feiertage zählen
                        # DEUTSCHE Feiertage werden NICHT berücksichtigt (chinesische Perspektive!)
                        weekday_check = check_date.weekday()  # 0=Mo, 6=So
                        is_weekend_check = weekday_check >= 5  # Samstag oder Sonntag
                        is_chinese_holiday_check = check_date in chinese_holidays
                        # Arbeitstag = nicht Wochenende und nicht chinesischer Feiertag
                        if not is_weekend_check and not is_chinese_holiday_check:
                            workdays_added += 1
                        if workdays_added < 4:
                            production_end_day += 1
                    if iteration < max_iterations:
                        production_date_for_order = workday_calc.get_date_from_day(production_end_day)
                
                # Speichere Bestellmenge, Freigabedatum und Produktionsdatum für diesen Bestellungstag
                # WICHTIG: Speichere immer, wenn released_date existiert, auch wenn production_date_for_order None ist
                # (production_date_for_order wird dann später berechnet, wenn es benötigt wird)
                if released_date is not None:
                    # Falls production_date_for_order noch None ist, versuche es nochmal zu berechnen
                    if production_date_for_order is None:
                        # Berechne Produktionsdatum: 4 Arbeitstage nach Freigabedatum (mit chinesischen Feiertagen)
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
                    
                    # Speichere nur, wenn production_date_for_order berechnet werden konnte
                    # Falls nicht, speichere mit None (wird später ignoriert)
                    order_quantities_by_order_date[current_date] = (daily_order_qty, released_date, production_date_for_order)
            
            # Freigegebene Bestellungen: Excel-Formel: SUMMENPRODUKT((Freigabedatum = F12) * (Bestellmenge))
            # Excel: Summiert die Bestellmengen aus Zeile 15 (Bestelleingang), wo Zeile 16 (Freigabedatum) = aktuelles Datum
            # Wenn Wochenende oder Feiertag: 0, sonst summiere alle Bestellmengen, deren Freigabedatum = aktuelles Datum
            released_orders_qty = 0.0
            if not is_weekend_or_holiday:
                # Summiere alle Bestellmengen, deren Freigabedatum = aktuelles Datum
                for order_date, (order_qty, released_date_for_order, production_date_for_order) in order_quantities_by_order_date.items():
                    if released_date_for_order == current_date:
                        released_orders_qty += order_qty
            
            # Produktionsdaten: Excel summiert die "Freigegebene Bestellungen"-Werte, deren Produktionsdatum = aktuelles Datum
            # WICHTIG: Produktionsmenge bezieht sich auf FREIGEGEBENE Bestellungen, nicht auf Bestelleingang!
            # Die Produktion startet 4 Arbeitstage nach dem Freigabedatum (released_day), nicht nach dem Bestelldatum
            # WICHTIG: Wir müssen die "Freigegebene Bestellungen" verwenden, nicht die Bestellmenge!
            # Dafür müssen wir für jedes Bestelldatum prüfen, ob dessen Freigabedatum ein Arbeitstag war
            production_date = None
            production_qty = 0.0
            # Summiere alle "Freigegebene Bestellungen"-Werte, deren Produktionsdatum = aktuelles Datum
            # WICHTIG: Die "Freigegebene Bestellungen" ist die Bestellmenge, wenn das Freigabedatum ein Arbeitstag war
            for order_date, (order_qty, released_date_for_order, production_date_for_order) in order_quantities_by_order_date.items():
                if production_date_for_order == current_date and released_date_for_order is not None:
                    # Prüfe ob das Freigabedatum ein Arbeitstag war (nicht Wochenende/Feiertag)
                    # Wenn released_date_for_order existiert, wurde die Bestellung freigegeben
                    # Die freigegebene Menge ist gleich der Bestellmenge (order_qty)
                    # ABER: Nur wenn das Freigabedatum ein Arbeitstag war!
                    # Prüfe ob released_date_for_order ein Arbeitstag war
                    weekday_released = released_date_for_order.weekday()
                    is_weekend_released = weekday_released >= 5
                    chinese_holidays = HolidaysConfig.get_holidays_for_year(2026, 'CN')
                    is_chinese_holiday_released = released_date_for_order in chinese_holidays
                    is_workday_released = not is_weekend_released and not is_chinese_holiday_released
                    
                    if is_workday_released:
                        production_qty += order_qty
                    if production_date is None and is_workday_released:
                        production_date = production_date_for_order
            
            # Warenausgang: Verwende die berechnete Losgrößenlogik aus Phase 2
            shipment_qty = shipment_qty_by_date_and_saddle.get((current_date, saddle_type), 0.0)
            
            # Warenbestand: Einfache Formel: Warenbestand (heute) = Warenbestand (Vortag) + Produktionsmenge (heute) - Warenausgang (heute)
            stock_at_port = stock_at_port_vortag + production_qty - shipment_qty
            # Stelle sicher, dass Warenbestand nicht negativ wird
            stock_at_port = max(0.0, stock_at_port)
            # Speichere für nächsten Tag
            stock_at_port_vortag = stock_at_port
            
            # Störung: Prüfe Komplikationen (Standard: "nein", außer Szenario aktiv)
            machine_breakdown = "nein"
            if day is not None and day >= 0:
                supplier_breakdowns = st.session_state.scenario_manager.get_supplier_breakdown_scenarios(day)
                for scenario in supplier_breakdowns:
                    if scenario.component_type in ['saddles', 'all']:
                        if day >= scenario.start_day and day <= scenario.end_day:
                            machine_breakdown = "ja"
                            break
            
            # Produktionsdatum: Finde das Produktionsdatum der Bestellungen, die an diesem Tag freigegeben wurden
            # WICHTIG: Nur anzeigen, wenn tatsächlich Bestellungen freigegeben wurden (released_orders_qty > 0)!
            # Das Produktionsdatum sollte aus den Bestellungen kommen, die an diesem Tag freigegeben wurden
            production_date_for_order = None
            if released_orders_qty > 0:
                # Finde das Produktionsdatum aus den Bestellungen, die an diesem Tag freigegeben wurden
                # Verwende die bereits gespeicherten Daten aus order_quantities_by_order_date
                for order_date, (order_qty, released_date_for_order, production_date_for_order_stored) in order_quantities_by_order_date.items():
                    if released_date_for_order == current_date and production_date_for_order_stored is not None:
                        # Verwende das Produktionsdatum der ersten Bestellung, die an diesem Tag freigegeben wurde
                        production_date_for_order = production_date_for_order_stored
                        break
            
            # Erstelle Log-Eintrag
            log_entry = {
                'Wochentag': weekday_abbr,
                'Datum': current_date.strftime('%d.%m.%Y'),
                'Bestelleingang': round(daily_order_qty) if daily_order_qty > 0 else '',
                'Freigabedatum': released_date.strftime('%d.%m.%Y') if released_date else '',
                'Freigegebene Bestellungen': round(released_orders_qty) if released_orders_qty > 0 else 0,
                'Störung': machine_breakdown,
                'Produktionsdatum': production_date_for_order.strftime('%d.%m.%Y') if production_date_for_order else '',
                'Produktionsmenge': round(production_qty) if production_qty > 0 else 0,
                'Warenausgang': round(shipment_qty) if shipment_qty > 0 else 0,
                'Warenbestand': round(stock_at_port),
                'Is_Weekend': is_weekend,
                'Is_Holiday': is_chinese_holiday
            }
            
            daily_data.append(log_entry)
        
        if daily_data:
            df_saddle = pd.DataFrame(daily_data)
            
            # Zeige ALLE Zeilen (nicht gefiltert)
            df_saddle = df_saddle.reset_index(drop=True)
            
            # Spaltenreihenfolge
            display_columns = [
                'Wochentag',
                'Datum',
                'Bestelleingang',
                'Freigabedatum',
                'Freigegebene Bestellungen',
                'Störung',
                'Produktionsdatum',
                'Produktionsmenge',
                'Warenausgang',
                'Warenbestand'
            ]
            
            df_display = df_saddle[display_columns].copy()
            
            # Speichere Flags für Wochenende und Feiertage
            weekend_flags = df_saddle['Is_Weekend'].values
            holiday_flags = df_saddle['Is_Holiday'].values
            
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
                styles = [''] * len(row)
                row_idx = row.name
                # Wochenende hat Priorität (wenn beides, dann Wochenende = rot)
                if weekend_flags[row_idx]:
                    return ['background-color: #ffebee' for _ in row]
                elif holiday_flags[row_idx]:
                    return ['background-color: #c8e6c9' for _ in row]
                return styles
            
            styled_df = df_display.style.apply(style_row, axis=1)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        else:
            st.info(f"Keine Daten für {saddle_type} im ausgewählten Zeitraum.")
        
        st.divider()
