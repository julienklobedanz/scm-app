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


def calculate_production_logs():
    """
    Berechnet production_logs_cache ohne UI-Rendering.
    Diese Funktion kann beim App-Start aufgerufen werden, ohne dass Streamlit-Widgets gerendert werden.
    """
    if 'simulator' not in st.session_state or st.session_state.simulator is None:
        return {}
    
    planner = st.session_state.simulator.production_planner
    
    if not hasattr(planner, 'production_logs') or not planner.production_logs:
        return {}
    
    # WICHTIG: Hole Cache-Key für Szenarien (für Cache-Invalidierung)
    volume_planning_cache_key = st.session_state.get('volume_planning_cache_key', None)
    
    # Erweitere Cache-Key um Szenarien
    cache_key = f"production_logs_{volume_planning_cache_key}"
    
    # Prüfe Cache
    if cache_key in st.session_state and 'production_logs_cache' in st.session_state:
        cached_key = st.session_state.get('production_logs_cache_key', None)
        if cached_key == cache_key:
            return st.session_state.production_logs_cache
    
    planning_year = st.session_state.get('planning_year', 2027)
    
    # Konvertiere Logs zu DataFrames
    production_logs = {}
    for product, logs in planner.production_logs.items():
        if logs:
            production_logs[product] = pd.DataFrame(logs)
        else:
            production_logs[product] = pd.DataFrame()
    
    # Dynamische Updates mit Rang-Logik (Option 3: Hybrid-Ansatz)
    daily_demands_actual = st.session_state.get('daily_demands_actual', {})
    material_inventory_data = st.session_state.get('material_inventory_data', {})
    workday_calc = WorkdayCalculator(year=planning_year)
    
    if daily_demands_actual:
        # OPTIMIERUNG: Gruppiere nach Tag, um für alle Produkte gleichzeitig zu berechnen
        # (wichtig für korrekte Material-Reduktion während Rang-Logik)
        days_to_update = {}
        
        for product, df in production_logs.items():
            if df.empty or 'Datum' not in df.columns or 'tatsächliche PM' not in df.columns:
                continue
            
            for idx, row in df.iterrows():
                date_str = row.get('Datum', '')
                if date_str:
                    try:
                        row_date = datetime.strptime(date_str, MasterData.DATE_FORMAT).date()
                        day = (row_date - date(planning_year, 1, 1)).days
                        
                        if day in daily_demands_actual:
                            if day not in days_to_update:
                                days_to_update[day] = {
                                    'date': row_date,
                                    'products': {}
                                }
                            
                            # Speichere statische Werte als Basis
                            base_tatsaechliche_pm = row.get('tatsächliche PM', 0)
                            base_geplante_pm = row.get('geplante PM', 0)
                            base_saddle_stock = row.get(MasterData.BOM[product]['saddle'], 0)
                            
                            days_to_update[day]['products'][product] = {
                                'df': df,
                                'idx': idx,
                                'base_tatsaechliche_pm': base_tatsaechliche_pm,
                                'base_geplante_pm': base_geplante_pm,
                                'base_saddle_stock': base_saddle_stock,
                                'shifts': row.get('Schichtanzahl', 0)
                            }
                    except (ValueError, TypeError):
                        pass
        
        # WICHTIG: Verarbeite Tage in chronologischer Reihenfolge, damit Backlog korrekt berechnet wird
        sorted_days = sorted(days_to_update.keys())
        
        # KRITISCH: Speichere berechnete Backlogs für jeden Tag (für korrekte Berechnung)
        calculated_backlogs = {}  # Dict[day] -> Dict[product] -> backlog
        
        # KRITISCH: Speichere kumulierten Mehrverbrauch pro Sattel (Delta)
        # Dies ist notwendig, damit der Mehrverbrauch von Tag X den Bestand an Tag X+1 reduziert
        cumulative_saddle_consumption_delta = {}  # Dict[saddle_name] -> float
        saddle_shares = MasterData.calculate_saddle_shares()
        for saddle in saddle_shares.keys():
            cumulative_saddle_consumption_delta[saddle] = 0.0
        
        # Berechne für jeden Tag mit Rang-Logik (für ALLE Produkte gleichzeitig)
        for day in sorted_days:
            day_data = days_to_update[day]
            row_date = day_data['date']
            products_info = day_data['products']
            
            # Hole aktualisierte Inputs
            product_demands_new = daily_demands_actual[day]
            
            # KRITISCH: Berechne Backlog für diesen Tag basierend auf bereits berechneten Werten
            backlog_by_product_calculated = {}
            for product in MasterData.BOM.keys():
                planned_pm = product_demands_new.get(product, 0)
                
                # Finde vorherigen Arbeitstag
                prev_day = day - 1
                while prev_day >= 0:
                    if workday_calc.is_workday(prev_day):
                        break
                    prev_day -= 1
                
                if prev_day >= 0:
                    # Hole bereits berechneten Backlog vom Vortag
                    if prev_day in calculated_backlogs:
                        prev_backlog = calculated_backlogs[prev_day].get(product, 0.0)
                    else:
                        # Fallback: Hole aus statischen Logs
                        prev_backlog = _get_backlog_from_previous_workday(
                            production_logs, product, day, planning_year, workday_calc
                        )
                    
                    # Hole bereits berechnete tatsächliche PM vom Vortag
                    prev_actual_pm = 0
                    prev_date = workday_calc.get_date_from_day(prev_day)
                    prev_date_str = prev_date.strftime(MasterData.DATE_FORMAT)
                    if product in production_logs:
                        df = production_logs[product]
                        if not df.empty and 'Datum' in df.columns and 'tatsächliche PM' in df.columns:
                            matching_rows = df[df['Datum'] == prev_date_str]
                            if not matching_rows.empty:
                                prev_actual_pm = matching_rows.iloc[0].get('tatsächliche PM', 0)
                                try:
                                    prev_actual_pm = int(prev_actual_pm) if prev_actual_pm > 0 else 0
                                except (ValueError, TypeError):
                                    prev_actual_pm = 0
                    
                    # Berechne Backlog für vorherigen Tag: (prev_planned_pm + prev_prev_backlog) - prev_actual_pm
                    # Für jetzt: Verwende bereits berechneten Backlog
                    backlog_by_product_calculated[product] = prev_backlog
                else:
                    # Kein vorheriger Arbeitstag: Backlog = 0
                    backlog_by_product_calculated[product] = 0.0
            
            # Berechne Materialverfügbarkeit für alle Sättel
            saddle_available_new = {}
            for saddle_name in saddle_shares.keys():
                # 1. Hole Basis-Bestand (aus Cache oder Fallback)
                base_stock = 0.0
                if row_date in material_inventory_data:
                    base_stock = material_inventory_data[row_date].get(saddle_name, 0.0)
                else:
                    # Fallback: Suche in products_info
                    for product in MasterData.BOM.keys():
                        if MasterData.BOM[product]['saddle'] == saddle_name:
                            if product in products_info:
                                val = products_info[product]['base_saddle_stock']
                                try:
                                    if isinstance(val, str) and val == '∞':
                                        base_stock = float('inf')
                                    else:
                                        base_stock = float(val)
                                except (ValueError, TypeError):
                                    base_stock = 0.0
                            break
                    if base_stock == 0.0:
                        base_stock = 0.0
                
                # 2. KRITISCH: Korrigiere Bestand um den kumulierten Mehrverbrauch der Vortage
                delta = cumulative_saddle_consumption_delta.get(saddle_name, 0.0)
                corrected_stock = max(0.0, base_stock - delta)
                saddle_available_new[saddle_name] = corrected_stock
            
            # Hole Tageskapazität (aus einem beliebigen Produkt, sollte für alle gleich sein)
            daily_capacity = 0.0
            if products_info:
                first_product_info = next(iter(products_info.values()))
                shifts = first_product_info['shifts']
                working_hours = MasterData.GLOBAL_CONFIG.get('working_hours_per_shift', 8)
                capacity_per_hour = MasterData.GLOBAL_CONFIG.get('capacity_per_hour', 130)
                daily_capacity = shifts * working_hours * capacity_per_hour
            
            # ----------------------------------------------------------------
            # ÄNDERUNG: Keine Prüfung auf inputs_changed mehr!
            # Wir berechnen IMMER neu, um sicherzustellen, dass production_logs 
            # und material_verbrauch absolut konsistent sind.
            # Dies korrigiert auch interne Inkonsistenzen aus der ursprünglichen Simulation.
            # ----------------------------------------------------------------
            
            if daily_capacity > 0:
                # IMMER neu berechnen: Repliziere KOMPLETTE statische Logik mit neuen Inputs
                # Verwende berechneten Backlog statt statischen Backlog
                new_production = _recalculate_all_products_with_rank_logic(
                    day,
                    product_demands_new,
                    saddle_available_new,
                    daily_capacity,
                    production_logs,
                    planning_year,
                    workday_calc,
                    backlog_by_product_calculated
                )
                
                # Aktualisiere DataFrame UND berechne neues Delta
                for product, info in products_info.items():
                    df = info['df']
                    idx = info['idx']
                    saddle_name = MasterData.BOM[product]['saddle']
                    
                    new_tatsaechliche_pm = new_production.get(product, 0)
                    base_tatsaechliche_pm = info['base_tatsaechliche_pm']
                    
                    # Update DataFrame
                    df.at[idx, 'tatsächliche PM'] = new_tatsaechliche_pm
                    
                    # WICHTIG: Schreibe Materialverbrauch explizit (immer konsistent mit tatsächlicher PM)
                    if 'material_verbrauch' not in df.columns:
                        df['material_verbrauch'] = 0
                    df.at[idx, 'material_verbrauch'] = new_tatsaechliche_pm
                    
                    # Korrigierten Bestand eintragen (Visualisierung)
                    df.at[idx, saddle_name] = int(round(saddle_available_new[saddle_name])) if saddle_available_new[saddle_name] > 0 else 0
                    
                    # Delta aktualisieren (Kumulierte Abweichung zur CSV-Basis)
                    # Delta = (Neue Produktion - Alte Produktion)
                    # Wenn wir mehr produzieren, erhöht sich das Delta (Bestand sinkt stärker)
                    try:
                        old_val = float(base_tatsaechliche_pm) if base_tatsaechliche_pm > 0 else 0.0
                    except (ValueError, TypeError):
                        old_val = 0.0
                    
                    consumption_diff = float(new_tatsaechliche_pm) - old_val
                    cumulative_saddle_consumption_delta[saddle_name] += consumption_diff
                
                # Backlog speichern
                calculated_backlogs[day] = {}
                for product in MasterData.BOM.keys():
                    planned_pm = product_demands_new.get(product, 0)
                    actual_pm = new_production.get(product, 0)
                    prev_backlog = backlog_by_product_calculated.get(product, 0.0)
                    new_backlog = max(0.0, (planned_pm + prev_backlog) - actual_pm)
                    calculated_backlogs[day][product] = new_backlog
            else:
                # Falls Kapazität 0 ist (z.B. Wochenende), setze Werte auf 0
                for product, info in products_info.items():
                    df = info['df']
                    idx = info['idx']
                    saddle_name = MasterData.BOM[product]['saddle']
                    
                    df.at[idx, 'tatsächliche PM'] = 0
                    if 'material_verbrauch' not in df.columns:
                        df['material_verbrauch'] = 0
                    df.at[idx, 'material_verbrauch'] = 0
                    
                    # Korrigierten Bestand eintragen (falls Delta vorhanden)
                    stock_val = saddle_available_new.get(saddle_name, 0.0)
                    df.at[idx, saddle_name] = int(round(stock_val)) if stock_val > 0 else 0
                
                # Backlog bleibt unverändert (wird am nächsten Arbeitstag weitergeführt)
                calculated_backlogs[day] = {}
                for product in MasterData.BOM.keys():
                    planned_pm = product_demands_new.get(product, 0)
                    prev_backlog = backlog_by_product_calculated.get(product, 0.0)
                    # Backlog erhöht sich um geplante PM (da nichts produziert wurde)
                    calculated_backlogs[day][product] = prev_backlog + planned_pm
        
        # Aktualisiere "fertiggestellte PM"
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
                        
                        # WICHTIG: "Fertiggestellte PM" sollte nur an Arbeitstagen angezeigt werden
                        # An Feiertagen/Wochenenden sollte sie 0 sein
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
    
        # Aktualisiere Backlog
        for product, df in production_logs.items():
            if df.empty or 'Datum' not in df.columns or 'fertiggestellte PM' not in df.columns or 'geplante PM' not in df.columns or 'Backlog' not in df.columns:
                continue
            
            df_sorted = df.copy()
            df_sorted['_date_parsed'] = pd.to_datetime(df_sorted['Datum'], format=MasterData.DATE_FORMAT)
            df_sorted = df_sorted.sort_values('_date_parsed').reset_index(drop=True)
            
            for idx, row in df_sorted.iterrows():
                date_str = row.get('Datum', '')
                if date_str:
                    try:
                        row_date = datetime.strptime(date_str, MasterData.DATE_FORMAT).date()
                        day = (row_date - date(planning_year, 1, 1)).days
                        
                        if day in daily_demands_actual:
                            product_demands = daily_demands_actual[day]
                            planned_pm = product_demands.get(product, 0)
                            
                            # KRITISCH: Backlog wird basierend auf der HEUTE GESTARTETEN Produktion reduziert
                            # (nicht erst bei Fertigstellung), um den "Echo-Effekt" zu vermeiden
                            actual_started = row.get('tatsächliche PM', 0)
                            try:
                                actual_started = int(actual_started) if actual_started > 0 else 0
                            except (ValueError, TypeError):
                                actual_started = 0
                            
                            prev_backlog = 0.0
                            if idx > 0:
                                prev_row = df_sorted.iloc[idx - 1]
                                prev_backlog = prev_row.get('Backlog', 0)
                                try:
                                    prev_backlog = float(prev_backlog) if prev_backlog > 0 else 0.0
                                except (ValueError, TypeError):
                                    prev_backlog = 0.0
                            
                            # Neuer Backlog = (geplante PM + Backlog gestern) - tatsächliche PM (heute gestartet)
                            # Dies stellt sicher, dass der Backlog sofort reduziert wird, wenn produziert wird
                            new_backlog = max(0.0, (planned_pm + prev_backlog) - actual_started)
                            df_sorted.at[idx, 'Backlog'] = int(round(new_backlog))
                            
                            current_planned_pm = row.get('geplante PM', 0)
                            try:
                                current_planned_pm = int(current_planned_pm) if current_planned_pm > 0 else 0
                            except (ValueError, TypeError):
                                current_planned_pm = 0
                            
                            if planned_pm != current_planned_pm:
                                df_sorted.at[idx, 'geplante PM'] = int(planned_pm)
                    except (ValueError, TypeError):
                        pass
            
            if '_date_parsed' in df_sorted.columns:
                df_sorted = df_sorted.drop(columns=['_date_parsed'])
            production_logs[product] = df_sorted
    
    # Cache Ergebnis
    st.session_state.production_logs_cache = production_logs
    st.session_state.production_logs_cache_key = cache_key
    
    # NEU: Datenfluss-Korrektur
    # Schreibe die aktualisierten DataFrames zurück in den Simulator,
    # damit das Materiallager (pages/5_materiallager.py) die Änderungen sieht.
    if planner:
        for product, df in production_logs.items():
            if not df.empty:
                # Konvertiere DataFrame zurück in Liste von Dicts
                # Wichtig: Entferne interne Spalten (die mit '_' beginnen) und behalte nur UI-relevante
                # Konvertiere zu Dict-Liste
                updated_logs = df.to_dict('records')
                planner.production_logs[product] = updated_logs
    
    # NEU: Erzwinge Neuberechnung des Materiallagers
    # Da sich die Produktion geändert hat, sind die gecachten Materialdaten veraltet.
    # Wir löschen sie, damit die Material-Seite sie beim nächsten Aufruf 
    # frisch aus den aktualisierten production_logs berechnet.
    if 'material_inventory_data' in st.session_state:
        del st.session_state['material_inventory_data']
    
    # WICHTIG: Cache-Key 'saddle_logs_cache' muss gelöscht werden, 
    # damit pages/5_materiallager.py die Daten neu berechnet.
    keys_to_clear = [
        'saddle_logs_cache',           # Cache für Materiallager-Tabelle
        'material_logs_cache',         # Legacy Cache
        'inventory_chart_cache'        # Cache für Charts
    ]
    
    # Lösche auch alle versionierten Cache-Keys des Materiallagers
    # (Keys die mit 'material_inventory_' beginnen, außer 'material_inventory_last_cache_key')
    for k in list(st.session_state.keys()):
        if k in keys_to_clear or (k.startswith('material_inventory_') and k != 'material_inventory_last_cache_key'):
            del st.session_state[k]
    
    return production_logs
