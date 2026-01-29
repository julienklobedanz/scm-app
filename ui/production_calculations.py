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
        for product in sorted(MasterData.BOM.keys()):
            backlog_by_product[product] = _get_backlog_from_previous_workday(
                production_logs, product, day, planning_year, workday_calc
            )
    
    # Schritt 2: Produktionsbedarf = Nachfrage + Backlog
    production_demand_by_product = {}
    for product in sorted(MasterData.BOM.keys()):
        demand = product_demands_new.get(product, 0)
        backlog = backlog_by_product.get(product, 0.0)
        production_demand_by_product[product] = demand + backlog
    
    # Schritt 3: Anteilige Produktion berechnen
    total_production_demand = sum(production_demand_by_product.values())
    proportional_production_by_product = {}
    # FIX: Garantiere deterministische Reihenfolge durch sorted()
    products_list = sorted(MasterData.BOM.keys())
    
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
    
    # PERFORMANCE: Vektorisierte Verarbeitung statt iterrows()
    avail_col = 'Tatsächliche Ankunft LKW 🇩🇪'
    if avail_col not in inbound_df.columns:
        return inbound_map
    
    # Filtere leere Ankunftsdaten
    valid_rows = inbound_df[inbound_df[avail_col].notna() & (inbound_df[avail_col].astype(str).str.strip() != '')]
    
    if valid_rows.empty:
        return inbound_map
    
    # Konvertiere Datumsspalte zu Datum-Objekten (vektorisiert)
    try:
        valid_rows = valid_rows.copy()
        valid_rows['_parsed_date'] = pd.to_datetime(valid_rows[avail_col], format=MasterData.DATE_FORMAT, errors='coerce').dt.date
        valid_rows = valid_rows[valid_rows['_parsed_date'].notna()]
        
        if valid_rows.empty:
            return inbound_map
        
        # Berechne day_idx für alle Zeilen auf einmal
        valid_rows['_day_idx'] = (pd.to_datetime(valid_rows['_parsed_date']) - pd.Timestamp(start_date_sim)).dt.days
        
        # Filtere nur Tage im Planungsjahr
        valid_rows = valid_rows[(valid_rows['_day_idx'] >= 0) & (valid_rows['_day_idx'] < 365)]
        
        if valid_rows.empty:
            return inbound_map
        
        # Gruppiere nach day_idx und summiere Mengen pro Sattel-Typ (vektorisiert)
        # KRITISCH: Verwende die ursprünglichen valid_rows, nicht gefilterte qty_series
        # um sicherzustellen, dass alle Zeilen mit _day_idx berücksichtigt werden
        for saddle_name in saddle_shares.keys():
            if saddle_name in valid_rows.columns:
                # Konvertiere zu numerisch (vektorisiert) - BEHALTE ALLE Zeilen
                qty_series = pd.to_numeric(valid_rows[saddle_name], errors='coerce').fillna(0.0)
                
                # KRITISCH: Verwende valid_rows direkt für groupby, nicht gefilterte qty_series
                # Dies stellt sicher, dass alle Zeilen mit _day_idx berücksichtigt werden
                # auch wenn qty = 0 ist (könnte wichtig sein für Konsistenz)
                grouped = valid_rows.groupby('_day_idx')[saddle_name].sum()
                for day_idx, total_qty in grouped.items():
                    # Nur hinzufügen wenn Menge > 0
                    if float(total_qty) > 0:
                        day_idx_int = int(day_idx)
                        if day_idx_int not in inbound_map:
                            inbound_map[day_idx_int] = {s: 0.0 for s in saddle_shares.keys()}
                        inbound_map[day_idx_int][saddle_name] += float(total_qty)
    except Exception:
        # Fallback auf alte Methode bei Fehler
        for _, row in inbound_df.iterrows():
            avail_str = row.get(avail_col, '')
            if not avail_str or (isinstance(avail_str, str) and avail_str.strip() == ''):
                continue
            
            try:
                avail_date = datetime.strptime(avail_str, MasterData.DATE_FORMAT).date()
                day_idx = (avail_date - start_date_sim).days
                
                if day_idx < 0 or day_idx >= 365:
                    continue
                
                if day_idx not in inbound_map:
                    inbound_map[day_idx] = {s: 0.0 for s in saddle_shares.keys()}
                
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
    # Sicherstellen, dass st verfügbar ist
    import streamlit as st_module
    if 'simulator' not in st_module.session_state or st_module.session_state.simulator is None:
        return {}
    
    simulator = st_module.session_state.simulator
    planner = simulator.production_planner
    
    if not hasattr(planner, 'production_logs') or not planner.production_logs:
        return {}
    
    # Cache-Key für Invalidierung
    volume_planning_cache_key = st_module.session_state.get('volume_planning_cache_key', None)
    cache_key = f"production_logs_running_v6_{volume_planning_cache_key}"  # v6: Fix für material_verbrauch - alle Tage + fertiggestellte PM Summe
    
    # PERFORMANCE: Prüfe Cache zuerst (schnellerer Check)
    if ('production_logs_cache' in st_module.session_state and 
        st_module.session_state.get('production_logs_cache_key') == cache_key):
        return st_module.session_state.production_logs_cache
    
    planning_year = st_module.session_state.get('planning_year', 2027)
    workday_calc = WorkdayCalculator(year=planning_year)
    scenario_manager = getattr(simulator, 'scenario_manager', None)
    
    # Setup: Sattel-Typen und Shares
    saddle_shares = MasterData.calculate_saddle_shares()
    saddles = list(saddle_shares.keys())
    
    # Init Running Stock (Laufender Bestand)
    running_stock = {s: 0.0 for s in saddles}
    
    # PERFORMANCE: Berechne Initialbestand direkt aus transport_status statt get_inbound_log_dataframe()
    # Dies vermeidet die teure Berechnung von get_inbound_log_dataframe() beim ersten Aufruf
    manager = simulator.china_transport_manager
    if manager:
        cutoff_date = date(planning_year, 1, 1)
        
        # PERFORMANCE: Verwende get_daily_arrival_qty() statt get_inbound_log_dataframe()
        # Dies ist viel schneller, da es direkt aus transport_status liest
        # Nur wenn wirklich die vollständige Tabelle benötigt wird, verwende get_inbound_log_dataframe()
        initial_stock = {s: 0.0 for s in saddles}
        
        # Berechne Initialbestand aus transport_status (Daten vor Planungsjahr)
        if hasattr(manager, 'transport_status') and manager.transport_status:
            for (order_day, order_id), status in manager.transport_status.items():
                available_day = status.get('available_day')
                if available_day is None:
                    continue
                
                try:
                    avail_date = workday_calc.get_date_from_day(available_day)
                    if avail_date < cutoff_date:
                        # Summiere die tatsächliche Menge (nach Verlusten)
                        qty = status.get('actual_quantity', status.get('quantity', 0.0))
                        if qty > 0:
                            # Verteile auf Sattel-Typen basierend auf saddle_shares
                            for saddle_name in saddles:
                                share = saddle_shares.get(saddle_name, 0.0)
                                initial_stock[saddle_name] += qty * share
                except Exception:
                    continue
        
        # Setze Running Stock auf Initialbestand
        running_stock = initial_stock.copy()
        
    # KRITISCH: Berechne inbound_arrivals IMMER für korrekte Verteilung basierend auf Produktion
    # Die Verteilung kommt aus get_inbound_log_dataframe(), die bereits die korrekte Verteilung hat
    inbound_arrivals = {}
    if manager:
        inbound_arrivals = _get_inbound_arrivals_by_day_and_saddle(simulator, planning_year)
    
    # PERFORMANCE: Hole Inbound-DF nur wenn wirklich benötigt (für Initialbestand)
    # Verwende inbound_arrivals für tägliche Zugänge (korrekte Verteilung)
    use_inbound_df = False  # Standard: Verwende inbound_arrivals
    
    if use_inbound_df:
            # Fallback: Nur wenn get_daily_arrival_qty() nicht verfügbar ist
            inbound_df = manager.get_inbound_log_dataframe(saddle_shares)
            
            if not inbound_df.empty:
                # PERFORMANCE: Vektorisierte Verarbeitung statt iterrows()
                avail_col = 'Tatsächliche Ankunft LKW 🇩🇪'
                if avail_col in inbound_df.columns:
                    valid_rows = inbound_df[avail_col].notna() & (inbound_df[avail_col].astype(str).str.strip() != '')
                    valid_rows = inbound_df[valid_rows]
                    if not valid_rows.empty:
                        try:
                            valid_rows = valid_rows.copy()
                            valid_rows['_parsed_date'] = pd.to_datetime(valid_rows[avail_col], format=MasterData.DATE_FORMAT, errors='coerce').dt.date
                            valid_rows = valid_rows[valid_rows['_parsed_date'].notna()]
                            valid_rows = valid_rows[valid_rows['_parsed_date'] < cutoff_date]
                            
                            # Summiere Mengen pro Sattel-Typ für alle Zeilen vor cutoff_date
                            for saddle_name in saddles:
                                if saddle_name in valid_rows.columns:
                                    qty_series = pd.to_numeric(valid_rows[saddle_name], errors='coerce').fillna(0.0)
                                    total_qty = qty_series.sum()
                                    if total_qty > 0:
                                        running_stock[saddle_name] += float(total_qty)
                        except Exception:
                            # Fallback auf alte Methode
                            for _, row in inbound_df.iterrows():
                                avail_str = row.get(avail_col, '')
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
    
    # KRITISCH: Initialisiere Sattel-Spalten und material_verbrauch für alle Produkte
    # Dies stellt sicher, dass die Spalten immer existieren, auch wenn der Bestand immer 0 war
    for product, df in production_logs.items():
        if not df.empty:
            saddle_name = MasterData.BOM.get(product, {}).get('saddle')
            if saddle_name and saddle_name not in df.columns:
                df[saddle_name] = 0  # Initialisiere Spalte mit 0 für alle Zeilen
            # KRITISCH: Initialisiere material_verbrauch für alle Zeilen mit 0
            # Dies stellt sicher, dass der Verbrauch für alle Tage erfasst wird
            if 'material_verbrauch' not in df.columns:
                df['material_verbrauch'] = 0
    
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
    
    # KRITISCH: Berechne inbound_arrivals IMMER für korrekte Verteilung basierend auf Produktion
    # Die Verteilung kommt aus get_inbound_log_dataframe(), die bereits die korrekte Verteilung hat
    inbound_arrivals = {}
    if manager:
        inbound_arrivals = _get_inbound_arrivals_by_day_and_saddle(simulator, planning_year)
    
    # Backlog Tracker (chronologisch)
    # FIX: Garantiere deterministische Reihenfolge durch sorted()
    current_backlog = {p: 0.0 for p in sorted(MasterData.BOM.keys())}
    
    # Tägliche Nachfrage (inkl. Marketing-Szenarien)
    daily_demands_actual = st_module.session_state.get('daily_demands_actual', {})
    
    # ------------------------------------------------------------
    # CHRONOLOGISCHE SCHLEIFE (Tag 0-365)
    # ------------------------------------------------------------
    for day in range(365):
        current_date = workday_calc.get_date_from_day(day)
        
        # A. INBOUND: Was kommt heute an?
        # KRITISCH: Verwende inbound_arrivals für korrekte Verteilung basierend auf Produktion
        # Die Verteilung kommt aus get_inbound_log_dataframe(), die bereits die korrekte Verteilung hat
        if day in inbound_arrivals:
            # Verwende inbound_arrivals für korrekte Verteilung pro Sattel-Typ
            for saddle_name, qty in inbound_arrivals[day].items():
                if qty > 0:
                    running_stock[saddle_name] += qty
        elif manager and hasattr(manager, 'get_daily_arrival_qty'):
            # Fallback: Verwende get_daily_arrival_qty() nur wenn inbound_arrivals nicht verfügbar
            # HINWEIS: Dies ist eine Näherung - die tatsächliche Verteilung hängt von der Produktion ab
            total_arrival_qty = manager.get_daily_arrival_qty(day)
            if total_arrival_qty > 0:
                # Verteile auf Sattel-Typen basierend auf saddle_shares (Näherung)
                for saddle_name in saddles:
                    share = saddle_shares.get(saddle_name, 0.0)
                    running_stock[saddle_name] += total_arrival_qty * share
        
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
        # KRITISCH: Stelle sicher, dass material_verbrauch für ALLE Tage gesetzt wird, auch für Wochenenden/Feiertage
        # Auch wenn kein Arbeitstag ist, muss material_verbrauch = 0 gesetzt werden
        current_date_str = current_date.strftime(MasterData.DATE_FORMAT)
        for p in sorted(MasterData.BOM.keys()):
            df = production_logs[p]
            if not df.empty and 'Datum' in df.columns:
                matching_rows = df[df['Datum'] == current_date_str]
                if not matching_rows.empty:
                    idx = matching_rows.index[0]
                    # KRITISCH: Initialisiere material_verbrauch Spalte falls nicht vorhanden
                    if 'material_verbrauch' not in df.columns:
                        df['material_verbrauch'] = 0
                    # KRITISCH: Setze material_verbrauch für Wochenenden/Feiertage auf 0
                    # Dies stellt sicher, dass der Verbrauch für ALLE Tage erfasst wird
                    if not is_workday:
                        df.at[idx, 'material_verbrauch'] = 0
        
        if day in day_row_map:
            for p, idx in day_row_map[day].items():
                saddle = MasterData.BOM[p]['saddle']
                df = production_logs[p]
                # KRITISCH: Initialisiere Sattel-Spalte falls nicht vorhanden
                # Dies stellt sicher, dass die Spalte in der Tabelle angezeigt wird, auch wenn der Bestand = 0 ist
                if saddle not in df.columns:
                    df[saddle] = 0
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
            # FIX: Garantiere deterministische Reihenfolge durch sorted()
            scheduled_production = {p: 0 for p in sorted(MasterData.BOM.keys())}
        
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
            # KRITISCH: material_verbrauch MUSS IMMER gesetzt werden für ALLE Produkte an ALLEN Tagen
            # Material wird bereits abgebucht (Zeile 656), daher muss es auch im DataFrame gespeichert werden
            df = production_logs[p]
            if not df.empty and 'Datum' in df.columns:
                current_date_str = current_date.strftime(MasterData.DATE_FORMAT)
                matching_rows = df[df['Datum'] == current_date_str]
                if not matching_rows.empty:
                    idx = matching_rows.index[0]
                    # KRITISCH: Initialisiere material_verbrauch Spalte falls nicht vorhanden
                    if 'material_verbrauch' not in df.columns:
                        df['material_verbrauch'] = 0
                    # KRITISCH: Setze material_verbrauch IMMER (auch wenn qty_to_book = 0)
                    # Dies stellt sicher, dass der Verbrauch für ALLE Tage korrekt erfasst wird
                    df.at[idx, 'material_verbrauch'] = qty_to_book
                    
                    # Setze weitere Felder nur wenn Tag in day_row_map ist
                    if day in day_row_map and p in day_row_map[day]:
                        df.at[idx, 'tatsächliche PM'] = qty_to_book
                        df.at[idx, 'Backlog'] = int(round(current_backlog[p]))
                        
                        # ANZEIGE: Bestand Morgens (statisch für den ganzen Tag)
                        # Hier nutzen wir daily_start_stock statt running_stock!
                        # KRITISCH: Setze die Sattel-Spalte IMMER, auch wenn der Bestand = 0 ist
                        # Dies stellt sicher, dass die Spalte in der Tabelle angezeigt wird
                        if saddle not in df.columns:
                            df[saddle] = 0  # Initialisiere Spalte falls nicht vorhanden
                        df.at[idx, saddle] = int(round(daily_start_stock[saddle])) if daily_start_stock[saddle] > 0 else 0
                        
                        planned_pm = todays_demand_map.get(p, 0)
                        df.at[idx, 'geplante PM'] = int(planned_pm)
    
    # Aktualisiere "fertiggestellte PM" (Produktion vom Vortag)
    # OPTIMIERT: Vereinfachte Logik für bessere Performance
    try:
        for product, df in production_logs.items():
            if df.empty or 'Datum' not in df.columns or 'tatsächliche PM' not in df.columns or 'fertiggestellte PM' not in df.columns:
                continue
            
            df_sorted = df.copy()
            df_sorted['_date_parsed'] = pd.to_datetime(df_sorted['Datum'], format=MasterData.DATE_FORMAT)
            df_sorted = df_sorted.sort_values('_date_parsed').reset_index(drop=True)
            
            # Erstelle Mapping: Datum -> Index (einmalig für bessere Performance)
            date_to_idx = {}
            for idx, row in df_sorted.iterrows():
                date_str = row.get('Datum', '')
                if date_str:
                    try:
                        row_date = datetime.strptime(date_str, MasterData.DATE_FORMAT).date()
                        date_to_idx[row_date] = idx
                    except (ValueError, TypeError):
                        pass
            
            # OPTIMIERT: Iteriere nur über Arbeitstage (nicht alle Zeilen)
            for idx, row in df_sorted.iterrows():
                date_str = row.get('Datum', '')
                if not date_str:
                    continue
                
                try:
                    row_date = datetime.strptime(date_str, MasterData.DATE_FORMAT).date()
                    day = (row_date - date(planning_year, 1, 1)).days
                    
                    if not workday_calc.is_workday(day):
                        df_sorted.at[idx, 'fertiggestellte PM'] = 0
                        continue
                    
                    # KRITISCH: Am letzten Tag des Jahres (31.12.2027) setze fertiggestellte PM = tatsächliche PM
                    # Die tatsächliche PM vom letzten Tag wird nicht als fertiggestellte PM am nächsten Tag berücksichtigt
                    # weil es keinen nächsten Tag gibt. Daher müssen wir sie hier explizit setzen.
                    if day == 364:  # Letzter Tag des Jahres (31.12.2027)
                        current_actual_pm = row.get('tatsächliche PM', 0)
                        try:
                            current_actual_pm = float(current_actual_pm) if current_actual_pm > 0 else 0.0
                            # Am letzten Tag: fertiggestellte PM = tatsächliche PM (keine Verzögerung, da es der letzte Tag ist)
                            df_sorted.at[idx, 'fertiggestellte PM'] = int(round(current_actual_pm))
                            continue  # Überspringe normale Logik für letzten Tag
                        except (ValueError, TypeError):
                            pass  # Fallback auf normale Logik
                    
                    # FIX: Prüfe ob Wasserschaden am aktuellen Tag ODER am Vortag war
                    # Wenn am Vortag Wasserschaden war, wurde nichts produziert → fertiggestellte PM = 0
                    water_damage_today = False
                    water_damage_yesterday = False
                    
                    try:
                        if scenario_manager:
                            water_damage_today = len(scenario_manager.get_water_damage_scenarios(day)) > 0
                            
                            # Prüfe auch Vortag: Wenn am Vortag Wasserschaden war, wurde nichts produziert
                            # WICHTIG: Nur den unmittelbar vorherigen Arbeitstag prüfen (nicht mehrere Tage zurück)
                            prev_day_check = day - 1
                            max_lookback_check = 5  # Maximal 5 Tage zurück (für Wochenenden/Feiertage)
                            lookback_check_count = 0
                            
                            while prev_day_check >= 0 and lookback_check_count < max_lookback_check:
                                if workday_calc.is_workday(prev_day_check):
                                    water_damage_yesterday = len(scenario_manager.get_water_damage_scenarios(prev_day_check)) > 0
                                    break  # Nur den ersten vorherigen Arbeitstag prüfen
                                prev_day_check -= 1
                                lookback_check_count += 1
                    except Exception:
                        water_damage_today = False
                        water_damage_yesterday = False
                    
                    # Wenn Wasserschaden heute: fertiggestellte PM = 0
                    if water_damage_today:
                        df_sorted.at[idx, 'fertiggestellte PM'] = 0
                    else:
                        # Normale Logik: Finde vorherigen Arbeitstag (mit Limit für Performance)
                        prev_workday_found = False
                        prev_day = day - 1
                        # KRITISCH: Erhöhtes Limit, um sicherzustellen, dass der erste Tag des Jahres gefunden wird
                        # (z.B. wenn der erste Tag am 04.01 ist, müssen wir bis zum 01.01 zurückgehen können)
                        max_lookback = 15  # Maximal 15 Tage zurück suchen (Performance-Optimierung, aber ausreichend für Jahresanfang)
                        lookback_count = 0
                        
                        while prev_day >= 0 and lookback_count < max_lookback:
                            if workday_calc.is_workday(prev_day):
                                prev_workday_date = workday_calc.get_date_from_day(prev_day)
                                
                                if prev_workday_date in date_to_idx:
                                    prev_idx = date_to_idx[prev_workday_date]
                                    prev_row = df_sorted.iloc[prev_idx]
                                    
                                    # Prüfe ob am Vortag Wasserschaden war
                                    prev_water_damage = False
                                    try:
                                        if scenario_manager:
                                            prev_water_damage = len(scenario_manager.get_water_damage_scenarios(prev_day)) > 0
                                    except Exception:
                                        prev_water_damage = False
                                    
                                    prev_actual_pm = prev_row.get('tatsächliche PM', 0)
                                    
                                    # Wenn am Vortag Wasserschaden war UND nichts produziert wurde → fertiggestellte PM = 0
                                    # Wenn am Vortag produziert wurde (auch wenn vorher Wasserschaden war) → fertiggestellte PM = tatsächliche PM vom Vortag
                                    if prev_water_damage and prev_actual_pm == 0:
                                        df_sorted.at[idx, 'fertiggestellte PM'] = 0
                                    else:
                                        df_sorted.at[idx, 'fertiggestellte PM'] = int(round(prev_actual_pm)) if prev_actual_pm > 0 else 0
                                    
                                    prev_workday_found = True
                                    break
                                lookback_count += 1
                            
                            prev_day -= 1
                            lookback_count += 1  # FIX: Auch bei Nicht-Arbeitstagen zählen
                        
                        if not prev_workday_found:
                            # KRITISCH: Am ersten Arbeitstag des Jahres (kein vorheriger Arbeitstag gefunden)
                            # Wenn am aktuellen Tag produziert wurde, sollte diese Produktion als fertiggestellt gezählt werden
                            # Dies verhindert, dass produzierten Einheiten am ersten Tag "verloren gehen"
                            current_actual_pm = row.get('tatsächliche PM', 0)
                            try:
                                current_actual_pm = float(current_actual_pm) if current_actual_pm > 0 else 0.0
                            except (ValueError, TypeError):
                                current_actual_pm = 0.0
                            
                            # Am ersten Tag: fertiggestellte PM = tatsächliche PM (keine Verzögerung, da es der erste Tag ist)
                            # ABER: Nur wenn tatsächlich produziert wurde
                            if current_actual_pm > 0:
                                df_sorted.at[idx, 'fertiggestellte PM'] = int(round(current_actual_pm))
                            else:
                                df_sorted.at[idx, 'fertiggestellte PM'] = 0
                except (ValueError, TypeError):
                    df_sorted.at[idx, 'fertiggestellte PM'] = 0
            
            if '_date_parsed' in df_sorted.columns:
                df_sorted = df_sorted.drop(columns=['_date_parsed'])
            production_logs[product] = df_sorted
    except Exception as e:
        # Bei Fehler: Logge Fehler und verwende normale Logik ohne Wasserschaden-Check
        try:
            st_module.error(f"⚠️ Fehler bei Berechnung von fertiggestellte PM: {str(e)}")
        except:
            pass  # Falls st nicht verfügbar ist, ignoriere Fehler
        # Setze alle fertiggestellte PM auf 0 als Fallback
        for product, df in production_logs.items():
            if not df.empty and 'fertiggestellte PM' in df.columns:
                df['fertiggestellte PM'] = 0
    
    # Cache Ergebnis
    st_module.session_state.production_logs_cache = production_logs
    st_module.session_state.production_logs_cache_key = cache_key
    
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
    
    for k in list(st_module.session_state.keys()):
        if k in keys_to_clear or (k.startswith('material_inventory_') and k != 'material_inventory_last_cache_key'):
            del st_module.session_state[k]
    
    return production_logs
