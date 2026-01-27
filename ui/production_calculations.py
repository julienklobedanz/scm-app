"""
Production Calculations
Berechnungslogik für Produktionslogs (ohne UI-Rendering)
"""

import streamlit as st
import pandas as pd
import math
from datetime import date, datetime, timedelta
from typing import Dict
from config.master_data import MasterData
from simulation.workday_calculator import WorkdayCalculator
from models.scenarios import WaterDamageScenario


def _get_backlog_from_previous_workday(
    production_logs: Dict[str, pd.DataFrame],
    product: str,
    day: int,
    planning_year: int,
    workday_calc: WorkdayCalculator
) -> float:
    """
    Holt Backlog vom vorherigen Arbeitstag aus den Produktionslogs.
    
    Args:
        production_logs: Dict[product] -> DataFrame mit Produktionslogs
        product: Produktname
        day: Aktueller Tag (0-basiert)
        planning_year: Planungsjahr
        workday_calc: WorkdayCalculator
    
    Returns:
        Backlog vom vorherigen Arbeitstag (0.0 wenn nicht gefunden)
    """
    if product not in production_logs:
        return 0.0
    
    df = production_logs[product]
    if df.empty or 'Datum' not in df.columns or 'Backlog' not in df.columns:
        return 0.0
    
    # Finde vorherigen Arbeitstag
    prev_day = day - 1
    while prev_day >= 0:
        if workday_calc.is_workday(prev_day):
            break
        prev_day -= 1
    
    if prev_day < 0:
        return 0.0
    
    # Finde Log-Eintrag für prev_day
    prev_date = workday_calc.get_date_from_day(prev_day)
    prev_date_str = prev_date.strftime(MasterData.DATE_FORMAT)
    
    matching_rows = df[df['Datum'] == prev_date_str]
    if not matching_rows.empty:
        backlog = matching_rows.iloc[0].get('Backlog', 0)
        try:
            return float(backlog) if backlog > 0 else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    return 0.0


def _recalculate_all_products_with_rank_logic(
    day: int,
    product_demands_new: Dict[str, int],
    saddle_available_new: Dict[str, float],
    daily_capacity: float,
    production_logs: Dict[str, pd.DataFrame],
    planning_year: int,
    workday_calc: WorkdayCalculator,
    backlog_by_product: Dict[str, float] = None
) -> Dict[str, int]:
    """
    Repliziert die komplette statische Produktionslogik für ALLE Produkte
    mit aktualisierten Inputs (Nachfrage mit Marketing, korrigierte Materialverfügbarkeit).
    
    WICHTIG: Diese Funktion implementiert die EXAKTE Logik aus production_planner.py,
    nur mit aktualisierten Inputs.
    
    Args:
        day: Tag-Index (0-basiert)
        product_demands_new: Dict[product] -> demand (mit Marketing)
        saddle_available_new: Dict[saddle] -> stock (korrigiert)
        daily_capacity: Tageskapazität
        production_logs: Statische Logs (für Backlog-Informationen)
        planning_year: Planungsjahr
        workday_calc: WorkdayCalculator
        previously_calculated_production: Optional: Bereits berechnete Produktion für vorherige Tage
                                          (für korrekte Backlog-Berechnung)
    
    Returns:
        Dict[product] -> "Tatsächliche PM" (mit Rang-Logik)
    """
    # Schritt 1: Hole Backlog vom Vortag
    # KRITISCH: Wenn backlog_by_product als Parameter übergeben wurde, verwende diesen (bereits berechnet)
    # Ansonsten hole Backlog aus statischen Logs (Fallback)
    if backlog_by_product is None:
        backlog_by_product = {}
        for product in MasterData.BOM.keys():
            backlog_by_product[product] = _get_backlog_from_previous_workday(
                production_logs, product, day, planning_year, workday_calc
            )
    
    # Schritt 2: Produktionsbedarf = Nachfrage + Backlog
    production_demand_by_product = {}
    for product in MasterData.BOM.keys():
        demand = product_demands_new.get(product, 0)
        backlog = backlog_by_product.get(product, 0.0)
        production_demand_by_product[product] = demand + backlog
    
    # Schritt 3: Anteilige Produktion berechnen
    total_production_demand = sum(production_demand_by_product.values())
    proportional_production_by_product = {}
    products_list = list(MasterData.BOM.keys())
    
    for product in products_list:
        demand = production_demand_by_product.get(product, 0.0)
        if total_production_demand > 0:
            # ABRUNDEN(Produktionsbedarf * Kapazität / Gesamtbedarf; 0)
            proportional = math.floor(demand * daily_capacity / total_production_demand)
        else:
            proportional = 0
        proportional_production_by_product[product] = proportional
    
    # Schritt 4: Rang berechnen (EXAKT wie in production_planner.py)
    rank_support_by_product = {}
    for idx, product in enumerate(products_list):
        row_number = idx + 1
        proportional = proportional_production_by_product.get(product, 0)
        # Rang_Unterstützung = Anteilige_Produktion + Zeile/1000000
        rank_support = (row_number / 1000000.0) + proportional
        rank_support_by_product[product] = rank_support
    
    # Sortiere Produkte nach Rang (Höchster Support-Wert zuerst = Rang 1)
    sorted_products = sorted(products_list, key=lambda p: rank_support_by_product[p], reverse=True)
    rank_by_product = {}
    for i, p in enumerate(sorted_products):
        rank_by_product[p] = i + 1
    
    # Schritt 5: "zu produzierende Mengen" berechnen (mit Material-Reduktion)
    scheduled_production_by_product = {}
    total_scheduled_so_far = 0.0
    
    # WICHTIG: Material wird dynamisch reduziert (wie in statischer Logik)
    stock_by_saddle_type = saddle_available_new.copy()
    
    for product in sorted_products:
        demand = production_demand_by_product.get(product, 0.0)
        proportional = proportional_production_by_product.get(product, 0)
        rank = rank_by_product.get(product, 999)
        
        if demand <= 0:
            scheduled_production_by_product[product] = 0.0
            continue
        
        # Minimale Produktion (Material-Limit)
        required_saddle_type = MasterData.BOM[product]['saddle']
        saddle_available = stock_by_saddle_type.get(required_saddle_type, 0.0)
        minimal = max(0.0, saddle_available)
        
        # Rang-basierte Berechnung (EXAKT wie in production_planner.py)
        if rank <= 4:
            # Rang 1-4: MIN(Bedarf, Anteilige, Minimale)
            scheduled_qty = min(demand, proportional, minimal)
        else:
            # Rang 5-8: MIN(Bedarf, Anteilige, Minimale) + Rest-Verteilung
            base_qty = min(demand, proportional, minimal)
            
            remaining_capacity = daily_capacity - total_scheduled_so_far
            remaining_demand = max(0.0, demand - base_qty)  # Stelle sicher, dass es nicht negativ ist
            
            if total_scheduled_so_far < daily_capacity and remaining_capacity > 0:
                rest_production = min(remaining_capacity, minimal, remaining_demand)
                scheduled_qty = base_qty + rest_production
            else:
                scheduled_qty = base_qty
        
        # KRITISCH: Stelle sicher, dass scheduled_qty nicht größer ist als demand
        # Dies verhindert, dass mehr produziert wird als der Produktionsbedarf erlaubt
        scheduled_qty = min(max(0.0, scheduled_qty), demand)
        scheduled_production_by_product[product] = scheduled_qty
        total_scheduled_so_far += scheduled_qty
        
        # KRITISCH: Reduziere Material SOFORT (dynamisch)
        if scheduled_qty > 0:
            stock_by_saddle_type[required_saddle_type] = max(0.0, stock_by_saddle_type[required_saddle_type] - scheduled_qty)
    
    # Sicherheitsprüfung 1: Stelle sicher, dass die Summe nicht die Kapazität überschreitet
    total_scheduled = sum(scheduled_production_by_product.values())
    if total_scheduled > daily_capacity:
        # Proportionale Reduktion, falls die Summe die Kapazität überschreitet
        scale_factor = daily_capacity / total_scheduled if total_scheduled > 0 else 0
        # WICHTIG: Bei Reduktion muss auch Material zurückgegeben werden
        for product in sorted_products:
            old_qty = scheduled_production_by_product.get(product, 0.0)
            new_qty = old_qty * scale_factor
            reduction = old_qty - new_qty
            scheduled_production_by_product[product] = new_qty
            
            # Gebe reduziertes Material zurück
            if reduction > 0:
                required_saddle_type = MasterData.BOM[product]['saddle']
                stock_by_saddle_type[required_saddle_type] = stock_by_saddle_type.get(required_saddle_type, 0.0) + reduction
    
    # Sicherheitsprüfung 2: Stelle sicher, dass die Summe nicht den Produktionsbedarf überschreitet
    total_production_demand = sum(production_demand_by_product.values())
    total_scheduled = sum(scheduled_production_by_product.values())
    if total_scheduled > total_production_demand:
        # Proportionale Reduktion auf Produktionsbedarf
        scale_factor = total_production_demand / total_scheduled if total_scheduled > 0 else 0
        # WICHTIG: Bei Reduktion muss auch Material zurückgegeben werden
        for product in sorted_products:
            old_qty = scheduled_production_by_product.get(product, 0.0)
            new_qty = old_qty * scale_factor
            reduction = old_qty - new_qty
            scheduled_production_by_product[product] = new_qty
            
            # Gebe reduziertes Material zurück
            if reduction > 0:
                required_saddle_type = MasterData.BOM[product]['saddle']
                stock_by_saddle_type[required_saddle_type] = stock_by_saddle_type.get(required_saddle_type, 0.0) + reduction
    
    # Schritt 6: Finale Prüfung - Stelle sicher, dass jedes Produkt nicht mehr produziert als sein Produktionsbedarf
    # Diese Prüfung ist kritisch, um sicherzustellen, dass niemals mehr produziert wird als geplant (wenn Backlog = 0)
    # WICHTIG: Wenn die Produktion reduziert wird, muss auch Material zurückgegeben werden
    for product in products_list:
        demand = production_demand_by_product.get(product, 0.0)
        scheduled_qty = scheduled_production_by_product.get(product, 0.0)
        
        # KRITISCH: Stelle sicher, dass scheduled_qty nicht größer ist als demand
        # Dies verhindert, dass mehr produziert wird als der Produktionsbedarf erlaubt
        if scheduled_qty > demand:
            old_qty = scheduled_production_by_product[product]
            scheduled_production_by_product[product] = demand
            reduction = old_qty - demand
            
            # Gebe reduziertes Material zurück
            if reduction > 0:
                required_saddle_type = MasterData.BOM[product]['saddle']
                stock_by_saddle_type[required_saddle_type] = stock_by_saddle_type.get(required_saddle_type, 0.0) + reduction
    
    # Schritt 7: "Tatsächliche PM" = "zu produzierende Mengen"
    result = {}
    for product in products_list:
        scheduled_qty = scheduled_production_by_product.get(product, 0.0)
        result[product] = int(scheduled_qty)
    
    return result


def _get_inbound_arrivals_by_day_and_saddle(simulator, planning_year: int) -> Dict[int, Dict[str, float]]:
    """
    Erstellt eine Map: Tag-Index -> {Sattel: Menge}, die an diesem Tag ankommt.
    Nutzt die Inbound-Tabelle für präzise Aufteilung pro Sattel-Typ.
    
    Args:
        simulator: Simulator-Instanz
        planning_year: Planungsjahr
    
    Returns:
        Dict[day_index] -> Dict[saddle_name] -> quantity
    """
    inbound_map = {}
    
    manager = simulator.china_transport_manager
    if not manager:
        return inbound_map
    
    # Hole Sattel-Shares für Verteilung (Fallback)
    saddle_shares = MasterData.calculate_saddle_shares()
    
    # Hole Inbound-DF (enthält bereits Verspätungen, Ladungsverluste etc.)
    inbound_df = manager.get_inbound_log_dataframe(saddle_shares)
    
    if inbound_df.empty:
        return inbound_map
    
    start_date_sim = date(planning_year, 1, 1)
    
    # Iteriere über alle Zeilen der Inbound-Tabelle
    for _, row in inbound_df.iterrows():
        # Hole Ankunftsdatum (Tatsächliche Ankunft LKW 🇩🇪)
        avail_str = row.get('Tatsächliche Ankunft LKW 🇩🇪', '')
        if not avail_str or (isinstance(avail_str, str) and avail_str.strip() == ''):
            continue
        
        try:
            avail_date = datetime.strptime(avail_str, MasterData.DATE_FORMAT).date()
            day_idx = (avail_date - start_date_sim).days
            
            # Nur Tage im Planungsjahr berücksichtigen
            if day_idx < 0 or day_idx >= 365:
                continue
            
            if day_idx not in inbound_map:
                inbound_map[day_idx] = {s: 0.0 for s in saddle_shares.keys()}
            
            # Hole Mengen pro Sattel-Typ aus den Spalten
            for saddle_name in saddle_shares.keys():
                if saddle_name in row:
                    qty_val = row[saddle_name]
                    try:
                        if isinstance(qty_val, str):
                            qty_val = qty_val.strip()
                            if qty_val == '' or qty_val == '-':
                                continue
                        qty = float(qty_val) if qty_val else 0.0
                        if qty > 0:
                            inbound_map[day_idx][saddle_name] += qty
                    except (ValueError, TypeError):
                        continue
        except (ValueError, TypeError):
            continue
    
    return inbound_map


def calculate_production_logs():
    """
    Berechnet production_logs_cache mit Running Inventory-Ansatz.
    
    NEUE LOGIK (Running Inventory):
    - Chronologische Schleife über alle 365 Tage
    - Running Stock pro Sattel-Typ wird Tag für Tag aktualisiert
    - Inbound wird hinzugefügt, Produktion wird abgezogen
    - Keine komplexen Deltas oder Synchronisationen mehr
    """
    if 'simulator' not in st.session_state or st.session_state.simulator is None:
        return {}
    
    simulator = st.session_state.simulator
    planner = simulator.production_planner
    
    if not hasattr(planner, 'production_logs') or not planner.production_logs:
        return {}
    
    # Cache-Key für Invalidierung
    volume_planning_cache_key = st.session_state.get('volume_planning_cache_key', None)
    cache_key = f"production_logs_running_v4_{volume_planning_cache_key}"  # v4: Fix für Double-Counting Bug
    
    # Prüfe Cache
    if cache_key in st.session_state and 'production_logs_cache' in st.session_state:
        if st.session_state.get('production_logs_cache_key') == cache_key:
            return st.session_state.production_logs_cache
    
    planning_year = st.session_state.get('planning_year', 2027)
    workday_calc = WorkdayCalculator(year=planning_year)
    scenario_manager = getattr(simulator, 'scenario_manager', None)
    
    # Setup: Sattel-Typen und Shares
    saddle_shares = MasterData.calculate_saddle_shares()
    saddles = list(saddle_shares.keys())
    
    # Init Running Stock (Laufender Bestand)
    running_stock = {s: 0.0 for s in saddles}
    
    # Berechne Initialbestand aus Inbound-Tabelle (Daten vor Planungsjahr)
    manager = simulator.china_transport_manager
    if manager:
        cutoff_date = date(planning_year, 1, 1)
        inbound_df = manager.get_inbound_log_dataframe(saddle_shares)
        
        if not inbound_df.empty:
            for _, row in inbound_df.iterrows():
                avail_str = row.get('Tatsächliche Ankunft LKW 🇩🇪', '')
                if not avail_str or (isinstance(avail_str, str) and avail_str.strip() == ''):
                    continue
                
                try:
                    avail_date = datetime.strptime(avail_str, MasterData.DATE_FORMAT).date()
                    if avail_date < cutoff_date:
                        # Diese Ware kam vor dem Planungsjahr an -> Initialbestand
                        for saddle_name in saddles:
                            if saddle_name in row:
                                qty_val = row[saddle_name]
                                try:
                                    if isinstance(qty_val, str):
                                        qty_val = qty_val.strip()
                                        if qty_val == '' or qty_val == '-':
                                            continue
                                    qty = float(qty_val) if qty_val else 0.0
                                    if qty > 0:
                                        running_stock[saddle_name] += qty
                                except (ValueError, TypeError):
                                    continue
                except (ValueError, TypeError):
                    continue
    
    # Konvertiere Logs zu DataFrames
    production_logs = {}
    for product, logs in planner.production_logs.items():
        if logs:
            production_logs[product] = pd.DataFrame(logs)
        else:
            production_logs[product] = pd.DataFrame()
    
    # Mapping für schnellen Zugriff: Tag -> {Produkt: ZeilenIndex}
    day_row_map = {}
    for p, df in production_logs.items():
        if df.empty:
            continue
        for idx, row in df.iterrows():
            d_str = row.get('Datum', '')
            if d_str:
                try:
                    d = datetime.strptime(d_str, MasterData.DATE_FORMAT).date()
                    day_idx = (d - date(planning_year, 1, 1)).days
                    if 0 <= day_idx < 365:
                        if day_idx not in day_row_map:
                            day_row_map[day_idx] = {}
                        day_row_map[day_idx][p] = idx
                except (ValueError, TypeError):
                    pass
    
    # Hole Inbound-Daten einmalig (Tag -> {Sattel: Menge})
    inbound_arrivals = _get_inbound_arrivals_by_day_and_saddle(simulator, planning_year)
    
    # Backlog Tracker (chronologisch)
    current_backlog = {p: 0.0 for p in MasterData.BOM.keys()}
    
    # Tägliche Nachfrage (inkl. Marketing-Szenarien)
    daily_demands_actual = st.session_state.get('daily_demands_actual', {})
    
    # ------------------------------------------------------------
    # CHRONOLOGISCHE SCHLEIFE (Tag 0-365)
    # ------------------------------------------------------------
    for day in range(365):
        current_date = workday_calc.get_date_from_day(day)
        
        # A. INBOUND: Was kommt heute an?
        if day in inbound_arrivals:
            for saddle_name, qty in inbound_arrivals[day].items():
                if qty > 0:
                    running_stock[saddle_name] += qty
        
        # B. WASSERSCHADEN: Prüfe Szenarien
        if scenario_manager:
            water_damage_scenarios = scenario_manager.get_water_damage_scenarios(day)
            for scenario in water_damage_scenarios:
                if scenario.affected_component == "saddles" and scenario.start_day == scenario.end_day:
                    if day == scenario.start_day:
                        # Setze Bestand aller Sättel auf 0
                        for s in saddles:
                            running_stock[s] = 0.0
                        break
        
        # --- WICHTIG: BESTAND MORGENS SICHERN (für die Anzeige) ---
        # Dieser Wert entspricht exakt dem "Bestand morgens" im Materiallager
        # Er wird statisch in alle Zeilen des Tages geschrieben
        daily_start_stock = running_stock.copy()
        
        # C. HEUTE KEIN ARBEITSTAG?
        is_workday = workday_calc.is_workday(day)
        
        # Bestand für UI schreiben (auch an Wochenenden)
        # ANZEIGE: Bestand Morgens (der sich am WE nicht ändert)
        if day in day_row_map:
            for p, idx in day_row_map[day].items():
                saddle = MasterData.BOM[p]['saddle']
                df = production_logs[p]
                df.at[idx, saddle] = int(round(daily_start_stock[saddle])) if daily_start_stock[saddle] > 0 else 0
                df.at[idx, 'Backlog'] = int(round(current_backlog[p]))
        
        if not is_workday:
            continue
        
        # D. PRODUKTION PLANEN
        todays_demand_map = daily_demands_actual.get(day, {})
        
        # Kapazität holen (aus Logs)
        daily_capacity = 0.0
        if day in day_row_map and day_row_map[day]:
            first_prod = next(iter(day_row_map[day]))
            first_idx = day_row_map[day][first_prod]
            df = production_logs[first_prod]
            shifts = df.at[first_idx, 'Schichtanzahl']
            working_hours = MasterData.GLOBAL_CONFIG.get('working_hours_per_shift', 8)
            capacity_per_hour = MasterData.GLOBAL_CONFIG.get('capacity_per_hour', 130)
            daily_capacity = shifts * working_hours * capacity_per_hour
        
        # FIX: WIR ADDIEREN HIER NICHT MEHR ZUM BACKLOG!
        # current_backlog enthält hier NUR den Rückstand von gestern.
        # Die Planungsfunktion addiert intern: Tagesbedarf + Backlog
        
        # E. RANKING & VERTEILUNG
        if daily_capacity > 0:
            scheduled_production = _recalculate_all_products_with_rank_logic(
                day,
                todays_demand_map,  # Übergibt den Tagesbedarf separat
                running_stock.copy(),
                daily_capacity,
                production_logs,
                planning_year,
                workday_calc,
                current_backlog.copy()  # Übergibt NUR den alten Backlog (vom Vortag)
            )
        else:
            scheduled_production = {p: 0 for p in MasterData.BOM.keys()}
        
        # F. BESTAND ABBUCHEN & LOGS UPDATEN
        for p, qty in scheduled_production.items():
            saddle = MasterData.BOM[p]['saddle']
            
            # 1. Physischer Abgang vom Gesamtbestand (intern, für Berechnung)
            qty_to_book = min(qty, running_stock[saddle])
            running_stock[saddle] -= qty_to_book
            
            # 2. Backlog Update (Hier passiert die korrekte Rechnung)
            # Neuer Backlog = (Alter Backlog + Tagesbedarf) - Produktion
            total_requirement = current_backlog[p] + todays_demand_map.get(p, 0)
            current_backlog[p] = max(0.0, total_requirement - qty_to_book)
            
            # 3. Schreiben in DataFrame
            if day in day_row_map and p in day_row_map[day]:
                idx = day_row_map[day][p]
                df = production_logs[p]
                
                df.at[idx, 'tatsächliche PM'] = qty_to_book
                if 'material_verbrauch' not in df.columns:
                    df['material_verbrauch'] = 0
                df.at[idx, 'material_verbrauch'] = qty_to_book
                df.at[idx, 'Backlog'] = int(round(current_backlog[p]))
                
                # ANZEIGE: Bestand Morgens (statisch für den ganzen Tag)
                # Hier nutzen wir daily_start_stock statt running_stock!
                df.at[idx, saddle] = int(round(daily_start_stock[saddle])) if daily_start_stock[saddle] > 0 else 0
                
                planned_pm = todays_demand_map.get(p, 0)
                df.at[idx, 'geplante PM'] = int(planned_pm)
    
    # Aktualisiere "fertiggestellte PM" (Produktion vom Vortag)
    for product, df in production_logs.items():
        if df.empty or 'Datum' not in df.columns or 'tatsächliche PM' not in df.columns or 'fertiggestellte PM' not in df.columns:
            continue
        
        df_sorted = df.copy()
        df_sorted['_date_parsed'] = pd.to_datetime(df_sorted['Datum'], format=MasterData.DATE_FORMAT)
        df_sorted = df_sorted.sort_values('_date_parsed').reset_index(drop=True)
        
        date_to_idx = {}
        for idx, row in df_sorted.iterrows():
            date_str = row.get('Datum', '')
            if date_str:
                try:
                    row_date = datetime.strptime(date_str, MasterData.DATE_FORMAT).date()
                    date_to_idx[row_date] = idx
                except (ValueError, TypeError):
                    pass
        
        for idx, row in df_sorted.iterrows():
            date_str = row.get('Datum', '')
            if date_str:
                try:
                    row_date = datetime.strptime(date_str, MasterData.DATE_FORMAT).date()
                    day = (row_date - date(planning_year, 1, 1)).days
                    
                    if not workday_calc.is_workday(day):
                        df_sorted.at[idx, 'fertiggestellte PM'] = 0
                        continue
                    
                    # Finde vorherigen Arbeitstag
                    prev_workday_found = False
                    prev_day = day - 1
                    while prev_day >= 0:
                        if workday_calc.is_workday(prev_day):
                            prev_workday_date = workday_calc.get_date_from_day(prev_day)
                            
                            if prev_workday_date in date_to_idx:
                                prev_idx = date_to_idx[prev_workday_date]
                                prev_row = df_sorted.iloc[prev_idx]
                                
                                prev_actual_pm = prev_row.get('tatsächliche PM', 0)
                                df_sorted.at[idx, 'fertiggestellte PM'] = int(round(prev_actual_pm)) if prev_actual_pm > 0 else 0
                                prev_workday_found = True
                                break
                        
                        prev_day -= 1
                    
                    if not prev_workday_found:
                        df_sorted.at[idx, 'fertiggestellte PM'] = 0
                except (ValueError, TypeError):
                    pass
        
        if '_date_parsed' in df_sorted.columns:
            df_sorted = df_sorted.drop(columns=['_date_parsed'])
        production_logs[product] = df_sorted
    
    # Cache Ergebnis
    st.session_state.production_logs_cache = production_logs
    st.session_state.production_logs_cache_key = cache_key
    
    # Schreibe zurück in Simulator
    if planner:
        for product, df in production_logs.items():
            if not df.empty:
                updated_logs = df.to_dict('records')
                planner.production_logs[product] = updated_logs
    
    # Lösche Materiallager-Cache (wird neu berechnet)
    keys_to_clear = [
        'saddle_logs_cache',
        'material_logs_cache',
        'inventory_chart_cache',
        'material_inventory_data'
    ]
    
    for k in list(st.session_state.keys()):
        if k in keys_to_clear or (k.startswith('material_inventory_') and k != 'material_inventory_last_cache_key'):
            del st.session_state[k]
    
    return production_logs
